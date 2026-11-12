"""Local-owner controls for individual paired-device revocation.

Public rows never expose the hashed cookie token, CSRF secret or pairing code.
The authenticated transport retains all session-grant authority.
"""
import json
import time

FIELDS = {
    "remote.sessions": ({}, []),
    "remote.revoke": ({"identity": {"type": "string", "minLength": 1, "maxLength": 100}}, ["identity"]),
}
SCOPES = {"remote.sessions": "read", "remote.revoke": "approve"}


def dispatch(k, op, a, p):
    with k.db() as db:
        if op == "remote.revoke":
            db.execute("BEGIN IMMEDIATE")
        rows = [(token, json.loads(payload)) for token, payload in db.execute("SELECT token,payload FROM sessions")]
        if op == "remote.sessions":
            return [{key: s.get(key) for key in ("identity", "device_name", "scopes", "paths", "tools", "created", "expires", "profile")}
                    for _, s in rows if s.get("expires", 0) > time.time()]
        count = 0
        for token, data in rows:
            if data.get("identity") == a["identity"]:
                db.execute("DELETE FROM sessions WHERE token=?", (token,))
                count += 1
        return {"identity": a["identity"], "revoked_sessions": count, "durable_jobs_preserved": True}
