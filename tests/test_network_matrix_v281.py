"""Deterministic local IPv4/IPv6 failover and WebSocket TLS acceptance tests."""
from __future__ import annotations

import base64
import hashlib
import os
import re
import socket
import ssl
import threading
import time
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import importlib.util
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'custom_components/cook4me/vendor/adaptive_transport.py'
SPEC = importlib.util.spec_from_file_location('cook4me_adapter_network_matrix', SOURCE)
at = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(at)


def certs(folder):
    folder = Path(folder)
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048',
                    '-noenc', '-keyout', str(folder/'key.pem'),
                    '-out', str(folder/'cert.pem'), '-days', '1',
                    '-subj', '/CN=localhost', '-addext',
                    'subjectAltName=DNS:localhost'],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(str(folder/'cert.pem'), str(folder/'key.pem'))
    client = ssl.create_default_context(cafile=str(folder/'cert.pem'))
    return server, client


def serve_tls(listener, context, *, do_websocket=False, wait_before_tls=0):
    try:
        peer, _ = listener.accept()
        with peer:
            if wait_before_tls:
                time.sleep(wait_before_tls)
                return
            try:
                with context.wrap_socket(peer, server_side=True) as conn:
                    if do_websocket:
                        buf = b""
                        conn.settimeout(3)
                        while b"\r\n\r\n" not in buf:
                            buf += conn.recv(4096)
                        key = re.search(rb"Sec-WebSocket-Key:\s*([^\r\n]+)", buf, re.I).group(1).strip()
                        accept = base64.b64encode(hashlib.sha1(key+b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
                        conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "+accept+b"\r\nSec-WebSocket-Protocol: mqtt\r\n\r\n")
                        try:conn.recv(1024)
                        except (TimeoutError, OSError):pass
                    else:
                        try:conn.recv(1)
                        except (TimeoutError, OSError):pass
            except (OSError, ssl.SSLError):
                pass
    finally:
        listener.close()


def sock_listener(family, port=0):
    sock = socket.socket(family, socket.SOCK_STREAM)
    if family == socket.AF_INET6:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.bind(('::1', port))
    else:
        sock.bind(('127.0.0.1', port))
    sock.listen(3)
    return sock


def addresses(v4port, v6port, first_family=socket.AF_INET):
    v4=(socket.AF_INET, socket.SOCK_STREAM,socket.IPPROTO_TCP,('127.0.0.1',v4port))
    v6=(socket.AF_INET6,socket.SOCK_STREAM,socket.IPPROTO_TCP,('::1',v6port,0,0))
    return [v4,v6] if first_family==socket.AF_INET else [v6,v4]


class NetworkMatrix(unittest.TestCase):
    def test_ipv4_stalled_tls_ipv6_fast_reverse_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            server, client=certs(d)
            v4=sock_listener(socket.AF_INET)
            try:v6=sock_listener(socket.AF_INET6)
            except OSError as e:
                v4.close();self.skipTest(f"No IPv6 loopback: {e}")
            t4=threading.Thread(target=serve_tls,args=(v4,server),kwargs={'wait_before_tls':1.35},daemon=True)
            t6=threading.Thread(target=serve_tls,args=(v6,server),daemon=True)
            t4.start();t6.start()
            addrs=addresses(v4.getsockname()[1],v6.getsockname()[1],socket.AF_INET)
            start=time.monotonic()
            with patch.object(at,'_alternating_addresses',return_value=addrs):
                with at.connect_tls_dual_stack('localhost',context=client,timeout=2) as conn:
                    self.assertTrue(conn.version().startswith('TLS'))
                    conn.sendall(b'a')
            self.assertLess(time.monotonic()-start,1.0)
            t6.join(2)

    def test_ipv6_only_websocket_tls_upgrade(self):
        with tempfile.TemporaryDirectory() as d:
            server, client=certs(d)
            try:v6=sock_listener(socket.AF_INET6)
            except OSError as e:self.skipTest(f"No IPv6 loopback: {e}")
            port=v6.getsockname()[1]
            t=threading.Thread(target=serve_tls,args=(v6,server),kwargs={'do_websocket':True},daemon=True)
            t.start()
            real=at.connect_tls_dual_stack
            def only_v6(host,_port=443,*,timeout=15):
                return real('localhost',port,timeout=timeout,context=client)
            with patch.object(at,'_alternating_addresses',return_value=addresses(9999,port,first_family=socket.AF_INET6)[:1]):
                with patch.object(at,'connect_tls_dual_stack',side_effect=only_v6):
                    with patch.object(at,'_proxy_options',return_value=None):
                        ws=at.create_mqtt_websocket('wss://localhost:443/mqtt','localhost',timeout=2)
                        self.assertTrue(ws.connected)
                        ws.close()
            t.join(2)

    def test_both_families_refused_returns_bounded_error(self):
        ports=[]
        for family in (socket.AF_INET,socket.AF_INET6):
            try: sock=sock_listener(family)
            except OSError as exc: self.skipTest(f"IPv6 loopback unavailable: {exc}")
            ports.append(sock.getsockname()[1]);sock.close()
        start=time.monotonic()
        with patch.object(at,'_alternating_addresses',return_value=addresses(*ports)):
            with self.assertRaises((OSError,TimeoutError)):
                at.connect_tls_dual_stack('localhost',timeout=1.0)
        self.assertLess(time.monotonic()-start,1.5)

    def test_untrusted_tls_certificate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            server, _=certs(d)
            sock=sock_listener(socket.AF_INET);port=sock.getsockname()[1]
            t=threading.Thread(target=serve_tls,args=(sock,server),daemon=True);t.start()
            with patch.dict(os.environ, {'WEBSOCKET_CLIENT_CA_BUNDLE':''}), patch.object(at,'_alternating_addresses',return_value=addresses(port,0)[:1]):
                with self.assertRaises(OSError):
                    at.connect_tls_dual_stack('localhost',timeout=1.5)
            t.join(2)

    def test_tls_hostname_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            server, client=certs(d)
            sock=sock_listener(socket.AF_INET);port=sock.getsockname()[1]
            t=threading.Thread(target=serve_tls,args=(sock,server),daemon=True);t.start()
            with patch.object(at,'_alternating_addresses',return_value=addresses(port,0)[:1]):
                with self.assertRaises(OSError):
                    at.connect_tls_dual_stack('bad.invalid',timeout=1.5,context=client)
            t.join(2)

class RealHTTPProxyMatrix(unittest.TestCase):
    @staticmethod
    def serve_proxy(listener, target_port, observed, *, require_auth=True):
        import select
        try:
            downstream, _=listener.accept()
            with downstream:
                downstream.settimeout(3)
                message=b''
                while b'\r\n\r\n' not in message and len(message)<8000:
                    fragment=downstream.recv(4096)
                    if not fragment:break
                    message+=fragment
                observed.append(message)
                expected=b'Proxy-Authorization: Basic '+base64.b64encode(b'user:secret')
                if require_auth and expected.lower() not in message.lower():
                    downstream.sendall(b'HTTP/1.1 407 Proxy Authentication Required\r\nContent-Length: 0\r\n\r\n')
                    return
                upstream=socket.create_connection(('127.0.0.1',target_port),timeout=3)
                with upstream:
                    downstream.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                    downstream.setblocking(False);upstream.setblocking(False)
                    ends=[downstream,upstream]
                    end_at=time.monotonic()+4
                    while time.monotonic()<end_at:
                        ready,_,_=select.select(ends,[],[],.1)
                        for side in ready:
                            try: data=side.recv(16384)
                            except BlockingIOError:continue
                            if not data:return
                            peer=upstream if side is downstream else downstream
                            peer.sendall(data)
        except (OSError,ssl.SSLError):pass
        finally:listener.close()

    def test_real_http_connect_authenticated_proxy_to_wss(self):
        import websocket
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            server,_=certs(directory)
            origin=sock_listener(socket.AF_INET);target=origin.getsockname()[1]
            accept=threading.Thread(target=serve_tls,args=(origin,server),kwargs={'do_websocket':True},daemon=True)
            accept.start()
            proxy=sock_listener(socket.AF_INET);port=proxy.getsockname()[1]
            captured=[]
            relay=threading.Thread(target=self.serve_proxy,args=(proxy,target,captured),daemon=True)
            relay.start()
            env={'HTTPS_PROXY':f'http://user:secret@127.0.0.1:{port}',
                 'NO_PROXY':'','WEBSOCKET_CLIENT_CA_BUNDLE':directory+'/cert.pem'}
            with patch.dict(os.environ,env,clear=True):
                ws=at.create_mqtt_websocket(f'wss://localhost:{target}/mqtt','localhost',timeout=3)
                self.assertTrue(ws.connected)
                ws.close()
            relay.join(5);accept.join(5)
            self.assertIn(b'CONNECT localhost:',captured[0])
            self.assertIn(b'Proxy-Authorization:',captured[0])

    def test_proxy_auth_denial_never_falls_back_to_direct(self):
        import websocket
        from unittest.mock import patch
        proxy=sock_listener(socket.AF_INET);port=proxy.getsockname()[1]
        captured=[]
        relay=threading.Thread(target=self.serve_proxy,args=(proxy,12345,captured),daemon=True)
        relay.start()
        env={'HTTPS_PROXY':f'http://127.0.0.1:{port}','NO_PROXY':''}
        with patch.dict(os.environ,env,clear=True):
            with self.assertRaises((websocket.WebSocketProxyException,OSError,ConnectionError)):
                at.create_mqtt_websocket('wss://localhost:12345/mqtt','localhost',timeout=2)
        relay.join(3)
        self.assertEqual(len(captured),1)

if __name__=='__main__':unittest.main(verbosity=2)
