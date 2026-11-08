"""SolidCraft bridge — probe the local install and run modelling scripts.

This module is the only place that knows about the ``solidcraft-cli``
executable.  It does no geometry work: it locates the CLI, checks its
version, runs a ``.json`` script or ``.sc`` design in a quiet subprocess,
and verifies that the promised export actually landed on disk.

Verified CLI behaviour (SolidCraft 0.30.1, Windows):

* ``solidcraft-cli run <script.json|design.sc|part.step> --out <file>``
  exports the result, choosing the format from the extension; ``--out`` may
  be repeated to write several formats in one run.
* ``--save <design.sc>`` stores the built design as an editable document.
* ``--results --json-out <file>`` writes a machine-readable step list.
* A failing step exits **1** and prints ``error: step N (cmd): ...`` on
  stderr; the run writes nothing.

License: MIT. See ../LICENSE.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "MISSING_MESSAGE",
    "MODEL_FORMATS",
    "SolidCraftError",
    "probe",
    "run",
    "load_requirement",
    "materialize_script",
]

#: Exact wording required when SolidCraft is absent (user-facing contract).
MISSING_MESSAGE = "请先在本机安装 SolidCraft 软件并配置环境变量，才能使用自然语言建模功能。"

#: Export formats the ``model`` action can ask SolidCraft for.
MODEL_FORMATS = {"stl": "stl", "step": "step", "stp": "step", "3mf": "3mf",
                 "obj": "obj", "urdf": "urdf"}

#: Command that performs the export for a format, used when a non-default
#: tessellation quality forces us to inject the export into the script.
EXPORT_COMMANDS = {
    "stl": "file.export_stl",
    "3mf": "file.export_3mf",
    "obj": "file.export_obj",
    "step": "file.export_step",
}

#: Formats whose export command accepts ``quality``.
QUALITY_FORMATS = {"stl", "3mf", "obj"}

_CLI_NAMES = ("solidcraft-cli.exe", "solidcraft-cli", "solidcraft.exe", "solidcraft")

_ENV_VARS = ("SOLIDCRAFT_CLI", "SOLIDCRAFT_HOME")

_VERSION_TIMEOUT = 20

#: Name of the temporary results sidecar written next to the export and
#: removed once parsed (unless the caller asks to keep it).
SKILL_TMP_STEM = "3d-fabric"


class SolidCraftError(RuntimeError):
    """The CLI could not be found, or refused to run the script."""


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def _known_paths() -> List[pathlib.Path]:
    """Install locations worth trying when the CLI is not on PATH."""
    candidates: List[pathlib.Path] = []
    for env, *rest in (
        ("PROGRAMFILES", "SolidCraft", "solidcraft-cli.exe"),
        ("PROGRAMFILES(X86)", "SolidCraft", "solidcraft-cli.exe"),
        ("LOCALAPPDATA", "Programs", "SolidCraft", "solidcraft-cli.exe"),
    ):
        root = os.environ.get(env)
        if root:
            candidates.append(pathlib.Path(root).joinpath(*rest))
    # The vendor's default install drive on this machine and neighbours.
    for drive in ("D:", "C:", "E:"):
        candidates.append(pathlib.Path(f"{drive}/Applications/SolidCraft/solidcraft-cli.exe"))
    return candidates


def _cli_argv(cli: pathlib.Path) -> List[str]:
    """Executable prefix for subprocess.

    A ``.py`` path is run through the current interpreter, which lets tests
    and scripted installs use a stub CLI without an .exe.
    """
    if cli.suffix.lower() == ".py":
        return [sys.executable, str(cli)]
    return [str(cli)]


def _version(cli: pathlib.Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            [*_cli_argv(cli), "--version"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=_VERSION_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    text = (proc.stdout or proc.stderr or "").strip().splitlines()
    return text[0].strip() if text else "unknown"


def probe(explicit: Optional[str] = None) -> Dict[str, Any]:
    """Locate the SolidCraft CLI and report how it was found.

    Order: explicit ``--solidcraft`` path, ``SOLIDCRAFT_CLI`` /
    ``SOLIDCRAFT_HOME``, ``PATH``, then the vendor's default install folders.
    Every candidate must answer ``--version`` with exit code 0 before it is
    accepted, so a stale shim on PATH cannot pass as a working install.
    """
    seen = set()
    candidates: List[tuple] = []

    def add(path: Any, source: str) -> None:
        if not path:
            return
        p = pathlib.Path(str(path)).expanduser()
        key = str(p).lower()
        if key in seen:
            return
        seen.add(key)
        candidates.append((p, source))

    add(explicit, "explicit")
    for var in _ENV_VARS:
        value = os.environ.get(var)
        if not value:
            continue
        p = pathlib.Path(value)
        if p.is_dir():
            for name in _CLI_NAMES:
                add(p / name, var)
        else:
            add(p, var)
    for name in _CLI_NAMES:
        add(shutil.which(name), "PATH")
    for p in _known_paths():
        add(p, "known-path")

    tried: List[str] = []
    for path, source in candidates:
        tried.append(str(path))
        if not path.is_file():
            continue
        version = _version(path)
        if version:
            return {
                "installed": True,
                "path": str(path),
                "version": version,
                "source": source,
                "message": "SolidCraft CLI ready",
                "tried": tried,
            }

    return {
        "installed": False,
        "path": None,
        "version": None,
        "source": None,
        "message": MISSING_MESSAGE,
        "tried": tried,
    }


# ---------------------------------------------------------------------------
# requirement handling
# ---------------------------------------------------------------------------

def load_requirement(path: "str | pathlib.Path") -> Dict[str, Any]:
    """Read a requirement/script JSON.

    Accepted shapes::

        {"commands": [{"command": ..., "params": {...}}, ...]}
        {"prompt": "...", "commands": [...], "output": "part.stl",
         "quality": "fine"}
        {"prompt": "...", "script": "build.json" | {...commands...}}
        {"prompt": "...", "design": "part.sc"}
    """
    p = pathlib.Path(path)
    if not p.is_file():
        raise SolidCraftError(f"requirement not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SolidCraftError(f"{p.name} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise SolidCraftError(f"{p.name} must contain a JSON object")
    return raw


def materialize_script(commands: Sequence[Dict[str, Any]],
                       path: "str | pathlib.Path") -> pathlib.Path:
    """Write ``{"commands": [...]}`` to ``path`` and return it."""
    if not commands:
        raise SolidCraftError("the script contains no commands")
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"commands": list(commands)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def with_export(commands: Sequence[Dict[str, Any]],
                path: "str | pathlib.Path",
                fmt: str,
                quality: str) -> List[Dict[str, Any]]:
    """Return ``commands`` plus an explicit export step.

    ``solidcraft-cli run --out`` exists but always tessellates with the
    default quality. When the caller asks for ``fine``/``finest`` the export
    has to be a script command, which also means the caller must drop the
    matching ``--out`` flag.
    """
    fmt = MODEL_FORMATS.get(fmt, fmt)
    command = EXPORT_COMMANDS.get(fmt)
    if command is None:
        raise SolidCraftError(f"no export command for format {fmt!r}")
    params: Dict[str, Any] = {"path": str(path)}
    if fmt in QUALITY_FORMATS:
        params["quality"] = quality
    return [*commands, {"command": command, "params": params}]


def read_commands(path: "str | pathlib.Path") -> Optional[List[Dict[str, Any]]]:
    """Return the ``commands`` list of a SolidCraft script JSON, else None."""
    p = pathlib.Path(path)
    if p.suffix.lower() != ".json" or not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    commands = data.get("commands") if isinstance(data, dict) else None
    return commands if isinstance(commands, list) else None


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------

def run(
    cli: "str | pathlib.Path",
    source: "str | pathlib.Path",
    outputs: Sequence["str | pathlib.Path"] = (),
    *,
    expected: Optional[Sequence["str | pathlib.Path"]] = None,
    timeout: float = 300.0,
    save_design: Optional["str | pathlib.Path"] = None,
    design_in: Optional["str | pathlib.Path"] = None,
    cwd: Optional["str | pathlib.Path"] = None,
    keep_results: bool = False,
) -> Dict[str, Any]:
    """Run a SolidCraft script/design and export ``outputs``.

    ``outputs`` become ``--out`` flags. ``expected`` is what must exist
    afterwards and defaults to ``outputs``; pass it when the script exports
    itself (a ``file.export_*`` command) and no ``--out`` is used.

    Returns a dict with ``ok``, ``returncode``, ``stderr``, ``error`` and the
    parsed ``results`` list. A non-zero exit or a missing output file is a
    failure; nothing is inferred from a silent run.
    """
    cli_path = pathlib.Path(cli)
    if not cli_path.is_file():
        raise SolidCraftError(f"SolidCraft CLI not found at {cli_path}")

    out_paths = [pathlib.Path(o) for o in outputs]
    check_paths = [pathlib.Path(p) for p in (expected if expected is not None else outputs)]
    if not out_paths and not check_paths:
        raise SolidCraftError("no export paths were given")

    for path in [*out_paths, *check_paths]:
        path.parent.mkdir(parents=True, exist_ok=True)

    results_file = pathlib.Path(
        out_paths[0].parent if out_paths else check_paths[0].parent
    ) / f".{SKILL_TMP_STEM}-results.json"

    cmd: List[str] = [*_cli_argv(cli_path), "run", str(source), "--quiet",
                      "--results", "--json-out", str(results_file)]
    if design_in:
        # apply the script on top of an existing design instead of an empty one
        cmd.extend(["--in", str(design_in)])
    for out in out_paths:
        cmd.extend(["--out", str(out)])
    if save_design:
        pathlib.Path(save_design).parent.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--save", str(save_design)])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )
    except subprocess.TimeoutExpired as exc:
        _unlink(results_file)
        raise SolidCraftError(
            f"SolidCraft did not finish within {timeout:g}s; "
            "raise --timeout or simplify the model"
        ) from exc
    except OSError as exc:
        _unlink(results_file)
        raise SolidCraftError(f"could not start the SolidCraft CLI: {exc}") from exc

    results: Any = None
    if results_file.is_file():
        try:
            results = json.loads(results_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            results = None
        if not keep_results:
            _unlink(results_file)

    stderr = (proc.stderr or "").strip()
    error = None
    if proc.returncode != 0:
        error = stderr.splitlines()[-1] if stderr else f"exit code {proc.returncode}"
    else:
        missing = [str(p) for p in check_paths if not p.is_file() or p.stat().st_size == 0]
        if missing:
            error = ("SolidCraft reported success but wrote no output: "
                     + ", ".join(missing))

    return {
        "ok": error is None,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": stderr,
        "error": error,
        "results": results,
        "command": cmd,
        "outputs": [str(p) for p in check_paths],
    }


def _unlink(path: pathlib.Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# inspection, rendering and script extraction
# ---------------------------------------------------------------------------

def _temp_sidecar(directory: pathlib.Path, suffix: str) -> pathlib.Path:
    return directory / f".{SKILL_TMP_STEM}{suffix}"


def eval_design(
    cli: "str | pathlib.Path",
    source: "str | pathlib.Path",
    *,
    timeout: float = 120.0,
    cwd: Optional["str | pathlib.Path"] = None,
    keep: bool = False,
) -> Dict[str, Any]:
    """Measure a design or STEP file without building a mesh.

    Runs ``solidcraft-cli eval`` and returns its structured measurements:
    per body ``volume_mm3``, ``area_mm2``, ``mass_g`` (from the assigned
    material), ``bbox``, ``closed``, face/edge/vertex counts and
    ``face_types``, plus the design's parameters.
    """
    cli_path = pathlib.Path(cli)
    src = pathlib.Path(source)
    if not cli_path.is_file():
        raise SolidCraftError(f"SolidCraft CLI not found at {cli_path}")
    if not src.is_file():
        raise SolidCraftError(f"design not found: {src}")

    out = _temp_sidecar(src.parent, "-eval.json")
    cmd = [*_cli_argv(cli_path), "eval", str(src), "--json-out", str(out)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout,
                              cwd=str(cwd) if cwd else None)
    except subprocess.TimeoutExpired as exc:
        _unlink(out)
        raise SolidCraftError(
            f"SolidCraft eval did not finish within {timeout:g}s") from exc
    except OSError as exc:
        _unlink(out)
        raise SolidCraftError(f"could not start the SolidCraft CLI: {exc}") from exc

    measurements = None
    if out.is_file():
        try:
            measurements = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            measurements = None
        if not keep:
            _unlink(out)

    stderr = (proc.stderr or "").strip()
    error = None
    if proc.returncode != 0:
        error = stderr.splitlines()[-1] if stderr else f"exit code {proc.returncode}"
    elif measurements is None:
        error = "SolidCraft eval produced no measurements"

    return {
        "ok": error is None,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": stderr,
        "error": error,
        "measurements": measurements,
    }


def snapshot(
    cli: "str | pathlib.Path",
    source: "str | pathlib.Path",
    out_png: "str | pathlib.Path",
    *,
    view: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    section: Optional[str] = None,
    bodies: Sequence[str] = (),
    timeout: float = 180.0,
    cwd: Optional["str | pathlib.Path"] = None,
) -> Dict[str, Any]:
    """Render a PNG of a design or STEP file.

    ``view`` is one of iso / front / back / top / bottom / left / right (or a
    view saved in the design). ``section`` cuts the model, e.g. ``z=27`` or
    ``XY``. ``bodies`` entries take the ``NAME:opacity=0.3,color=#rrggbb``
    form the CLI documents.
    """
    cli_path = pathlib.Path(cli)
    src = pathlib.Path(source)
    target = pathlib.Path(out_png)
    if not cli_path.is_file():
        raise SolidCraftError(f"SolidCraft CLI not found at {cli_path}")
    if not src.is_file():
        raise SolidCraftError(f"design not found: {src}")

    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [*_cli_argv(cli_path), "snapshot", "--in", str(src), "--out", str(target)]
    if view:
        cmd.extend(["--view", view])
    if width:
        cmd.extend(["--width", str(int(width))])
    if height:
        cmd.extend(["--height", str(int(height))])
    if section:
        cmd.extend(["--section", section])
    for body in bodies:
        cmd.extend(["--body", body])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout,
                              cwd=str(cwd) if cwd else None)
    except subprocess.TimeoutExpired as exc:
        raise SolidCraftError(
            f"SolidCraft snapshot did not finish within {timeout:g}s") from exc
    except OSError as exc:
        raise SolidCraftError(f"could not start the SolidCraft CLI: {exc}") from exc

    stderr = (proc.stderr or "").strip()
    info: Any = None
    try:
        info = json.loads((proc.stdout or "").strip() or "null")
    except json.JSONDecodeError:
        info = None

    error = None
    if proc.returncode != 0:
        error = stderr.splitlines()[-1] if stderr else f"exit code {proc.returncode}"
    elif not target.is_file() or target.stat().st_size == 0:
        error = f"SolidCraft reported success but wrote no image: {target}"

    return {
        "ok": error is None,
        "returncode": proc.returncode,
        "stderr": stderr,
        "error": error,
        "info": info,
        "path": str(target),
        "bytes": target.stat().st_size if target.is_file() else 0,
    }


def extract_script(
    cli: "str | pathlib.Path",
    source: "str | pathlib.Path",
    out_json: "str | pathlib.Path",
    *,
    timeout: float = 120.0,
    cwd: Optional["str | pathlib.Path"] = None,
) -> Dict[str, Any]:
    """Write the command script that rebuilds an existing design.

    Turns an opaque ``.sc`` into an editable ``{"commands": [...]}`` list, so
    the agent can read what an existing design does and patch it with
    ``model --in``.
    """
    cli_path = pathlib.Path(cli)
    src = pathlib.Path(source)
    target = pathlib.Path(out_json)
    if not cli_path.is_file():
        raise SolidCraftError(f"SolidCraft CLI not found at {cli_path}")
    if not src.is_file():
        raise SolidCraftError(f"design not found: {src}")

    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [*_cli_argv(cli_path), "script", str(src), "--out", str(target)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout,
                              cwd=str(cwd) if cwd else None)
    except subprocess.TimeoutExpired as exc:
        raise SolidCraftError(
            f"SolidCraft script extraction did not finish within {timeout:g}s") from exc
    except OSError as exc:
        raise SolidCraftError(f"could not start the SolidCraft CLI: {exc}") from exc

    stderr = (proc.stderr or "").strip()
    document: Any = None
    if target.is_file():
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            document = None

    error = None
    if proc.returncode != 0:
        error = stderr.splitlines()[-1] if stderr else f"exit code {proc.returncode}"
    elif document is None:
        error = f"SolidCraft wrote no script: {target}"

    steps = None
    if isinstance(document, dict) and isinstance(document.get("commands"), list):
        steps = len(document["commands"])

    return {
        "ok": error is None,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": stderr,
        "error": error,
        "path": str(target),
        "step_count": steps,
        "about": document.get("about") if isinstance(document, dict) else None,
    }
