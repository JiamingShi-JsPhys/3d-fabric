"""Test double for ``solidcraft-cli``.

Implements just enough of the real CLI to exercise 3d-fabric's bridge:

* ``--version``              -> prints a version line
* ``run SRC [--out P]... ``  -> writes the requested exports
* ``--save P``               -> writes a stub .sc
* ``--results --json-out F`` -> writes a per-step result list

Behaviour is switched with ``STUB_MODE``:
    ok       (default) succeed and write every export
    fail     exit 1 with ``error: step 1 (solid.box): ...`` on stderr
    silent   exit 0 and write nothing
    crash    exit 2 with no stderr

Export targets are taken from ``--out`` flags **and** from any
``file.export_*`` command inside the script, mirroring the real CLI, so the
quality-injection path is covered end to end.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys


VERSION = "solidcraft-cli 9.9.9-stub"


def _export_paths(argv, script):
    paths = [pathlib.Path(argv[i + 1]) for i, a in enumerate(argv) if a == "--out"]
    try:
        data = json.loads(pathlib.Path(script).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    for command in data.get("commands", []) if isinstance(data, dict) else []:
        name = str(command.get("command", ""))
        if name.startswith("file.export"):
            target = command.get("params", {}).get("path")
            if target:
                paths.append(pathlib.Path(target))
    return paths


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0

    record = os.environ.get("STUB_ARGV_OUT")
    if record:
        pathlib.Path(record).write_text(json.dumps(argv), encoding="utf-8")

    mode = os.environ.get("STUB_MODE", "ok")

    if mode == "fail":
        print("error: step 1 (solid.box): stub exploded", file=sys.stderr)
        return 1
    if mode == "crash":
        return 2
    if mode == "silent":
        return 0

    if "eval" in argv:
        return _eval(argv, mode)
    if "snapshot" in argv:
        return _snapshot(argv)
    if "script" in argv:
        return _script(argv)
    if "run" not in argv:
        print("error: stub only implements 'run', 'eval', 'snapshot' and 'script'",
              file=sys.stderr)
        return 1

    script = argv[argv.index("run") + 1]
    import trimesh

    mesh = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    for target in _export_paths(argv, script):
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() in (".step", ".stp"):
            target.write_text(
                "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('stub'),'2;1');\n"
                "ENDSEC;\nEND-ISO-10303-21;\n", encoding="utf-8")
        else:
            mesh.export(str(target))

    if "--save" in argv:
        save = pathlib.Path(argv[argv.index("--save") + 1])
        save.parent.mkdir(parents=True, exist_ok=True)
        save.write_text("stub design\n", encoding="utf-8")

    if "--json-out" in argv:
        out = pathlib.Path(argv[argv.index("--json-out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([
            {"name": "Box1", "warning": None, "created_bodies": ["Body1"]},
            *[{"path": str(p)} for p in _export_paths(argv, script)],
        ]), encoding="utf-8")

    return 0


def _eval(argv, mode):
    out = pathlib.Path(argv[argv.index("--json-out") + 1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "body_count": 1,
        "bodies": [{
            "name": "Body1",
            "volume_mm3": 1000.0,
            "area_mm2": 600.0,
            "mass_g": 1.29,
            "closed": mode != "open",
            "bbox": {"min": [-5.0, -5.0, 0.0], "max": [5.0, 5.0, 10.0]},
            "faces": 6,
            "edges": 12,
            "face_types": {"plane": 6},
        }],
        "params": [{"name": "L", "expression": "10 mm"}],
    }), encoding="utf-8")
    return 0


def _snapshot(argv):
    target = pathlib.Path(argv[argv.index("--out") + 1])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    width = int(argv[argv.index("--width") + 1]) if "--width" in argv else 480
    height = int(argv[argv.index("--height") + 1]) if "--height" in argv else 320
    print(json.dumps({"bytes": target.stat().st_size, "width": width,
                      "height": height, "path": str(target),
                      "renderer": "stub"}))
    return 0


def _script(argv):
    target = pathlib.Path(argv[argv.index("--out") + 1])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "about": {"design": "stub", "replay": "stub replay"},
        "commands": [
            {"command": "parameters.add", "params": {"name": "L", "expression": "10 mm"}},
            {"command": "solid.box", "params": {"length": "L"}},
        ],
    }), encoding="utf-8")
    print(f"{target.name}: 2 steps")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
