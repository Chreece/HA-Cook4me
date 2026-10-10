"""Connection-family fallback for direct, TLS-protected Cook4Me MQTT sockets.

The OS chooses the route (including VPN routes). Both reachable IP families are
tried with a short stagger; a stalled IPv6 or IPv4 handshake cannot consume the
entire deadline before the other family starts. Existing proxy connections stay
with websocket-client so no explicit proxy is ever bypassed.
"""
from __future__ import annotations

import errno
import os
import selectors
import socket
import ssl
import time

FALLBACK_DELAY = 0.25
_IN_PROGRESS = {errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK, errno.EINTR}


def _alternating_addresses(host: str, port: int) -> list[tuple]:
    """Preserve DNS first-family preference, then alternate IPv6 and IPv4."""
    resolved = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    families = {socket.AF_INET: [], socket.AF_INET6: []}
    seen = set()
    for address in resolved:
        family, sock_type, protocol, _, sockaddr = address
        if family not in families:
            continue
        identity = (family, sockaddr)
        if identity not in seen:
            seen.add(identity)
            families[family].append((family, sock_type, protocol, sockaddr))
    first_family = next((item[0] for item in resolved if item[0] in families), socket.AF_INET)
    second_family = socket.AF_INET if first_family == socket.AF_INET6 else socket.AF_INET6
    interleaved = []
    for index in range(max(len(families[first_family]), len(families[second_family]))):
        for family in (first_family, second_family):
            if index < len(families[family]):
                interleaved.append(families[family][index])
    return interleaved


def _tls_context() -> ssl.SSLContext:
    """Honor the existing websocket-client CA override without weakening TLS."""
    ca = os.environ.get("WEBSOCKET_CLIENT_CA_BUNDLE", "")
    if os.path.isfile(ca):
        return ssl.create_default_context(cafile=ca)
    if os.path.isdir(ca):
        return ssl.create_default_context(capath=ca)
    return ssl.create_default_context()


def connect_tls_dual_stack(
    host: str,
    port: int = 443,
    *,
    timeout: float = 15.0,
    fallback_delay: float = FALLBACK_DELAY,
    context: ssl.SSLContext | None = None,
) -> ssl.SSLSocket:
    """Race TLS handshakes across resolved families with a *single* deadline.

    Uses selectors rather than background threads, so losing sockets are closed
    before returning and a Home Assistant reload cannot leave network workers.
    """
    if timeout <= 0 or fallback_delay < 0:
        raise ValueError("Invalid connection timing")
    addresses = _alternating_addresses(host, port)
    if not addresses:
        raise OSError("Cook4Me MQTT endpoint has no supported IP addresses")
    ssl_context = context if context is not None else _tls_context()
    deadline = time.monotonic() + timeout
    next_start = time.monotonic()
    pending = list(addresses)
    selector = selectors.DefaultSelector()
    active: set[socket.socket] = set()
    selected_socket = None
    last_failure: OSError | ssl.SSLError | None = None

    def close_attempt(sock):
        active.discard(sock)
        try:
            selector.unregister(sock)
        except (KeyError, ValueError):
            pass
        sock.close()

    try:
        while time.monotonic() < deadline and (pending or active):
            now = time.monotonic()
            if pending and (now >= next_start or not active):
                family, socktype, proto, sockaddr = pending.pop(0)
                raw = socket.socket(family, socktype, proto)
                try:
                    raw.setblocking(False)
                    error = raw.connect_ex(sockaddr)
                    if error not in _IN_PROGRESS and error != 0:
                        last_failure = OSError(error, "Connection unavailable")
                        raw.close()
                        next_start = now
                    else:
                        active.add(raw)
                        selector.register(raw, selectors.EVENT_WRITE, "connecting")
                        next_start = now + fallback_delay
                except BaseException:
                    raw.close()
                    raise
                continue

            until_next = max(0.0, next_start - now) if pending else deadline - now
            wait = min(max(0.0, deadline - now), until_next)
            for key, _ in selector.select(wait):
                sock = key.fileobj
                if key.data == "connecting":
                    error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if error:
                        last_failure = OSError(error, "Connection unavailable")
                        close_attempt(sock)
                        continue
                    selector.unregister(sock)
                    active.discard(sock)
                    try:
                        secure = ssl_context.wrap_socket(
                            sock, server_hostname=host, do_handshake_on_connect=False
                        )
                        secure.setblocking(False)
                        active.add(secure)
                        selector.register(secure, selectors.EVENT_READ | selectors.EVENT_WRITE, "handshake")
                    except (OSError, ssl.SSLError) as exc:
                        last_failure = exc
                        sock.close()
                    continue

                try:
                    sock.do_handshake()
                except ssl.SSLWantReadError:
                    selector.modify(sock, selectors.EVENT_READ, "handshake")
                except ssl.SSLWantWriteError:
                    selector.modify(sock, selectors.EVENT_WRITE, "handshake")
                except (OSError, ssl.SSLError) as exc:
                    last_failure = exc
                    close_attempt(sock)
                else:
                    selector.unregister(sock)
                    active.discard(sock)
                    selected_socket = sock
                    selected_socket.settimeout(timeout)
                    return selected_socket
        if last_failure is not None and not active and not pending:
            raise OSError("Cook4Me MQTT TLS connection failed for all resolved addresses") from last_failure
        raise TimeoutError("Cook4Me MQTT TLS connection timed out across available IP families")
    finally:
        for sock in list(active):
            close_attempt(sock)
        selector.close()


def _proxy_in_use(host: str) -> bool:
    """Use websocket-client's own proxy decisions, including NO_PROXY."""
    try:
        from websocket._url import get_proxy_info
        return bool(get_proxy_info(host, is_secure=True)[0])
    except Exception:
        # If proxy resolution is ambiguous, never bypass a configured proxy.
        return bool(os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or
                    os.environ.get("wss_proxy") or os.environ.get("WSS_PROXY") or
                    os.environ.get("all_proxy") or os.environ.get("ALL_PROXY"))


def create_mqtt_websocket(url: str, host: str, *, timeout: float = 15.0):
    """Preserve websocket-client's proxy path; use dual-stack TLS when direct."""
    import websocket

    options = dict(timeout=timeout, subprotocols=["mqtt"], suppress_origin=True, host=f"{host}:443")
    if _proxy_in_use(host):
        return websocket.create_connection(url, **options)
    tls_socket = connect_tls_dual_stack(host, 443, timeout=timeout)
    try:
        return websocket.create_connection(url, socket=tls_socket, **options)
    except BaseException:
        tls_socket.close()
        raise
