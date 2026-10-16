"""arc1 command-line entry point. See docs/CLI.md for the contract."""

import argparse
import json
import sys
import traceback

from . import doctor as doctor_mod
from . import device, hardware, passrec, project
from .core import (EXIT_CODES, EXIT_INTERNAL, SCHEMA_REVISION, SDK_VERSION, Result, UsageError,
                   display_path, write_report)
from .jsonschema_lite import SchemaError

EPILOG = ("Exit codes: 0 PASS, 1 FAIL, 2 usage/input error, 3 NOT_AVAILABLE or NOT_RUN, "
          "4 internal error. --json prints the tool result (sdk/schemas/tool-result.schema.json).")


def _frames(text):
    v = int(text)
    if not 1 <= v <= 36000:
        raise argparse.ArgumentTypeError("frames must be 1..36000")
    return v


def _dump_list(text):
    try:
        vals = sorted({int(x) for x in text.split(",") if x != ""})
    except ValueError:
        raise argparse.ArgumentTypeError("expected comma-separated frame numbers")
    if len(vals) > 16 or any(v < 0 for v in vals):
        raise argparse.ArgumentTypeError("at most 16 non-negative frame numbers")
    return vals


def build_parser():
    # SUPPRESS keeps a subcommand from resetting a --json given before it.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="print the JSON tool result to stdout")

    p = argparse.ArgumentParser(prog="arc1", description="ARC-1 agent-native SDK (host tools, M0-M1).",
                                epilog=EPILOG)
    p.add_argument("--json", action="store_true", help="print the JSON tool result to stdout")
    p.add_argument("--version", action="version",
                   version="arc1 %s (schema %s)" % (SDK_VERSION, SCHEMA_REVISION))
    sub = p.add_subparsers(dest="cmd", metavar="<command>")

    sub.add_parser("doctor", parents=[common], epilog=EPILOG,
                   help="check toolchain, schemas, manifests; report absent hardware")

    s = sub.add_parser("new", parents=[common], epilog=EPILOG, help="create a minimal C game project")
    s.add_argument("name", help="project name, [a-z][a-z0-9_]{0,31}")
    s.add_argument("--dir", default=".", help="parent directory (default: current directory)")

    for name, helptext in (("build", "compile the host demo of a project"),
                           ("sim", "run the host reference model"),
                           ("test", "run the project's deterministic tests")):
        s = sub.add_parser(name, parents=[common], epilog=EPILOG, help=helptext)
        s.add_argument("project", nargs="?", default=".", help="project directory (default: .)")
        if name == "sim":
            s.add_argument("--frames", type=_frames, default=120)
            s.add_argument("--replay", help="replay file relative to the project")
            s.add_argument("--dump", type=_dump_list, default=[], help="frames to save as PPM, e.g. 0,60")
        if name == "test":
            s.add_argument("--update-golden", action="store_true",
                           help="re-record golden baselines (review-sensitive, TST-003)")
            s.add_argument("--only", action="append", help="run only this test id (repeatable)")

    hw = sub.add_parser("hw", help="hardware fact queries").add_subparsers(dest="hwcmd", metavar="<subcommand>")
    s = hw.add_parser("inspect", parents=[common], epilog=EPILOG, help="validate and query a hardware manifest")
    s.add_argument("--manifest", default=str(hardware.DEFAULT_BOARD))
    s.add_argument("--chip", help="limit output to one chip id")

    ps = sub.add_parser("pass", help="agent pass records").add_subparsers(dest="passcmd", metavar="<subcommand>")
    s = ps.add_parser("validate", parents=[common], epilog=EPILOG, help="validate covenant, evidence and handoff")
    s.add_argument("record", help="pass.json or its directory")
    s.add_argument("--root", help="directory that record paths are relative to (default: SDK root)")
    s.add_argument("--no-git", action="store_true", help="skip base-commit and disclosure checks")

    fp = sub.add_parser("fpga", help="FPGA flows (Phase 2)").add_subparsers(dest="fpgacmd", metavar="<subcommand>")
    fp.add_parser("check", parents=[common], epilog=EPILOG, help="RTL lint/sim/synthesis/P&R (not implemented)")

    dv = sub.add_parser("device", help="physical board operations").add_subparsers(dest="devcmd", metavar="<subcommand>")
    s = dv.add_parser("deploy", parents=[common], epilog=EPILOG, help="deploy to a physical board (not available)")
    s.add_argument("project", nargs="?", default=".")
    dv.add_parser("detect", parents=[common], epilog=EPILOG,
                  help="read-only check for an F133 in FEL mode on rear USB-C (runs `xfel version`)")
    s = dv.add_parser("flash", parents=[common], epilog=EPILOG,
                      help="plan a NOR partition write and check it; writing is disabled (always NOT_AVAILABLE)")
    s.add_argument("--partition", required=True, help="NOR partition id, e.g. F1MA (see `arc1 ui` flasher)")
    s.add_argument("--image", required=True, help="image file to plan")

    s = sub.add_parser("ui", help="DOS-style debug console and flasher (text UI)")
    s.add_argument("project", nargs="?", default="examples/hello_arc1", help="project for build/sim/test items")
    s.add_argument("--snapshot", metavar="ITEM",
                   help="render one menu item to an 80x25 text screen on stdout instead of starting the UI")
    return p


def _print_human(data):
    print("%s: %s [%s]" % (data["command"], data["verdict"], data["evidence_level"]))
    for f in data["failure_reasons"]:
        print("  FAIL %s %s%s" % (f["code"], f["message"], " (%s)" % f["path"] if "path" in f else ""))
    for w in data["warnings"]:
        print("  warn %s" % w)
    if "test_count" in data:
        print("  tests: %d, failed: %d" % (data["test_count"], data["failed_count"]))
    for a in data["artifacts"][:12]:
        print("  artifact %s %s" % (a["sha256"][:12], a["path"]))
    if len(data["artifacts"]) > 12:
        print("  ... %d more artifacts" % (len(data["artifacts"]) - 12))


def execute(args):
    """Runs a parsed command and returns (result dict, report file or None).
    Shared by the command line and the text UI."""
    report_file = None
    if args.cmd == "doctor":
        result = Result("arc1 doctor", "STATIC_CHECK")
        doctor_mod.doctor(result)
    elif args.cmd == "new":
        result = Result("arc1 new", "STATIC_CHECK")
        project.new(result, args.name, args.dir)
    elif args.cmd in ("build", "sim", "test"):
        proj = project.Project(args.project)
        result = Result("arc1 %s" % args.cmd, "STATIC_CHECK" if args.cmd == "build" else "HOST_SIM")
        if args.cmd == "build":
            project.build(result, proj)
        elif args.cmd == "sim":
            project.sim(result, proj, args.frames, args.replay, args.dump)
        else:
            project.test(result, proj, args.update_golden, args.only)
        report_file = project.report_path(proj, args.cmd)
    elif args.cmd == "hw":
        result = Result("arc1 hw inspect %s" % display_path(args.manifest), "DESIGN")
        hardware.inspect(result, args.manifest, args.chip)
    elif args.cmd == "pass":
        result = Result("arc1 pass validate", "STATIC_CHECK")
        passrec.validate(result, args.record, args.root, not args.no_git)
    elif args.cmd == "fpga":
        result = Result("arc1 fpga check", "NONE")
        result.verdict = "NOT_RUN"
        result.failures.append({"code": "NOT_RUN", "message":
                                "Phase 2: no RTL is in this repository and no FPGA flow is locked"})
    elif args.devcmd == "detect":
        result = Result("arc1 device detect", "NONE")
        device.detect(result)
    elif args.devcmd == "flash":
        result = Result("arc1 device flash", "NONE")
        device.flash(result, args.partition, args.image)
    else:
        result = Result("arc1 device deploy", "NONE")
        result.verdict = "NOT_AVAILABLE"
        result.failures.append({"code": "CLI-002", "message":
                                "no identified physical ARC-1 board, transport or verified recovery path; "
                                "nothing was deployed and simulator output cannot substitute"})

    data = write_report(result, report_file) if report_file else result.to_dict()
    return data, report_file


def run(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd or (args.cmd == "hw" and not args.hwcmd) or (args.cmd == "pass" and not args.passcmd) \
            or (args.cmd == "fpga" and not args.fpgacmd) or (args.cmd == "device" and not args.devcmd):
        parser.print_help()
        return EXIT_CODES["ERROR"]
    if args.cmd == "ui":
        from . import ui
        return ui.main(args.project, args.snapshot)

    data, report_file = execute(args)
    if args.json:
        sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    else:
        _print_human(data)
        if report_file:
            print("  report %s" % display_path(report_file))
    return EXIT_CODES[data["verdict"]]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        return run(argv)
    except UsageError as e:
        sys.stderr.write("arc1: error: %s\n" % e)
        return EXIT_CODES["ERROR"]
    except SchemaError as e:
        sys.stderr.write("arc1: schema error: %s\n" % e)
        return EXIT_CODES["ERROR"]
    except BrokenPipeError:  # output consumer went away (e.g. `| head`)
        sys.stderr.close()
        return EXIT_CODES["ERROR"]
    except Exception:  # pragma: no cover - surfaced as a distinct exit code
        traceback.print_exc()
        return EXIT_INTERNAL
