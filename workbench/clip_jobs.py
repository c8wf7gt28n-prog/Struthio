"""Bounded provider-neutral Clip jobs. Providers propose; the kernel authorizes.

The deterministic provider is an explicit offline test adapter, not an AI model.
Gemini uses the existing per-user credential adapter and requires source-sharing
consent. External agents can use MCP/JSONL without adopting either provider.
"""

from __future__ import annotations
import json
import time
import uuid
from .engineering_kernel import KernelError, Principal
from .project_inventory import hashes, revision


def submit(kernel, a, p):
    if not {"candidate", "execute"} <= p.scopes:
        raise KernelError("Clip engineering tasks need candidate and execute scopes")
    goal = a.get("goal")
    paths = a.get("paths")
    iterations = a.get("max_iterations", 1)
    runtime = a.get("max_runtime", 300)
    provider = a.get("provider", "deterministic")
    tool = a.get("test_tool", "struthio.test")
    budget = a.get("max_provider_calls", iterations)
    if not isinstance(goal, str) or not goal.strip() or len(goal) > 2000:
        raise KernelError("A bounded engineering goal is required")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 5:
        raise KernelError("Approve one to five exact source files")
    for path in paths:
        file = kernel.safe(path)
        if (
            not any(path.startswith(prefix) for prefix in p.paths)
            or file.name.startswith("test_")
            or file.suffix not in (".c", ".h")
            or file.name == "struthio_tower_generated.h"
        ):
            raise KernelError("Clip file scope is not authorized")
    if (
        type(iterations) != int
        or not 1 <= iterations <= 3
        or type(budget) != int
        or not 0 <= budget <= 3
    ):
        raise KernelError("Iteration/provider-call limits: 1–3 / 0–3")
    if type(runtime) != int or not 10 <= runtime <= 600:
        raise KernelError("Task runtime must be 10–600 seconds")
    if provider not in ("deterministic", "gemini"):
        raise KernelError(
            "Provider unavailable; external agents should use MCP candidate services"
        )
    if provider == "gemini" and not a.get("share_source"):
        raise KernelError("Explicit consent required to send scoped source to Gemini")
    if tool not in p.tools or tool not in ("struthio.test", "diagnostic.compare"):
        raise KernelError("Regression tool not authorized")
    rounds = a.get("proposals", [])
    if provider == "deterministic" and (
        not isinstance(rounds, list) or not 1 <= len(rounds) <= iterations
    ):
        raise KernelError(
            "Deterministic test adapter requires one proposal list per iteration"
        )
    if len(json.dumps(rounds)) > 500000:
        raise KernelError("Proposal budget exceeded")
    key = a.get('request_key', uuid.uuid4().hex)
    if not isinstance(key, str) or not 1 <= len(key) <= 128:
        raise KernelError('Invalid idempotency key')
    request_spec = {k: v for k, v in a.items() if k != 'request_key'}
    id = uuid.uuid4().hex
    j = {
        "id": id,
        "owner": p.identity,
        "state": "Waiting for Approval",
        "goal": goal,
        "tool": "clip.loop",
        "candidate": None,
        "revision": revision(hashes(kernel.root)),
        "scope": paths,
        "timeout": runtime,
        "iteration_limit": iterations,
        "provider_budget": {
            "max_calls": budget,
            "max_context_bytes": 60000,
            "max_output_bytes": 100000,
            "currency_cost_measured": False,
        },
        "task": {
            "provider": provider,
            "test_tool": tool,
            "proposals": rounds,
            "share_source": bool(a.get("share_source")),
        },
        "authorized_tools": [tool],
        "created": time.time(),
        "cancel": False,
        "pause": False,
        "pid": None,
        "approval_required": True,
        "current_operation": "Review file/tool/runtime/provider scope",
        "iterations": [],
        "provider_calls": 0,
        "request_spec": request_spec,
    }
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT job FROM requests WHERE owner=? AND key=?', (p.identity, key)).fetchone()
        if old:
            prior = kernel.record('jobs', old[0])
            if prior['tool'] != 'clip.loop' or prior.get('request_spec') != request_spec:
                raise KernelError('Idempotency key reused with different request')
            return prior
        kernel.save('jobs', j, db)
        db.execute('INSERT INTO requests VALUES(?,?,?)', (p.identity, key, id))
    return j


class DeterministicProvider:
    name = "deterministic-test-adapter"

    def propose(self, task, index, context):
        rounds = task["proposals"]
        return rounds[index] if index < len(rounds) else []


class GeminiProvider:
    name = "gemini"

    def propose(self, task, index, context):
        from .clip import Settings, generate

        settings = Settings.load()
        if not settings.ready() or not settings.model:
            raise KernelError(
                "Configure a Gemini key and explicit model in Clip before autonomous use"
            )
        prompt = (
            "Propose one reversible C change for this approved task. Return ONLY a JSON array of objects with path, sha256, content. "
            "No shell commands, no additional files, no tests or generated constants changes. Empty array means no justified improvement.\n"
            + json.dumps(context)
        )
        result = generate(
            settings.api_key(),
            settings.model,
            [("user", prompt)],
            timeout=context["timeout"],
        )
        if len(result.encode()) > 100000:
            raise KernelError("Provider output budget exceeded")
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)


def run(kernel, id):
    j = kernel.record("jobs", id)
    start = time.monotonic()
    spent = j.get("runtime_used", 0)
    p = Principal(
        j["owner"],
        frozenset({"read", "candidate", "execute"}),
        tuple(j["scope"]),
        tuple(j["authorized_tools"]),
        mode="Autonomous",
    )
    if not j.get("authorized_by"):
        raise KernelError("Task has no operator authorization")
    child = None
    candidate = None

    def update(**values):
        nonlocal j
        with kernel.db() as db:
            db.execute("BEGIN IMMEDIATE")
            live = kernel.record("jobs", id)
            live.update(values)
            live["runtime_used"] = spent + time.monotonic() - start
            kernel.save("jobs", live, db)
            j = live

    def check():
        live = kernel.record("jobs", id)
        if live.get("cancel"):
            raise KernelError("Paused" if live.get("pause") else "Cancelled")
        if spent + time.monotonic() - start >= j["timeout"]:
            raise KernelError("Task runtime limit reached")

    def call(op, params):
        r = kernel.dispatch(op, params, p)
        if not r["ok"]:
            raise KernelError(r["error"]["message"])
        return r["result"]

    def test(candidate=None):
        nonlocal child
        check()
        a = {
            "tool": j["task"]["test_tool"],
            "timeout": max(
                1, min(120, j["timeout"] - spent - (time.monotonic() - start))
            ),
            "request_key": uuid.uuid4().hex,
            "goal": j["goal"],
        }
        if candidate:
            a["candidate"] = candidate
        child = call("jobs.submit", a)["id"]
        update(child=child)
        while True:
            check()
            record = kernel.record("jobs", child)
            if record["state"] not in ("Queued", "Running"):
                return record
            time.sleep(0.1)

    try:
        if revision(hashes(kernel.root)) != j["revision"]:
            raise KernelError("Source changed after scope approval")
        update(current_operation="Baseline regression tests")
        baseline = test()
        update(baseline=baseline["id"])
        if baseline["state"] != "Completed":
            raise KernelError("Baseline failed; investigate before autonomous changes")
        provider = (
            GeminiProvider()
            if j["task"]["provider"] == "gemini"
            else DeterministicProvider()
        )
        for iteration in range(len(j["iterations"]), j["iteration_limit"]):
            check()
            if j["provider_calls"] >= j["provider_budget"]["max_calls"]:
                raise KernelError("Provider-call budget exhausted")
            context = {
                "goal": j["goal"],
                "files": [call("files.read", {"path": path}) for path in j["scope"]],
                "previous_iterations": j["iterations"],
                "timeout": max(
                    1, min(60, j["timeout"] - spent - (time.monotonic() - start))
                ),
            }
            if (
                len(json.dumps(context).encode())
                > j["provider_budget"]["max_context_bytes"]
            ):
                raise KernelError("Source context budget exceeded")
            update(
                current_operation="Provider proposal %d/%d"
                % (iteration + 1, j["iteration_limit"]),
                provider_calls=j["provider_calls"] + 1,
            )
            proposals = provider.propose(j["task"], iteration, context)
            check()
            if not proposals:
                update(
                    state="Completed", current_operation="No justified change proposed"
                )
                break
            if not isinstance(proposals, list) or len(proposals) > len(j["scope"]):
                raise KernelError("Provider returned an invalid proposal")
            candidate = call(
                "candidates.create",
                {
                    "goal": j["goal"],
                    "paths": j["scope"],
                    "required_tools": j["authorized_tools"],
                },
            )["id"]
            for patch in proposals:
                if (
                    not isinstance(patch, dict)
                    or set(patch) != {"path", "sha256", "content"}
                    or patch["path"] not in j["scope"]
                ):
                    raise KernelError("Provider attempted to expand its file scope")
                call("candidates.patch", {"id": candidate, **patch})
            # This delegation is established by clip.authorize for the bounded task;
            # neither provider text nor an external agent can mint it.
            c = kernel.record("candidates", candidate)
            c["execution_approval"] = {
                "by": j["authorized_by"],
                "task": id,
                "revision": revision(hashes(kernel.candidate_root(candidate))),
                "at": time.time(),
            }
            kernel.save("candidates", c)
            update(current_operation="Candidate regression tests", candidate=candidate)
            result = test(candidate)
            iterations = j["iterations"] + [
                {
                    "number": iteration + 1,
                    "candidate": candidate,
                    "test_job": result["id"],
                    "state": result["state"],
                }
            ]
            update(iterations=iterations)
            if result["state"] == "Completed":
                call("candidates.review", {"id": candidate})
                update(
                    state="Waiting for Approval",
                    current_operation="Candidate passed; review diff and accept/reject",
                )
                break
            call("candidates.reject", {"id": candidate})
            update(
                candidate=None,
                current_operation="Failed candidate retained as evidence; accepted source unchanged",
            )
        else:
            update(
                state="Failed",
                current_operation="Iteration limit reached without passing candidate",
            )
    except Exception as exc:
        if child:
            record = kernel.record("jobs", child)
            if record["state"] in ("Queued", "Running"):
                kernel.dispatch("jobs.cancel", {"id": child}, p)
        message = str(exc)
        state = (
            "Paused"
            if message == "Paused"
            else "Cancelled"
            if message == "Cancelled"
            else "Failed"
        )
        update(state=state, error=message, current_operation=message)
    update(finished=time.time())
    evidence = {
        "id": uuid.uuid4().hex,
        "job": id,
        "candidate": j.get("candidate"),
        "tool": "clip.loop",
        "revision": j["revision"],
        "state": j["state"],
        "class": "HOST_SIM",
        "environment": {
            "provider": j["task"]["provider"],
            "mock_agent": j["task"]["provider"] == "deterministic",
        },
        "iterations": j["iterations"],
        "provider_calls": j["provider_calls"],
        "duration_seconds": time.monotonic() - start,
        "created": time.time(),
        "stdout": j["current_operation"],
        "stderr": j.get("error", ""),
        "artifacts": [],
        "exit_status": 0 if j["state"] in ("Completed", "Waiting for Approval") else 1,
    }
    kernel.save("evidence", evidence)
    update(evidence=evidence["id"])
