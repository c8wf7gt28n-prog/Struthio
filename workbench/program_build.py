"""Files-backed Blender and Godot rooms with explicit native handoffs."""

from __future__ import annotations

import gzip
import json
import os
from pathlib import PurePosixPath
import re
import shutil
import subprocess
import tempfile
import threading
import time

from . import files_service, record_io


PATH = {"type": "string", "minLength": 1, "maxLength": 1000}
SHA = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
BOUND = {"path": PATH, "expected_sha256": SHA}
GODOT_BOUND = {**BOUND, "scene": PATH}
FIELDS = {
    "programs.blender.inspect": ({"path": PATH}, ["path"]),
    "programs.blender.check": (BOUND, list(BOUND)),
    "programs.blender.open": (BOUND, list(BOUND)),
    "programs.godot.inspect": ({"path": PATH}, ["path"]),
    "programs.godot.open": (GODOT_BOUND, list(BOUND)),
    "programs.godot.play": (GODOT_BOUND, list(BOUND)),
}
SCOPES = {op: "read" if op.endswith(".inspect") else "approve" for op in FIELDS}

BLENDER_LIMIT = 512 * 1024**2
GODOT_CONFIG_LIMIT = 512 * 1024
GODOT_SCAN_LIMIT = 5000
GODOT_SCENE_LIMIT = 100
GODOT_DEPTH_LIMIT = 12
BLENDER_TIMEOUT = 15
BLENDER_MARKER = b"GRAPHITE_BLENDER_COUNTS "
BLENDER_CHECK = (
    "import bpy, json; "
    "print('GRAPHITE_BLENDER_COUNTS ' + json.dumps({"
    "'filepath': bpy.data.filepath, "
    "'scenes': len(bpy.data.scenes), "
    "'objects': len(bpy.data.objects), "
    "'meshes': len(bpy.data.meshes), "
    "'active_scene': bpy.context.scene.name if bpy.context.scene else None}))"
)


def _tool(room):
    # Godot: its own builds are godot4 or godot; Debian 13 ships Godot 3 as the package godot3, whose command is godot3.
    commands = ("blender",) if room == "blender" else ("godot4", "godot", "godot3")
    for command in commands:
        executable = shutil.which(command)
        if executable:
            return {"name": room.capitalize(), "available": True, "executable": os.path.abspath(executable)}
    return {"name": room.capitalize(), "available": False}


def _source(kernel, name, room):
    path = record_io.project_path(files_service.root(kernel, create=False), name)
    if room == "blender":
        if path.suffix.lower() != ".blend":
            raise ValueError("Select a Blender .blend file from Files.")
        limit = BLENDER_LIMIT
    else:
        if path.name != "project.godot":
            raise ValueError("Select the project's project.godot file from Files.")
        limit = GODOT_CONFIG_LIMIT
    if path.stat().st_size > limit:
        raise ValueError(f"This file exceeds the {limit // 1024**2} MiB Blender room limit."
                         if room == "blender" else "This project.godot exceeds the 512 KiB room limit.")
    return path


def _blender_header(path):
    with path.open("rb") as stream:
        header = stream.read(17)
    compression = None
    if header.startswith(b"\x28\xb5\x2f\xfd"):
        return {"format": "Zstandard-compressed .blend", "version": None, "header_verified": False}
    if header.startswith(b"\x1f\x8b"):
        compression = "gzip-compressed"
        try:
            with gzip.open(path, "rb") as stream:
                header = stream.read(17)
        except (OSError, EOFError) as exc:
            raise ValueError("The compressed Blender header is unreadable.") from exc
    legacy = re.match(rb"BLENDER[_-][vV]([0-9]{3})", header)
    modern = re.fullmatch(rb"BLENDER17-01v([0-9]{4})", header)
    match = legacy or modern
    if match is None:
        raise ValueError("The file does not have a recognized Blender header.")
    version = int(match.group(1))
    return {
        "format": f"{compression} .blend" if compression else ".blend",
        "version": f"{version // 100}.{version % 100}",
        "header_verified": True,
    }


def _godot_config(path):
    with path.open("rb") as stream:
        raw = stream.read(GODOT_CONFIG_LIMIT + 1)
    if len(raw) > GODOT_CONFIG_LIMIT:
        raise ValueError("This project.godot exceeds the 512 KiB room limit.")
    section = None
    config_version = None
    values = {}
    for line in raw.decode("utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        if section is None and key == "config_version":
            match = re.fullmatch(r"\s*([0-9]{1,3})\s*(?:;.*)?", value)
            if match:
                config_version = int(match.group(1))
        if section == "application" and key in ("config/name", "run/main_scene") and value.lstrip().startswith('"'):
            try:
                parsed, _ = json.JSONDecoder().raw_decode(value.lstrip())
            except (ValueError, RecursionError):
                continue
            if isinstance(parsed, str):
                values[key] = parsed
    if config_version is None:
        raise ValueError("project.godot is missing a readable config_version.")
    return {
        "title": values.get("config/name") or path.parent.name,
        "main_scene": values.get("run/main_scene") or None,
        "config_version": config_version,
    }


def _godot_scenes(root):
    scenes = []
    directories = [(root, 0)]
    scanned = 0
    truncated = False
    while directories:
        folder, depth = directories.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                scanned += 1
                if scanned > GODOT_SCAN_LIMIT:
                    return sorted(scenes), True
                if entry.name.startswith(".") or entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if depth < GODOT_DEPTH_LIMIT:
                        directories.append((folder / entry.name, depth + 1))
                    else:
                        truncated = True
                elif entry.name.lower().endswith((".tscn", ".scn")) and entry.is_file(follow_symlinks=False):
                    name = "res://" + (folder / entry.name).relative_to(root).as_posix()
                    if len(name) <= PATH["maxLength"]:
                        if len(scenes) == GODOT_SCENE_LIMIT:
                            return sorted(scenes), True
                        scenes.append(name)
                    else:
                        truncated = True
    return sorted(scenes), truncated


def _scene(root, requested):
    prefix = "res://"
    name = requested.removeprefix(prefix)
    if PurePosixPath(name).suffix.lower() not in (".tscn", ".scn"):
        raise ValueError("Select a .tscn or .scn scene inside this Godot project.")
    record_io.project_path(root, name)
    return prefix + name


def _same_source(path, expected):
    actual = record_io.sha(path)
    if actual != expected:
        raise ValueError("The selected file changed. Inspect it again before starting a native action.")
    return actual


def _inspect(path, name, room, tool):
    before = path.stat()
    if room == "blender":
        details = _blender_header(path)
    else:
        details = _godot_config(path)
        details["scenes"], details["scenes_truncated"] = _godot_scenes(path.parent)
    digest = record_io.sha(path)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("The selected file changed during inspection. Try again.")
    return {
        "state": "READY" if tool["available"] else "TOOL_UNAVAILABLE",
        "path": name,
        "sha256": digest,
        "bytes": after.st_size,
        "tool": tool,
        **details,
    }


def _blender_check(executable, path):
    command = [
        executable, "--background", "--factory-startup", "--disable-autoexec",
        "--threads", "2", str(path), "--python-exit-code", "17", "--python-expr", BLENDER_CHECK,
    ]
    with tempfile.TemporaryDirectory(prefix="graphite-blender-") as directory, tempfile.TemporaryFile() as output:
        try:
            result = subprocess.run(
                command, cwd=directory, stdin=subprocess.DEVNULL,
                stdout=output, stderr=subprocess.STDOUT, timeout=BLENDER_TIMEOUT, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"Blender did not finish within {BLENDER_TIMEOUT} seconds.") from exc
        output.seek(max(0, output.tell() - 16 * 1024))
        for line in reversed(output.read().splitlines()):
            if result.returncode == 0 and line.startswith(BLENDER_MARKER):
                data = json.loads(line[len(BLENDER_MARKER):])
                if (isinstance(data, dict) and data.pop("filepath", None) == str(path)
                        and all(type(data.get(key)) is int for key in ("scenes", "objects", "meshes"))):
                    return data
    raise ValueError("Blender could not read the file. Check the installed Blender version and source.")


def _start(command, directory):
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise ValueError("Open the Graphite desktop session to hand this file to a native window.")
    process = subprocess.Popen(
        command, cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )
    time.sleep(0.15)
    if process.poll() is not None:
        raise ValueError("The native program exited before Graphite could hand off the session.")
    threading.Thread(target=process.wait, daemon=True).start()
    return process.pid


def dispatch(kernel, op, args, principal):
    _, room, action = op.split(".")
    path = _source(kernel, args["path"], room)
    tool = _tool(room)
    if action == "inspect":
        return _inspect(path, args["path"], room, tool)
    if principal.identity != "desktop-owner" or not {"read", "approve"} <= principal.scopes:
        raise ValueError("A native action needs desktop owner approval.")
    digest = _same_source(path, args["expected_sha256"])
    if not tool["available"]:
        raise ValueError(f"{tool['name']} is unavailable on this host.")
    result = {"path": args["path"], "sha256": digest, "tool": tool}
    executable = tool["executable"]
    if room == "blender":
        _blender_header(path)
        if action == "check":
            data = _blender_check(executable, path)
            _same_source(path, digest)
            return {"state": "CHECKED", **result, **data}
        command = [executable, "--disable-autoexec", str(path)]
    else:
        project = _godot_config(path)
        selected = args.get("scene")
        scene = _scene(path.parent, selected) if selected else None
        if action == "play" and scene is None:
            main = project["main_scene"]
            if not main:
                raise ValueError("Choose a scene or set a main scene in the Godot editor.")
            if main.startswith("res://"):
                scene = _scene(path.parent, main)
            elif re.fullmatch(r"uid://[a-z0-9]+", main) is None:
                raise ValueError("The configured Godot main scene is outside the supported project paths.")
        command = [executable, "--path", str(path.parent)]
        if action == "open":
            command.append("--editor")
        if scene:
            command.append(scene)
        result["scene"] = scene or (project["main_scene"] if action == "play" else None)
    return {"state": "STARTED", **result, "pid": _start(command, path.parent)}
