from __future__ import annotations

import re
import time
import urllib.parse
from pathlib import Path
from typing import Any

from . import recipe_search_v8
from .vendor import cook4me_phonefree as c4m
from .vendor import cook4me_recipe_catalog as catalog

_DIAGNOSTIC_HEADER_NAMES = {"app", "access_rcu", "id_rcu"}
_SECRET_PATTERNS = (
    re.compile(r"Bearer\s+[^\s,;]+", re.IGNORECASE),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
)


def _safe_text(value: Any, limit: int = 180) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    # Avoid reflecting unexpectedly long opaque server values into HA/UI logs.
    text = re.sub(r"\b[A-Za-z0-9_=-]{80,}\b", "[REDACTED]", text)
    return text[:limit] or None


def _response_detail(response) -> dict[str, Any]:
    status = int(response.status_code)
    out: dict[str, Any] = {"status": status, "success": 200 <= status < 300}
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        for source, target in (
            ("errorCode", "errorCode"),
            ("code", "code"),
            ("error", "error"),
            ("message", "message"),
            ("error_description", "message"),
        ):
            if source in payload and target not in out:
                value = _safe_text(payload.get(source))
                if value:
                    out[target] = value
    elif not out["success"]:
        value = _safe_text(getattr(response, "text", None))
        if value:
            out["message"] = value
    return out


def _token_meta(tokens: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("access_token", "id_token", "refresh_token"):
        token = tokens.get(key)
        row: dict[str, Any] = {"present": bool(token)}
        if token and key != "refresh_token":
            try:
                exp = c4m.jwt_exp(token)
            except Exception:
                exp = None
            if exp:
                row["expiresAt"] = int(exp)
                row["expired"] = bool(exp <= time.time())
        out[key] = row
    return out


def _url_matches_base(url: str, base: str | None) -> bool:
    if not base:
        return False
    try:
        target = urllib.parse.urlsplit(url)
        expected = urllib.parse.urlsplit(base)
    except Exception:
        return False
    if not target.scheme or not target.netloc or not expected.netloc:
        return False
    return (
        target.scheme.lower() == expected.scheme.lower()
        and target.netloc.lower() == expected.netloc.lower()
        and target.path.startswith(expected.path.rstrip("/"))
    )


def _probe_body(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    url: str,
    params: dict[str, Any],
    body: dict[str, Any],
    country: str,
    configured_language: str,
    app_version: str,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    success = False
    auth_mode: str | None = None
    headers_iter = catalog._request_headers(
        cfg,
        tokens,
        country,
        configured_language,
        app_version,
        url,
        pcfg,
    )
    for name, headers in headers_iter:
        # Ordinary SearchRecipesV2 traffic is not SAP-CC remote traffic. The
        # APK appends .REMOTE only when the target URL matches sapCcBaseUrl.
        # Probe the exact useful candidates and avoid multiplying requests.
        if name not in _DIAGNOSTIC_HEADER_NAMES:
            continue
        try:
            response = catalog.c4m.curl_requests.post(
                url,
                params=params,
                headers=headers,
                json=body,
                timeout=20,
                allow_redirects=True,
                impersonate="chrome",
            )
        except Exception as exc:
            attempts.append({"mode": name, "networkError": type(exc).__name__})
            continue
        row = {"mode": name, **_response_detail(response)}
        attempts.append(row)
        if row.get("success"):
            success = True
            auth_mode = name
            break
    return {"success": success, "authMode": auth_mode, "attempts": attempts}


def diagnose_search(
    storage_home: str,
    *,
    country: str,
    configured_language: str,
    app_version: str,
    query: str,
) -> dict[str, Any]:
    """Compare legacy-empty and v8 search bodies without exposing credentials."""
    cfg = c4m.read_apk_config(None)
    token_path = Path(storage_home) / ".config" / "cook4me" / "tokens.json"
    try:
        tokens = c4m.load_json(token_path)
    except Exception:
        tokens = {}
    pcfg = catalog._platform_context(cfg, country, configured_language, app_version)
    base = cfg["platform_base_url"].rstrip("/")
    url = base + "/common-api/v4/search/recipes"
    market = f"GS_{str(country).upper()}"
    params = {
        "lang": configured_language,
        "market": market,
        "page": 0,
        "size": 3,
        "q": str(query or ""),
        "groupBy": "",
        "myUniverse": "false",
        "myOwnRecipe": "false",
        "withAutomaticSpellcheck": "true",
    }

    common = dict(
        cfg=cfg,
        tokens=tokens,
        pcfg=pcfg,
        url=url,
        params=params,
        country=country,
        configured_language=configured_language,
        app_version=app_version,
    )
    legacy = _probe_body(**common, body={})
    app_body = _probe_body(
        **common,
        body=recipe_search_v8.app_search_body(configured_language, market),
    )

    return {
        "readOnly": True,
        "host": urllib.parse.urlsplit(url).netloc,
        "path": urllib.parse.urlsplit(url).path,
        "language": configured_language,
        "market": market,
        "tokenFileExists": token_path.exists(),
        "tokenFileMtime": int(token_path.stat().st_mtime) if token_path.exists() else None,
        "tokens": _token_meta(tokens),
        "dcpContextPresent": bool(pcfg.get("profile_perimeter")),
        "apimSubscriptionKeyPresent": bool(pcfg.get("apim_subscription_key")),
        "requestMatchesApimBase": _url_matches_base(url, pcfg.get("apim_url")),
        "legacyEmptyBody": legacy,
        "v8AppBody": app_body,
        "bodyMismatchProven": bool(legacy.get("success") and not app_body.get("success")),
        "authenticationRejectedByBoth": bool(
            not legacy.get("success") and not app_body.get("success")
        ),
    }


def diagnostic_summary(diagnostic: dict[str, Any]) -> str:
    """Produce a compact redacted summary suitable for the Recipe Hub UI."""
    def modes(section: str) -> str:
        rows = diagnostic.get(section, {}).get("attempts") or []
        values = []
        for row in rows:
            mode = str(row.get("mode") or "?")
            if row.get("status") is not None:
                suffix = str(row["status"])
                code = row.get("errorCode") or row.get("code") or row.get("error")
                if code:
                    suffix += f"/{_safe_text(code, 50)}"
            else:
                suffix = str(row.get("networkError") or "error")
            values.append(f"{mode}={suffix}")
        return ", ".join(values) or "no attempts"

    if diagnostic.get("bodyMismatchProven"):
        return (
            "KRUPS credentials work with the legacy search body, but the v8 "
            f"SearchRecipesV2 body is rejected. legacy[{modes('legacyEmptyBody')}] "
            f"v8[{modes('v8AppBody')}]"
        )
    return (
        "KRUPS catalog rejected both search contracts. "
        f"legacy[{modes('legacyEmptyBody')}] v8[{modes('v8AppBody')}] "
        f"DCP-context={'yes' if diagnostic.get('dcpContextPresent') else 'no'} "
        f"APIM-match={'yes' if diagnostic.get('requestMatchesApimBase') else 'no'}"
    )
