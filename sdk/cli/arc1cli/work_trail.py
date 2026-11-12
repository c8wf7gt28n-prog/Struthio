"""Portable, bounded work-trail presentation; no execution or qualification."""
import re

VERSION = "arc.work-trail/1"
MAX_INTENTS = 256
MAX_LINKS = 8
MAX_ARTIFACTS = 64
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
STAGES = ("Intent", "Scope check", "Work", "Artifacts", "Outcome")


def ident(value):
    if not isinstance(value, str) or not re.fullmatch("[a-f0-9]{32}", value):
        raise ValueError("TRAIL_UNAVAILABLE")
    return value


def summary(row, jobs):
    states = sorted(set(j["lifecycle"] for j in jobs))
    return {
        "id": row["id"], "operation": row["operation"], "created": row["created"],
        "request_state": row["state"], "scope_check": row["scope_check"],
        "work": ", ".join(states) if states else "No registered job",
        "job_ids": [j["job_id"] for j in jobs],
        "label": row["operation"] + " · " + (", ".join(states) if states else row["state"]),
    }


def stages(row, jobs, artifacts):
    outcomes = [j["outcome"] for j in jobs]
    return [
        {"name": STAGES[0], "state": "RECORDED", "detail": row["operation"]},
        {"name": STAGES[1], "state": row["scope_check"],
         "detail": "Scope allowed or denied. Exact-source and object grants are checked separately."},
        {"name": STAGES[2], "state": ", ".join(sorted(set(j["lifecycle"] for j in jobs))) if jobs else "NO_REGISTERED_JOB",
         "detail": "Recorded job lifecycle; the request returns separately."},
        {"name": STAGES[3], "state": "CHECKS_RECORDED" if artifacts else "NO_REGISTERED_ARTIFACTS",
         "detail": str(len(artifacts)) + " registered artifact(s). Current-byte observations below."},
        {"name": STAGES[4], "state": ", ".join(outcomes) if outcomes else row["state"],
         "detail": "Recorded result. Acceptance and physical qualification remain separate."},
    ]

