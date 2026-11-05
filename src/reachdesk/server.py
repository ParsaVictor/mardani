"""Local dashboard server. Binds to loopback and refuses cross-site requests."""
from __future__ import annotations

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import __version__, channels, db, plans, scoring, service

MAX_BODY = 25_000_000
STATIC = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class Retrainer:
    """Re-ranks after ratings without making the dashboard wait.

    Several quick ratings collapse into one training run.
    """

    def __init__(self, db_path: str, debounce: float = 0.5):
        self.db_path, self.debounce = db_path, debounce
        self.pending: set[int] = set()
        self.lock = threading.Lock()
        self.wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def request(self, campaign_id: int) -> None:
        with self.lock:
            self.pending.add(campaign_id)
        self.wake.set()

    def _loop(self) -> None:
        while True:
            self.wake.wait()
            time.sleep(self.debounce)
            self.wake.clear()
            with self.lock:
                batch, self.pending = self.pending, set()
            conn = db.connect(self.db_path)
            try:
                for campaign_id in batch:
                    service.retrain(conn, campaign_id)
            except Exception as exc:  # a failed run must not stop later ones
                service.audit(conn, "retrain_error", str(exc)[:300])
                conn.commit()
            finally:
                conn.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "ReachDesk"
    db_path: str = ""

    def log_message(self, *args):  # contacts' data must not end up in console logs
        pass

    # ------------------------------------------------------------ protection
    def _allowed_hosts(self) -> set[str]:
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") in self._allowed_hosts()

    def _write_ok(self) -> bool:
        """A custom header cannot be sent cross-site without a preflight, which we refuse."""
        origin = self.headers.get("Origin", "")
        if origin and urlsplit(origin).netloc not in self._allowed_hosts():
            return False
        return self.headers.get("X-ReachDesk") == "1"

    def _refuse(self, reason: str) -> None:
        """Read the unwanted body first: closing with unread data can reset the reply away."""
        try:
            length = min(int(self.headers.get("Content-Length") or 0), MAX_BODY)
            if length > 0:
                self.connection.settimeout(5)  # a client that never sends must not hold a thread
                self.rfile.read(length)
        except (ValueError, OSError):
            self.close_connection = True
        self._json({"error": reason}, 403)

    # --------------------------------------------------------------- replies
    def _send(self, status: int, payload: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        for key, value in {**SECURITY_HEADERS, **(extra or {})}.items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(payload)
        except ConnectionError:  # the browser navigated away; nothing to do
            self.close_connection = True

    def _json(self, data, status: int = 200) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("request too large")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw or b"{}")
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        return data

    def _run(self, method: str) -> None:
        if not self._host_ok():
            return self._refuse("forbidden host")
        parts = urlsplit(self.path)
        if method == "POST" and not self._write_ok():
            return self._refuse("forbidden origin")
        if method == "GET" and parts.path in STATIC:
            name, ctype = STATIC[parts.path]
            return self._send(200, resources.files("reachdesk").joinpath("static", name).read_bytes(), ctype)
        conn = db.connect(self.db_path)
        try:
            query = {k: v[0] for k, v in parse_qs(parts.query).items()}
            body = self._body() if method == "POST" else {}
            result = route(conn, method, parts.path, query, body, self.server.retrainer.request)
            if isinstance(result, tuple):
                return self._send(200, result[0].encode("utf-8"), result[1], {"Content-Disposition": 'attachment; filename="reachdesk-export.csv"'})
            return self._json(result)
        except service.LimitError as exc:
            return self._json({"error": str(exc), "upgrade": True}, 402)
        except KeyError as exc:
            return self._json({"error": f"not found: {exc}"}, 404)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._json({"error": str(exc)}, 400)
        finally:
            conn.close()

    def do_GET(self):
        self._run("GET")

    def do_POST(self):
        self._run("POST")


def route(conn, method: str, path: str, q: dict, b: dict, request_retrain):
    """All API routes. Returns JSON-able data, or (text, content_type) for downloads."""
    if method == "GET":
        if path == "/api/bootstrap":
            return {
                "version": __version__, "campaigns": service.list_campaigns(conn), "plan": service.plan(conn),
                "plans": plans.PLANS, "reasons": scoring.REASONS, "consent_bases": service.CONSENT_BASES,
                "smtp": {k: service.get_setting(conn, k) for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_from", "email_attachment")},
                "smtp_password_set": bool(channels.smtp_config(conn)["password"]),
            }
        cid = int(q.get("campaign", 0))
        if path == "/api/items":
            return service.list_items(conn, cid, q.get("kind", ""), q.get("status", ""), q.get("q", ""), float(q.get("min", 0) or 0), int(q.get("limit", 100)), int(q.get("offset", 0)))
        if path == "/api/queue":
            return service.list_queue(conn, cid, q.get("status", "ready"))
        if path == "/api/insights":
            return service.insights(conn, cid)
        if path == "/api/searches":
            campaign = service.get_campaign(conn, cid)
            if not campaign:
                raise KeyError(cid)
            return service.search_links(campaign)
        if path == "/api/variants":
            return service.list_variants(conn, cid)
        if path == "/api/export":
            return service.export_items(conn, cid), "text/csv; charset=utf-8"
        return _not_found()

    if path == "/api/campaigns":
        slug = re.sub(r"[^a-z0-9-]+", "-", (b.get("name") or "campaign").lower()).strip("-") or "campaign"
        return service.create_campaign(conn, slug, b.get("name") or slug)
    if path == "/api/license":
        token = (b.get("token") or "").strip()
        if token and not plans.read_license(token):
            raise ValueError("this license key is not valid or has expired")
        service.set_setting(conn, "license", token)
        return service.plan(conn)
    if path == "/api/settings":
        for key in ("smtp_host", "smtp_port", "smtp_user", "smtp_from", "email_attachment"):
            if key in b:
                service.set_setting(conn, key, str(b[key]))
        return {"ok": True}

    match = re.fullmatch(r"/api/campaigns/(\d+)(?:/(\w+))?", path)
    if match:
        cid, action = int(match.group(1)), match.group(2)
        if not service.get_campaign(conn, cid):
            raise KeyError(cid)
        if action is None:
            return service.update_campaign(conn, cid, b)
        if action == "paste":
            return _pair(service.paste_item(conn, cid, b.get("text", ""), b.get("url", ""), b.get("location", ""), b.get("kind", "")))
        if action == "import":
            return service.import_csv(conn, cid, b.get("csv", ""))
        if action == "fetch":
            return service.fetch_sources(conn, cid)
        if action == "queue":
            return service.build_queue(conn, cid)
        if action == "dispatch":
            return channels.dispatch_email(conn, cid)
        if action == "variant":
            return service.save_variant(conn, cid, b["name"], b["body"], b.get("step", "message"), bool(b.get("active", True)))
        return _not_found()

    match = re.fullmatch(r"/api/items/(\d+)/(\w+)", path)
    if match:
        iid, action = int(match.group(1)), match.group(2)
        if action == "rate":
            item = service.rate_item(conn, iid, int(b["stars"]), b.get("reason", ""), retrain_now=False)
            request_retrain(item["campaign_id"])
            return item
        if action == "status":
            service.set_item_status(conn, iid, b["status"])
            return {"ok": True}
        if action == "update":
            return service.set_item_fields(conn, iid, b)
        if action == "accepted":
            return service.mark_accepted(conn, iid)
        if action == "forget":
            service.forget_item(conn, iid)
            return {"ok": True}
        return _not_found()

    match = re.fullmatch(r"/api/outreach/(\d+)/(\w+)", path)
    if match:
        oid, action = int(match.group(1)), match.group(2)
        if action == "sent":
            return service.mark_sent(conn, oid)
        if action == "skip":
            service.skip_draft(conn, oid)
            return {"ok": True}
        if action == "edit":
            service.edit_draft(conn, oid, b["body"])
            return {"ok": True}
        if action == "reply":
            service.record_reply(conn, oid, bool(b.get("positive")), bool(b.get("opt_out")))
            return {"ok": True}
    return _not_found()


def _pair(result: tuple[dict, bool]) -> dict:
    return {"item": result[0], "created": result[1]}


def _not_found():
    raise KeyError("route")


def auto_loop(db_path: str, stop: threading.Event, interval: float = 900.0) -> None:
    """Keep automatic-email campaigns moving while the dashboard is running."""
    while not stop.wait(interval):
        conn = db.connect(db_path)
        try:
            for campaign in service.list_campaigns(conn):
                if campaign["auto_email"]:
                    service.build_queue(conn, campaign["id"])
                    channels.dispatch_email(conn, campaign["id"])
        except Exception as exc:  # the loop must survive a bad network or SMTP moment
            service.audit(conn, "auto_loop_error", str(exc)[:300])
            conn.commit()
        finally:
            conn.close()


def make_server(db_path: str | Path, port: int = 8765) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"db_path": str(db_path)})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.retrainer = Retrainer(str(db_path))
    return server


def serve(db_path: str | Path, port: int = 8765) -> None:
    server = make_server(db_path, port)
    stop = threading.Event()
    threading.Thread(target=auto_loop, args=(str(db_path), stop), daemon=True).start()
    print(f"ReachDesk is running at http://127.0.0.1:{server.server_address[1]}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
