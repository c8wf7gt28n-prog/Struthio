"""Owner-hosted PWA/API: local HTTP, direct TLS, or owner HTTPS proxy.

No relay, CDN, login service, shell or physical programmer is required. Opening
a non-loopback listener requires an explicit interface and owner certificate.
Sessions survive a same-policy service restart; revocation is an owner action.
"""

from __future__ import annotations
import hashlib
import ipaddress
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import platform
from pathlib import Path
import secrets
import socket
import ssl
import threading
import time
from urllib.parse import urlsplit
from .engineering_kernel import Principal
from sdk.cli.arc1cli.record_visibility import REMOTE_OPERATIONS as LEGACY_REMOTE_OPERATIONS
from sdk.cli.arc1cli.window_views import REMOTE_OPERATIONS as DECK_OPERATIONS
from . import locations

# Four read/presentation routes, individually protected by live per-view grants.
# The pre-existing reviewed SDK operation set is byte preserved.
REMOTE_OPERATIONS = LEGACY_REMOTE_OPERATIONS | DECK_OPERATIONS | {'deployment.progress'}

REMOTE_PATHS = ("software/arcos/src/", "software/arcos/games/", "software/struthio/")
REMOTE_TOOLS = ("arcos.build", "arcos.test", "arcos.dependencies", "struthio.build",
                "struthio.test", "struthio.replay", "console.build", "console.lifecycle",
                "book.refresh", "diagnostic.compare", "clip.loop")


def validate_origin(origin):
    parsed = urlsplit(origin)
    if (parsed.path or parsed.query or parsed.fragment or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or any(c.isspace() for c in origin) or parsed.port == 0):
        raise ValueError("Origin must be scheme://host[:port], without a path or credentials")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")):
        raise ValueError("Phone access requires HTTPS; HTTP is local-only")
    return parsed


class RemoteServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, kernel, port, origin, allow_approvals=False, *, bind="127.0.0.1", cert=None, key=None, profile="develop"):
        parsed = validate_origin(origin)
        address = ipaddress.ip_address(bind)
        if profile not in ("view", "develop", "owner"):
            raise ValueError("Unknown pairing profile")
        if allow_approvals:
            profile = "owner"  # compatible explicit legacy owner switch
        if bool(cert) != bool(key):
            raise ValueError("Supply both owner certificate and private key")
        if not address.is_loopback and not cert:
            raise ValueError("A non-loopback interface requires direct TLS with owner certificate/key")
        if cert and parsed.scheme != "https":
            raise ValueError("TLS listener requires an HTTPS origin")
        self.tls_context = None
        if cert:
            key_path = Path(key).resolve()
            if key_path.is_relative_to(kernel.root) and not key_path.is_relative_to(kernel.state):
                raise ValueError("Keep the TLS private key outside active sources (or under private .ledger)")
            self.tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.tls_context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.tls_context.load_cert_chain(str(cert), str(key))
        if address.version == 6:
            self.address_family = socket.AF_INET6
        self.kernel = kernel
        self.origin = origin
        self.secure = parsed.scheme == "https"
        self.pair_code = secrets.token_urlsafe(24)
        self.pair_expiry = time.time() + 300
        self.profile = profile
        self.scopes = ["read"] if profile == "view" else ["read", "execute", "candidate"]
        if profile == "owner": self.scopes.append("approve")
        self.paths = list(REMOTE_PATHS) if profile != "view" else []
        self.tools = list(REMOTE_TOOLS) if profile != "view" else []
        self.policy = hashlib.sha256(json.dumps({"version": 3, "operations":sorted(REMOTE_OPERATIONS), "origin": origin, "profile": profile,
            "scopes": self.scopes, "paths": self.paths, "tools": self.tools}, sort_keys=True).encode()).hexdigest()
        self.allow_approvals = profile == "owner"
        self.lock = threading.Lock()
        self.clients = threading.BoundedSemaphore(16)
        self.rates = {}
        super().__init__((bind, port), Handler)
        with kernel.db() as db:
            # Old grants are retained only when their exact policy matches.
            for token, payload in db.execute("SELECT token,payload FROM sessions").fetchall():
                data = json.loads(payload)
                if data.get("policy") != self.policy or data.get("expires", 0) < time.time():
                    db.execute("DELETE FROM sessions WHERE token=?", (token,))
            db.execute(
                "INSERT OR REPLACE INTO settings VALUES('remote_enabled','true')"
            )

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        if self.tls_context:
            try:
                connection = self.tls_context.wrap_socket(connection, server_side=True)
            except (OSError, ssl.SSLError):
                connection.close()
                raise
        return connection, address

    def process_request(self, request, address):
        if not self.clients.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.clients.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.clients.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "ArcLedger/13D"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *args):
        pass  # Never log pairing codes, sessions or request bodies.

    def send(self, status, data, ctype="application/json"):
        if not isinstance(data, bytes):
            data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache"
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            # A phone disconnect does not cancel or undo the durable operation.
            pass

    def validate(self, mutation=False):
        expected = urlsplit(self.server.origin).netloc
        accepted = {expected}
        if not self.server.secure:
            accepted.add("127.0.0.1:" + str(self.server.server_port))
        if self.headers.get("Host") not in accepted:
            self.send(403, {"error": "Host rejected"})
            return False
        if mutation and self.headers.get("Origin") != self.server.origin:
            self.send(403, {"error": "Origin rejected"})
            return False
        with self.server.kernel.db() as db:
            row = db.execute(
                "SELECT value FROM settings WHERE key='remote_enabled'"
            ).fetchone()
        if not row or row[0] != "true":
            self.send(503, {"error": "Remote disabled by operator"})
            return False
        with self.server.lock:
            key = self.client_address[0]
            t = time.time()
            entries = [x for x in self.server.rates.get(key, []) if t - x < 60]
            if len(entries) >= 120:
                self.send(429, {"error": "Rate limit; retry later"})
                return False
            if key not in self.server.rates and len(self.server.rates) >= 512:
                self.server.rates = {ip: [x for x in times if t-x < 60] for ip, times in self.server.rates.items() if times and t-times[-1] < 60}
                if len(self.server.rates) >= 512:
                    self.send(429, {"error": "Connection capacity; retry later"})
                    return False
            self.server.rates[key] = entries + [t]
        return True

    def session(self, mutation=False):
        try:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookies["ledger_session"].value
            hashed = hashlib.sha256(token.encode()).hexdigest()
            with self.server.kernel.db() as db:
                row = db.execute(
                    "SELECT payload FROM sessions WHERE token=?", (hashed,)
                ).fetchone()
            data = json.loads(row[0]) if row else {}
            if data.get("expires", 0) < time.time() or data.get("policy") != self.server.policy:
                raise ValueError("Expired session")
            if mutation and not secrets.compare_digest(
                self.headers.get("X-Ledger-CSRF", ""), data["csrf"]
            ):
                raise ValueError("CSRF validation failed")
            return data, hashed
        except (KeyError, ValueError, TypeError):
            self.send(401, {"error": "Pair this device with the local operator"})
            return None, None

    def do_GET(self):
        if not self.validate():
            return
        if self.path == "/api/session":
            s, _ = self.session()
            if s:
                self.send(
                    200,
                    {
                        "identity": s["identity"],
                        "csrf": s["csrf"],
                        "scopes": s["scopes"],
                        "online": True,
                        "expires": s["expires"],
                        "device_name": s.get("device_name", "Paired iPhone"),
                        "host_platform": platform.system(),
                        "release": "Ledger and Slate 13D Development candidate",
                        "paths": s["paths"], "tools": s["tools"], "profile": s["profile"],
                        "operations":sorted(REMOTE_OPERATIONS),
                        "owner_hosted": True, "tls_transport": "direct" if self.server.tls_context else "owner-proxy" if self.server.secure else "local-http",
                    },
                )
            return
        if self.path == "/api/frame":
            s, _ = self.session()
            if not s:
                return
            frame = self.server.kernel.root / "build/native_struthio/frame.png"
            if not frame.is_file():
                self.send(404, {"error": "No host-captured PNG frame available"})
                return
            self.send(200, frame.read_bytes(), "image/png")
            return
        files = {
            "/": "index.html",
            "/app.js": "app.js",
            "/deck.js": "deck.js",
            "/slate-icon-192.png": "slate-icon-192.png",
            "/slate-icon-512.png": "slate-icon-512.png",
            "/style.css": "style.css",
            "/manifest.webmanifest": "manifest.webmanifest",
            "/sw.js": "sw.js",
            "/icon.svg": "icon.svg",
            "/icon-192.png": "icon-192.png",
            "/icon-512.png": "icon-512.png",
            "/apple-touch-icon.png": "apple-touch-icon.png",
        }
        name = files.get(self.path)
        nav = {"/nav-clip.svg": "clip", "/nav-workspace.svg": "brain-link", "/nav-game.svg": "game",
               "/nav-jobs.svg": "jobs", "/nav-evidence.svg": "evidence"}
        if self.path in nav:
            from sdk.cli.arc1cli.ui_assets import AssetPack
            self.send(200, AssetPack(locations.program(self.server.kernel.root)).svg(nav[self.path], "dark"), "image/svg+xml")
            return
        if self.path == '/slate-sheet.png':
            from . import record_io
            base=locations.program(self.server.kernel.root)/'branding/slate';data=record_io.strict_json((base/'assets.json').read_bytes())
            row=data['files']['slate_keyposes.png'];raw=(base/'slate_keyposes.png').read_bytes()
            if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
                self.send(503,{'error':'Graphite artwork unavailable'});return
            self.send(200,raw,'image/png');return
        if self.path == '/reading-cjk.otf':
            font=locations.program(self.server.kernel.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'
            self.send(200,font.read_bytes(),'font/otf');return
        if self.path in ("/clip.png", "/stacy.png", "/stacy-avatar.png"):
            name = "stacy-avatar.png" if self.path == "/stacy-avatar.png" else "stacy.png"
            self.send(200, (locations.program(self.server.kernel.root) / "branding/stacy" / name).read_bytes(), "image/png")
            return
        if not name:
            self.send(404, {"error": "Not found"})
            return
        types = {
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript",
            ".css": "text/css",
            ".webmanifest": "application/manifest+json",
            ".svg": "image/svg+xml",
            ".png": "image/png",
        }
        file = Path(__file__).parent / "remote_pwa" / name
        self.send(200, file.read_bytes(), types[file.suffix])

    def do_POST(self):
        if not self.validate(True):
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if (
                not 0 < length <= 1200000
                or self.headers.get("Content-Type", "").split(";")[0]
                != "application/json"
            ):
                raise ValueError("JSON body required; maximum 1.2 MB")
            from .record_io import strict_json
            body = strict_json(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Expected object")
        except (ValueError, TypeError, RecursionError):
            self.send(400, {"error": "Invalid request body"})
            return
        if self.path == "/api/pair":
            device_name = body.get("device_name", "Paired iPhone")
            if not isinstance(device_name, str) or not 1 <= len(device_name.strip()) <= 60:
                self.send(400, {"error": "Device name must contain 1–60 characters"})
                return
            with self.server.lock:
                if (
                    time.time() > self.server.pair_expiry
                    or not self.server.pair_code
                    or not secrets.compare_digest(
                        str(body.get("code", "")), self.server.pair_code
                    )
                ):
                    self.server.kernel.audit("unpaired", "remote.pair", "DENIED")
                    self.send(
                        401, {"error": "Invalid or expired one-time pairing code"}
                    )
                    return
                self.server.pair_code = None
            token = secrets.token_urlsafe(32)
            hashed = hashlib.sha256(token.encode()).hexdigest()
            scopes = list(self.server.scopes)
            data = {
                "identity": "remote-device-" + secrets.token_hex(6),
                "scopes": scopes,
                "csrf": secrets.token_urlsafe(24),
                "expires": time.time() + 12 * 3600,
                "device_name": device_name.strip(),
                "paths": self.server.paths, "tools": self.server.tools,
                "profile": self.server.profile, "policy": self.server.policy, "created": time.time(),
            }
            with self.server.kernel.db() as db:
                db.execute(
                    "INSERT INTO sessions VALUES(?,?)", (hashed, json.dumps(data))
                )
            self.server.kernel.audit(data["identity"], "remote.pair", "OK")
            encoded = json.dumps(
                {"paired": True, "csrf": data["csrf"], "scopes": scopes}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Set-Cookie",
                "ledger_session="
                + token
                + "; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200"
                + ("; Secure" if self.server.secure else ""),
            )
            self.end_headers()
            self.wfile.write(encoded)
            return
        s, token = self.session(True)
        if not s:
            return
        if self.path == "/api/revoke":
            with self.server.kernel.db() as db:
                db.execute("DELETE FROM sessions WHERE token=?", (token,))
            self.server.kernel.audit(s["identity"], "remote.revoke", "OK")
            self.send(200, {"revoked": True})
            return
        if self.path != "/api/call":
            self.send(404, {"error": "Not found"})
            return
        principal = Principal(s["identity"], frozenset(s["scopes"]), tuple(s["paths"]), tuple(s["tools"]))
        if not isinstance(body.get('operation'),str) or body['operation'] not in REMOTE_OPERATIONS:
            self.send(403,{'error':'Operation is not enabled for paired devices'})
            return
        result = self.server.kernel.dispatch(
            body.get("operation"), body.get("params", {}), principal
        )
        # A revoked/expired device must not receive a late read result. Effects
        # already committed by the Kernel remain durable and may be ambiguous
        # to the disconnected client; its original request key is still required.
        current, _ = self.session()
        if not current:return
        grant_fields=('identity','scopes','paths','tools','profile','policy','csrf')
        if any(current.get(k)!=s.get(k) for k in grant_fields):
            self.send(403,{'error':'Device grants changed during request'});return
        with self.server.kernel.db() as db:
            enabled=db.execute("SELECT value FROM settings WHERE key='remote_enabled'").fetchone()
        if not enabled or enabled[0]!='true':
            self.send(503,{'error':'Remote disabled by operator'});return
        if result['ok'] and body.get('operation')=='capabilities':
            result['result']['operations']={k:v for k,v in result['result']['operations'].items() if k in REMOTE_OPERATIONS}
            result['result']['schemas']={k:v for k,v in result['result']['schemas'].items() if k in REMOTE_OPERATIONS}
        self.send(200 if result["ok"] else 400, result)


def serve(kernel, port, origin, allow_approvals=False, **config):
    server = RemoteServer(kernel, port, origin, allow_approvals, **config)
    print(
        "Owner-hosted service. Transport: " + ("direct TLS" if server.tls_context else "owner proxy" if server.secure else "local HTTP only"),
        flush=True,
    )
    print("One-time pairing code (5 minutes): " + server.pair_code, flush=True)
    print(
        "Origin: " + origin + " | pairing profile: " + server.profile,
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
