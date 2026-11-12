"""SW-001 portable logical-window metadata and presentation bounds."""
from __future__ import annotations
import math
import re
from .object_context import selector

VERSION = "arc.slate-window/1"
MAX_WINDOWS = 32
MAX_DEVICES = 16
MAX_RECORD = 16 * 1024
MAX_SNAPSHOT = 16 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
DEFAULT_LAYOUT = {"view": "overview", "scroll": 0, "zoom": 1.0, "collapsed": False}


def window_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"sw_[a-f0-9]{32}", value):
        raise ValueError("WINDOW_UNAVAILABLE")
    return value


def presentation(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULT_LAYOUT):
        raise ValueError("WINDOW_PRESENTATION_FIELDS")
    result = dict(DEFAULT_LAYOUT, **value)
    if result["view"] != "overview" or type(result["scroll"]) is not int or not 0 <= result["scroll"] <= 10_000_000:
        raise ValueError("WINDOW_PRESENTATION_RANGE")
    if type(result["zoom"]) not in (int, float) or not math.isfinite(result["zoom"]) or not .5 <= result["zoom"] <= 3:
        raise ValueError("WINDOW_PRESENTATION_RANGE")
    if type(result["collapsed"]) is not bool:
        raise ValueError("WINDOW_PRESENTATION_RANGE")
    return result


def overview(context):
    """Explicitly published metadata only; no source text, paths or action args."""
    return {
        "object": selector(context["selector"]),
        "object_id": context["object_id"],
        "source_revision": context["revision"],
        "title": context["title"][:300],
        "authority": context["authority"],
        "source_count": len(context["sources"]),
        "evidence_count": len(context["evidence"]),
        "gaps": [str(g)[:180] for g in context["gaps"][:8]],
    }


def snapshot(row, layout):
    return {
        "schema": VERSION, "window_id": window_id(row["id"]),
        "kind": "engineering.inspector", "state": "AVAILABLE",
        "state_revision": row["generation"], "mode": "read",
        **row["overview"], "views": ["overview"], "available_actions": [],
        "presentation": presentation(layout),
        "physical_qualification": False,
        "notice": "Published overview only. Source text and engineering actions require separate checked views.",
    }

