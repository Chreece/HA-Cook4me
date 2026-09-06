#!/usr/bin/env python3
"""
KRUPS / Cook4Me phone-free authentication over plain HTTP.

No Playwright / Chromium.

Protocol reconstructed from the live KRUPS Salesforce Visualforce flow:
  ContinuationForExpId
    -> OAuth authorize
    -> RemoteAccessAuthorizationPage
    -> /Login
    -> A4J POST /Login (userEmail/password + Salesforce ViewState)
    -> frontdoor.jsp
    -> /apex/LoginFlow
    -> A4J POST /LoginFlow (ViewState + ViewStateCSRF)
    -> RemoteAccessAuthorizationPage
    -> OAuth completion -> gsmoduser://tokens

Credentials are stored locally after the first successful entry and reused automatically.
The credential file is mode 0600 inside ~/.config/cook4me (mode 0700).
Sensitive values are never printed. A timestamped sanitized log is written.
"""

import argparse
import getpass
import html
import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

try:
    from curl_cffi import requests as curl_requests
except Exception as exc:  # Home Assistant installs this from manifest requirements
    curl_requests = None
    _CURL_CFFI_IMPORT_ERROR = exc
else:
    _CURL_CFFI_IMPORT_ERROR = None

from urllib.parse import (
    parse_qs, parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
)

APP_VERSION_DEFAULT = "36.0.0-RC3"

SENSITIVE_KEYS = {
    "password", "userEmail", "email",
    "access_token", "refresh_token", "id_token",
    "sid", "source", "allp", "appkp", "cshc",
    "apikey", "api_key", "authorization",
}

def load_client():
    p = Path(__file__).resolve().parent / "cook4me_phonefree.py"
    if not p.exists():
        raise RuntimeError(f"Missing {p}")
    spec = importlib.util.spec_from_file_location("cook4me_phonefree", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def safe_url(url):
    try:
        p = urlsplit(url)
        q = [(k, "<redacted>") for k, _ in parse_qsl(p.query, keep_blank_values=True)]
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), ""))
    except Exception:
        return "<unparseable-url>"

def redact_text(s, email=None, password=None):
    if not s:
        return s
    if email:
        s = s.replace(email, "<email-redacted>")
    if password:
        s = s.replace(password, "<password-redacted>")
    s = re.sub(r'gsmoduser://tokens[^\s\'"<]+', 'gsmoduser://tokens?<redacted>', s)
    s = re.sub(
        r'(?i)((?:access_token|refresh_token|id_token|authorization|password|'
        r'userEmail|email|session[_-]?token|secret|sid|apikey|api_key)\s*[=:]\s*)'
        r'[^&\s,"\'};<>]+',
        r'\1<redacted>',
        s
    )
    s = re.sub(
        r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}',
        '<jwt-redacted>',
        s
    )
    return s

class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None
        self.all_inputs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag.lower() == "form":
            self.current = {
                "id": a.get("id"),
                "name": a.get("name"),
                "method": (a.get("method") or "get").lower(),
                "action": a.get("action") or "",
                "inputs": [],
                "buttons": [],
            }
            self.forms.append(self.current)
        elif tag.lower() == "input":
            item = {
                "id": a.get("id"),
                "name": a.get("name"),
                "type": (a.get("type") or "text").lower(),
                "value": a.get("value") or "",
            }
            self.all_inputs.append(item)
            if self.current is not None:
                self.current["inputs"].append(item)
        elif self.current is not None and tag.lower() == "button":
            self.current["buttons"].append({
                "id": a.get("id"),
                "name": a.get("name"),
                "type": a.get("type"),
                "value": a.get("value"),
            })

    def handle_endtag(self, tag):
        if tag.lower() == "form":
            self.current = None

def parse_forms(text):
    p = FormParser()
    p.feed(text)
    return p.forms

def form_by_id(forms, form_id):
    for f in forms:
        if f.get("id") == form_id or f.get("name") == form_id:
            return f
    return None

def hidden_fields(form):
    out = []
    for i in form["inputs"]:
        if i["type"] == "hidden" and i["name"]:
            out.append((i["name"], i["value"]))
    return out

def salesforce_state_fields(html_text, form):
    """
    Salesforce Visualforce may render ViewState inputs outside the literal <form>.
    VFState.js/vfPrepareForms associates them client-side. Collect normal form
    hidden inputs plus document-wide Salesforce state inputs.
    """
    p = FormParser()
    p.feed(html_text)
    out = hidden_fields(form)
    have = {k for k, _ in out}
    wanted_prefix = "com.salesforce.visualforce."
    for i in p.all_inputs:
        name = i.get("name")
        if (
            i.get("type") == "hidden"
            and name
            and name.startswith(wanted_prefix)
            and name not in have
        ):
            out.append((name, i.get("value") or ""))
            have.add(name)
    return out


def rcu_base(rcu):
    if isinstance(rcu, str):
        return rcu
    if not isinstance(rcu, dict):
        raise RuntimeError(f"Unexpected RCU result type {type(rcu).__name__}")
    # IMPORTANT:
    # The Android IoT stack uses DCP bestMatchMarket.rcuBaseUrl as its
    # Salesforce identity-provider base.  brand_rcu_base_url is the
    # brand-specific /url-connexion result and is NOT interchangeable
    # with the Cognito/Salesforce provider.
    for k in ("rcu_base_url", "brand_rcu_base_url", "base_url", "url", "host"):
        v = rcu.get(k)
        if v:
            v = str(v)
            if k == "host" and not v.startswith("http"):
                return "https://" + v
            return v
    for v in rcu.values():
        if isinstance(v, str) and "account.krups" in v:
            return v
    raise RuntimeError(f"RCU base not found in {list(rcu)}")

def build_login_url(c4m, base, cfg, version):
    if hasattr(c4m, "_build_login_url"):
        return c4m._build_login_url(base, cfg, version)
    api_key = cfg["api_key"]
    return urljoin(
        base.rstrip("/") + "/",
        "ContinuationForExpId?"
        f"apikey={quote(str(api_key), safe='')}"
        "&redirect_uri=gsmoduser%3A%2F%2Ftokens"
        "&state=STATE"
        "&response_type=token+id_token+refresh_token"
        "&nonce=NONCE"
        "&isUserName=true"
        f"&version={quote(version, safe='')}"
    )

class CurlSession:
    """Browser-compatible in-process HTTP session.

    The standalone reverse-engineering client originally spawned the system
    `curl` binary.  Home Assistant containers cannot be expected to provide
    that executable, so the integration uses curl_cffi's embedded libcurl and
    browser TLS impersonation instead.  No credentials or token-bearing URLs
    are exposed in a process command line.
    """

    def __init__(self, cookie_jar, log, email, password):
        if curl_requests is None:
            raise RuntimeError(
                "Cook4Me HTTP backend is unavailable (curl-cffi import failed: "
                f"{type(_CURL_CFFI_IMPORT_ERROR).__name__})"
            )
        self.cookie_jar = Path(cookie_jar)
        self.log = log
        self.email = email
        self.password = password
        self.session = curl_requests.Session(impersonate="chrome")
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36"
            ),
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        })

    def _one(self, method, url, data=None, referer=None, headers=None):
        req_headers = dict(headers or {})
        if referer:
            req_headers["Referer"] = referer
        if data is not None:
            req_headers.setdefault(
                "Content-Type",
                "application/x-www-form-urlencoded; charset=UTF-8",
            )
        try:
            response = self.session.request(
                method, url,
                data=(data.encode("utf-8") if isinstance(data, str) else data),
                headers=req_headers,
                allow_redirects=False,
                timeout=60,
            )
        except Exception as exc:
            raise RuntimeError(
                f"HTTP transport error contacting {urlsplit(url).netloc}: "
                f"{type(exc).__name__}: {exc}"
            ) from None

        status = int(response.status_code)
        location = response.headers.get("Location")
        content_type = response.headers.get("Content-Type")
        try:
            body = response.text
        except Exception:
            body = response.content.decode("utf-8", "replace")
        raw_headers = "\n".join(f"{k}: {v}" for k, v in response.headers.items())
        rec = {
            "method": method,
            "url": safe_url(url),
            "status": status,
            "location": safe_url(urljoin(url, location)) if location else None,
            "content_type": content_type,
            "body_length": len(body),
        }
        if data is not None:
            rec["post_field_names"] = [k for k, _ in parse_qsl(data, keep_blank_values=True)]
        self.log["http"].append(rec)
        return status, location, body, raw_headers

    def _run(self, method, url, data=None, referer=None, headers=None, max_redirs=0):
        current = url
        current_method = method
        current_data = data
        current_referer = referer
        redirects = 0
        while True:
            status, location, body, raw_headers = self._one(
                current_method, current, current_data, current_referer, headers
            )
            if not location or status not in (301, 302, 303, 307, 308) or redirects >= max_redirs:
                return status, location, body, raw_headers, current
            nxt = urljoin(current, location)
            if nxt.startswith("gsmoduser://"):
                return status, nxt, body, raw_headers, current
            current_referer = current
            current = nxt
            redirects += 1
            if status in (301, 302, 303) and current_method != "GET":
                current_method = "GET"
                current_data = None


def extract_bootstrap_redirect(body, base_url):
    """Extract Salesforce ContinuationForExpId's client-side OAuth redirect."""
    txt = html.unescape(body)
    patterns = (
        r'projectOneNavigator\.handleRedirect\(\s*["\']([^"\']+)["\']',
        r'window\.location\.replace\(\s*["\']([^"\']+)["\']',
        r'(?:window\.)?location\.href\s*=\s*["\']([^"\']+)["\']',
    )
    for pat in patterns:
        m = re.search(pat, txt, re.I | re.S)
        if m:
            return urljoin(base_url, m.group(1).replace("\\/", "/"))
    return None


def extract_a4j_redirect(body, base_url):
    """
    Find navigation encoded in an Ajax4JSF XML response.
    Supports <redirect>, window.location, location.href and escaped URLs.
    """
    txt = html.unescape(body)
    candidates = []

    # XML redirect element
    for pat in (
        r'<redirect[^>]*>(.*?)</redirect>',
        r'<redirect[^>]+url=["\']([^"\']+)["\']',
        r'(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
        r'window\.open\(["\']([^"\']+)["\']',
        r'["\'](https?://[^"\']+)["\']',
    ):
        for m in re.finditer(pat, txt, re.I | re.S):
            val = m.group(1).strip()
            val = val.replace("\\/", "/").replace("\\u0026", "&")
            val = html.unescape(val)
            if "frontdoor.jsp" in val or "RemoteAccessAuthorizationPage" in val or "/apex/LoginFlow" in val:
                candidates.append(urljoin(base_url, val))
    return candidates[0] if candidates else None

def extract_remote_action(html_text, current_url):
    """
    Inspect the authenticated RemoteAccessAuthorizationPage for an automatic
    continuation/approval target. This deliberately does not guess hidden
    credential values; it follows only page-supplied navigation/actions.
    """
    txt = html.unescape(html_text)

    # Direct callback already embedded
    m = re.search(r'(gsmoduser://tokens[^"\'<\s]+)', txt)
    if m:
        return m.group(1)

    # Common JS redirects/submits.
    pats = [
        r'(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
        r'window\.open\(["\']([^"\']+)["\']',
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\'][^;]+;\s*url=([^"\']+)',
    ]
    for pat in pats:
        for m in re.finditer(pat, txt, re.I):
            u = html.unescape(m.group(1)).replace("\\/", "/")
            if any(x in u for x in ("oauth2", "RemoteAccessAuthorization", "gsmoduser://tokens")):
                return urljoin(current_url, u)

    forms = parse_forms(html_text)
    # Prefer OAuth/authorization-looking POST forms.
    for f in forms:
        action = urljoin(current_url, f["action"])
        low = action.lower()
        if any(x in low for x in ("oauth", "authorize", "remoteaccessauthorization")):
            return ("FORM", f, action)
    return None

def save_tokens_from_callback(callback, path):
    # OAuth implicit/hybrid responses normally return tokens in the URI fragment:
    # gsmoduser://tokens#access_token=...&id_token=...&refresh_token=...
    # Some implementations may use the query, so accept and merge both.
    p = urlsplit(html.unescape(callback))
    params = {}
    for raw in (p.query, p.fragment):
        if not raw:
            continue
        for k, vals in parse_qs(raw, keep_blank_values=True).items():
            if vals:
                params[k] = vals

    tokens = {}
    for k in ("access_token", "refresh_token", "id_token"):
        if params.get(k):
            tokens[k] = params[k][0]

    if len(tokens) < 2:
        return False, sorted(params)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)
    return True, sorted(params)


def credential_path():
    return Path.home() / ".config/cook4me/credentials.json"

def load_saved_credentials(path):
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Could not read saved KRUPS credentials: {type(exc).__name__}")
    email = str(data.get("email") or "").strip()
    password = str(data.get("password") or "")
    if not email or not password:
        raise RuntimeError("Saved KRUPS credential file is incomplete")
    # Tighten permissions every time it is used.
    try:
        os.chmod(path.parent, 0o700)
        os.chmod(path, 0o600)
    except OSError:
        pass
    return email, password

def save_credentials(path, email, password):
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)

    # Atomic write so an interrupted run cannot leave a half-written password file.
    fd, tmp_name = tempfile.mkstemp(prefix=".credentials-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"email": email, "password": password}, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    finally:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except Exception:
            pass

def get_credentials(args):
    path = credential_path()

    if args.forget_credentials:
        path.unlink(missing_ok=True)
        print("Saved KRUPS credentials removed:", path)
        return None, None, False

    env_email = os.environ.get("COOK4ME_EMAIL", "").strip()
    env_password = os.environ.get("COOK4ME_PASSWORD", "")
    if env_email and env_password:
        return env_email, env_password, False

    saved = load_saved_credentials(path)
    if saved:
        email, password = saved
        print("KRUPS credentials   : loaded from ~/.config/cook4me/credentials.json")
        return email, password, True

    email = input("KRUPS email: ").strip()
    password = getpass.getpass("KRUPS password: ")
    if not email or not password:
        raise RuntimeError("Email/password cannot be empty")

    if not args.no_save_credentials:
        save_credentials(path, email, password)
        print("KRUPS credentials   : saved to ~/.config/cook4me/credentials.json (0600)")
    return email, password, False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk")
    ap.add_argument("--country", default="DE")
    ap.add_argument("--language", default="de")
    ap.add_argument("--app-version", default=APP_VERSION_DEFAULT)
    ap.add_argument(
        "--no-save-credentials",
        action="store_true",
        help="Prompt normally but do not save KRUPS credentials for later runs",
    )
    ap.add_argument(
        "--forget-credentials",
        action="store_true",
        help="Delete saved KRUPS credentials and exit",
    )
    args = ap.parse_args()

    email, password, credentials_loaded = get_credentials(args)
    if args.forget_credentials:
        return

    c4m = load_client()
    cfg = c4m.read_apk_config(Path(args.apk) if args.apk else None)
    try:
        rcu = c4m.discover_rcu(cfg, args.country, args.language, args.app_version, save=True)
    except TypeError:
        rcu = c4m.discover_rcu(
            cfg,
            country=args.country,
            language=args.language,
            app_version=args.app_version,
            save=True,
        )

    base = rcu_base(rcu)
    start_url = build_login_url(c4m, base, cfg, args.app_version)

    log = {
        "started": datetime.now().isoformat(),
        "mode": "plain-http-no-browser",
        "rcu_host": urlsplit(base).netloc,
        "http": [],
        "stages": [],
        "callback_observed": False,
        "callback_token_names": [],
        "credentials_source": "saved" if credentials_loaded else "prompt",
    }

    outdir = Path.home() / "cook4me-re"
    outdir.mkdir(parents=True, exist_ok=True)
    logfile = outdir / f"krups-plain-http-auth-{datetime.now():%Y%m%d-%H%M%S}.log"
    cookiejar = outdir / f".krups-cookies-{os.getpid()}.txt"

    try:
        sess = CurlSession(cookiejar, log, email, password)

        # 1. ContinuationForExpId returns HTTP 200 with a JavaScript redirect
        # to /services/oauth2/authorize/expid_..., not an HTTP Location header.
        status, loc, bootstrap_html, _, bootstrap_url = sess._run(
            "GET", start_url, max_redirs=0
        )
        if status != 200:
            raise RuntimeError(f"ContinuationForExpId returned HTTP {status}")
        oauth_url = extract_bootstrap_redirect(bootstrap_html, bootstrap_url)
        if not oauth_url:
            raise RuntimeError(
                "ContinuationForExpId did not contain the expected Salesforce OAuth redirect"
            )
        log["stages"].append("bootstrap_js_redirect_extracted")

        # Follow the OAuth endpoint's real HTTP redirect chain to /Login.
        status, loc, login_html, _, login_effective_url = sess._run(
            "GET", oauth_url, referer=bootstrap_url, max_redirs=10
        )
        login_url = login_effective_url
        if "/Login" not in urlsplit(login_url).path:
            raise RuntimeError(
                f"OAuth authorize chain did not reach /Login; final={safe_url(login_url)}"
            )
        log["stages"].append("login_page_loaded")

        forms = parse_forms(login_html)
        lf = form_by_id(forms, "LoginPage:j_id4")
        if not lf:
            raise RuntimeError(
                f"Login Visualforce form not found; forms={[f.get('id') for f in forms]}"
            )

        login_post_url = urljoin(login_url, lf.get("action") or login_url)

        fields = salesforce_state_fields(login_html, lf)
        required = {
            "com.salesforce.visualforce.ViewState",
            "com.salesforce.visualforce.ViewStateVersion",
            "com.salesforce.visualforce.ViewStateMAC",
        }
        present = {k for k, _ in fields}
        missing = required - present
        if missing:
            raise RuntimeError(f"Login page missing hidden fields: {sorted(missing)}")

        # Exact A4J form observed live.
        post1 = list(fields)
        if not any(k == "AJAXREQUEST" for k, _ in post1):
            post1.insert(0, ("AJAXREQUEST", "_viewRoot"))
        if not any(k == "LoginPage:j_id4" for k, _ in post1):
            post1.append(("LoginPage:j_id4", "LoginPage:j_id4"))
        post1 += [
            ("password", password),
            ("userEmail", email),
            ("LoginPage:j_id4:j_id59", "LoginPage:j_id4:j_id59"),
        ]
        body1 = urlencode(post1)

        status, loc, a4j1, _, _ = sess._run(
            "POST", login_post_url, body1,
            referer=login_url,
            headers={"Accept": "*/*", "X-Requested-With": "XMLHttpRequest"},
        )
        if status != 200:
            raise RuntimeError(f"/Login A4J returned HTTP {status}")
        log["stages"].append("login_a4j_post_ok")

        next_url = extract_a4j_redirect(a4j1, login_url)
        if not next_url:
            # Live successful flow goes to frontdoor.jsp. The URL can be embedded in
            # Ajax XML as JS with escaping, so keep a sanitized diagnostic excerpt.
            log["login_a4j_excerpt"] = redact_text(a4j1[:8000], email, password)
            raise RuntimeError(
                "Login credentials were submitted, but no frontdoor redirect "
                "could be extracted from the A4J response"
            )

        log["stages"].append("frontdoor_redirect_extracted")

        # 2. frontdoor -> LoginFlow page
        status, loc, flow_html, _, flow_effective_url = sess._run(
            "GET", next_url, max_redirs=10
        )
        flow_url = flow_effective_url

        # Salesforce frontdoor.jsp can itself return HTTP 200 with a JS redirect,
        # exactly like ContinuationForExpId. Decode that client-side hop and continue.
        if "LoginFlow" not in urlsplit(flow_url).path:
            frontdoor_js_url = extract_bootstrap_redirect(flow_html, flow_url)
            if not frontdoor_js_url:
                # Broader Salesforce redirect patterns used by frontdoor pages.
                txt = html.unescape(flow_html)
                pats = (
                    r'(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
                    r'(?:window\.)?location\.replace\(\s*["\']([^"\']+)["\']',
                    r'top\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
                    r'parent\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
                )
                for pat in pats:
                    m = re.search(pat, txt, re.I | re.S)
                    if m:
                        frontdoor_js_url = urljoin(flow_url, m.group(1).replace("\\/", "/"))
                        break

            if not frontdoor_js_url:
                # Save structural evidence only; no body/cookie/token values.
                log["frontdoor_structure"] = {
                    "body_length": len(flow_html),
                    "has_loginflow": "LoginFlow" in flow_html,
                    "has_location": bool(re.search(r"location", flow_html, re.I)),
                    "has_form": bool(re.search(r"<form\b", flow_html, re.I)),
                    "has_script": bool(re.search(r"<script\b", flow_html, re.I)),
                }
                raise RuntimeError(
                    f"Authenticated frontdoor returned an undecoded client-side page; "
                    f"final={safe_url(flow_url)}"
                )

            log["stages"].append("frontdoor_js_redirect_extracted")
            status, loc, flow_html, _, flow_effective_url = sess._run(
                "GET", frontdoor_js_url, referer=flow_url, max_redirs=10
            )
            flow_url = flow_effective_url

        if "LoginFlow" not in urlsplit(flow_url).path:
            raise RuntimeError(
                f"Frontdoor client-side redirect did not reach LoginFlow; final={safe_url(flow_url)}"
            )
        log["stages"].append("loginflow_page_loaded")

        forms = parse_forms(flow_html)
        ff = form_by_id(forms, "LoginFlow:j_id5")
        if not ff:
            raise RuntimeError(
                f"LoginFlow Visualforce form not found; forms={[f.get('id') for f in forms]}"
            )

        flow_post_url = urljoin(flow_url, ff.get("action") or flow_url)

        fields2 = salesforce_state_fields(flow_html, ff)
        present2 = {k for k, _ in fields2}
        for required_name in (
            "com.salesforce.visualforce.ViewState",
            "com.salesforce.visualforce.ViewStateVersion",
            "com.salesforce.visualforce.ViewStateMAC",
            "com.salesforce.visualforce.ViewStateCSRF",
        ):
            if required_name not in present2:
                raise RuntimeError(f"LoginFlow missing {required_name}")

        post2 = list(fields2)
        if not any(k == "AJAXREQUEST" for k, _ in post2):
            post2.insert(0, ("AJAXREQUEST", "_viewRoot"))
        if not any(k == "LoginFlow:j_id5" for k, _ in post2):
            post2.append(("LoginFlow:j_id5", "LoginFlow:j_id5"))
        post2.append(("LoginFlow:j_id5:j_id6", "LoginFlow:j_id5:j_id6"))

        status, loc, a4j2, _, _ = sess._run(
            "POST",
            flow_post_url,
            urlencode(post2),
            referer=flow_url,
            headers={"Accept": "*/*", "X-Requested-With": "XMLHttpRequest"},
        )
        if status != 200:
            raise RuntimeError(f"/LoginFlow A4J returned HTTP {status}")
        log["stages"].append("loginflow_a4j_post_ok")

        next2 = extract_a4j_redirect(a4j2, flow_url)
        if not next2:
            log["loginflow_a4j_excerpt"] = redact_text(a4j2[:8000], email, password)
            # Known post-success destination from live flow.
            # Extract source-bearing URL if present anywhere in response.
            m = re.search(
                r'(/setup/secur/RemoteAccessAuthorizationPage\.apexp\?source=[^"\'<>\s]+)',
                html.unescape(a4j2)
            )
            if m:
                next2 = urljoin(base, m.group(1))
            else:
                raise RuntimeError(
                    "LoginFlow completed, but RemoteAccessAuthorizationPage "
                    "redirect could not be extracted"
                )

        log["stages"].append("remote_authorization_redirect_extracted")

        # 3. Authenticated OAuth authorization page.
        status, loc, remote_html, _, remote_effective_url = sess._run("GET", next2, max_redirs=10)
        next2 = remote_effective_url
        log["stages"].append("remote_authorization_loaded")

        # Direct callback may already be final URL/body.
        m = re.search(r'(gsmoduser://tokens[^"\'<\s]+)', html.unescape(remote_html))
        callback = m.group(1) if m else None

        if not callback:
            action = extract_remote_action(remote_html, next2)
            if isinstance(action, str):
                if action.startswith("gsmoduser://"):
                    callback = action
                else:
                    st, lo, body3, hdr3, _ = sess._run("GET", action, max_redirs=0)
                    if lo and lo.startswith("gsmoduser://"):
                        callback = lo
                    else:
                        mm = re.search(
                            r'(gsmoduser://tokens[^"\'<\s]+)',
                            html.unescape(body3 + "\n" + hdr3)
                        )
                        if mm:
                            callback = mm.group(1)
            elif isinstance(action, tuple) and action[0] == "FORM":
                _, form, action_url = action
                pdata = salesforce_state_fields(remote_html, form)
                # Submit only page-provided hidden/default fields; this mirrors an
                # automatic approval form if Salesforce renders one.
                st, lo, body3, hdr3, _ = sess._run(
                    form["method"].upper(),
                    action_url,
                    urlencode(pdata) if form["method"] == "post" else None,
                    referer=next2,
                    max_redirs=0,
                )
                if lo and lo.startswith("gsmoduser://"):
                    callback = lo
                else:
                    mm = re.search(
                        r'(gsmoduser://tokens[^"\'<\s]+)',
                        html.unescape(body3 + "\n" + hdr3)
                    )
                    if mm:
                        callback = mm.group(1)

        if not callback:
            # We reached authenticated OAuth page over plain HTTP. Save structural
            # diagnostics only, never secrets.
            forms = parse_forms(remote_html)
            log["remote_auth_forms"] = [
                {
                    "id": f["id"],
                    "method": f["method"],
                    "action": safe_url(urljoin(next2, f["action"])),
                    "hidden_names": [k for k, _ in hidden_fields(f)],
                    "button_ids": [b["id"] for b in f["buttons"]],
                }
                for f in forms
            ]
            # Find likely action IDs without logging values/source.
            log["remote_auth_markers"] = sorted(set(
                re.findall(
                    r'(?i)\b(?:approve|authorize|allow|continue|deny|cancel)[A-Za-z0-9_:-]*',
                    remote_html
                )
            ))[:100]
            raise RuntimeError(
                "Plain HTTP login and LoginFlow succeeded; authenticated OAuth "
                "authorization page reached, but its final approval action still "
                "needs decoding. Upload the generated log."
            )

        log["callback_observed"] = True
        ok, names = save_tokens_from_callback(
            callback, Path.home() / ".config/cook4me/tokens.json"
        )
        log["callback_token_names"] = names
        log["tokens_saved"] = ok
        log["stages"].append("oauth_callback_received")

        print("Plain HTTP authentication complete.")
        print("Browser/Chromium    : not used")
        print("Callback observed   : yes")
        print("Tokens saved        :", "~/.config/cook4me/tokens.json" if ok else "no")

    except Exception as exc:
        log["error"] = f"{type(exc).__name__}: {redact_text(str(exc), email, password)}"
        print(f"Plain HTTP auth stopped: {type(exc).__name__}: {exc}")
    finally:
        try:
            cookiejar.unlink(missing_ok=True)
        except Exception:
            pass

        logfile.write_text(
            "KRUPS / COOK4ME PLAIN HTTP AUTH - SANITIZED\n"
            "No Playwright/Chromium. Credential/token/cookie values omitted.\n"
            + "=" * 80 + "\n"
            + json.dumps(log, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        os.chmod(logfile, 0o600)
        print("Sanitized log       :", logfile)
        if not log.get("callback_observed"):
            print("Upload that log file.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped with Ctrl+C.")
