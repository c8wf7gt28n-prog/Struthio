"""Small provider/GUI-independent contract for source-bound agent proposals.

This validates data; it grants no file access, process execution or acceptance.
An agent's runtime name and explanation are declarations, not authentication.
"""
from __future__ import annotations
import hashlib
import json

CONTRACT = "arc-ledger.agent-task/1"
MAX_CONTEXT = 60000
MAX_OUTPUT = 100000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def binding(task_id, revision, files, tool):
    body = {"schema": CONTRACT, "task": task_id, "revision": revision,
            "files": files, "test_tool": tool}
    return sha(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())


def validate_proposal(proposal, *, expected_binding, files):
    """Accept one exact UTF-8 file edit, bound to the handoff's source hashes."""
    if not isinstance(proposal, dict) or set(proposal) != {"binding", "agent", "explanation", "patch"}:
        raise ValueError("Expected binding, agent, explanation and one patch")
    if len(json.dumps(proposal).encode()) > MAX_OUTPUT:
        raise ValueError("Agent output exceeds 100000 bytes")
    if proposal["binding"] != expected_binding:
        raise ValueError("Stale agent context; request the current handoff")
    for key, cap in (("agent", 160), ("explanation", 4000)):
        if not isinstance(proposal[key], str) or not 1 <= len(proposal[key].strip()) <= cap:
            raise ValueError("Invalid agent " + key)
    patch = proposal["patch"]
    if not isinstance(patch, dict) or set(patch) != {"path", "sha256", "content"}:
        raise ValueError("Expected path, sha256 and complete UTF-8 content")
    if not isinstance(patch["path"], str) or patch["path"] not in files:
        raise ValueError("Proposal exceeds the delegated file scope")
    if patch["sha256"] != files[patch["path"]]:
        raise ValueError("Proposal source hash does not match the handoff")
    if not isinstance(patch["content"], str) or not patch["content"] or "\0" in patch["content"]:
        raise ValueError("Proposal must contain nonempty UTF-8 source")
    data = patch["content"].encode("utf-8")
    if sha(data) == patch["sha256"]:
        raise ValueError("Proposal contains no source change")
    return dict(patch)
