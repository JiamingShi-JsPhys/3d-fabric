#!/usr/bin/env python3
"""3d-fabric — natural-language 3D modelling and print QC for local SolidCraft.

Positioning
-----------
This plugin does not implement a solid kernel and does not try to speak to
other CAD applications. It is the bridge between an AI agent and the
SolidCraft installation on this machine, plus the print gate that follows it:

    natural language
        -> agent writes a SolidCraft script (see SKILL.md)
        -> --action model  : probe CLI, run the script headlessly, export STL
        -> --action inspect: trimesh checks watertight/manifold/normals/size
        -> --action repair : fix holes on meshes that came from elsewhere

Actions
-------
    probe    locate solidcraft-cli and report its version
    model    run a SolidCraft script/design and export, then auto-inspect
    inspect  report geometry + topology + printability of a mesh
    repair   fix print blockers and export

Exit codes
----------
0  PASS       — installed / model built / mesh print-ready / repair closed it
1  FAIL       — SolidCraft failed, or the mesh is structurally unusable
2  UNVERIFIED — SolidCraft missing, defects repairable, or unreadable input
3  USAGE      — bad arguments (argparse)

License: MIT. See LICENSE.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from scripts import engine  # noqa: E402
from scripts import solidcraft as sc  # noqa: E402

SKILL = "3d-fabric"

PASS, FAIL, UNVERIFIED = 0, 1, 2

_VERDICT_TO_STATUS = {
    "ready_to_print": "PASS",
    "needs_repair": "UNVERIFIED",
    "blocked": "FAIL",
}

#: SolidCraft can export these; trimesh can read the ones marked True.
_MODEL_EXPORTS = {
    "stl": {"mesh": True, "engine": "stl"},
    "obj": {"mesh": True, "engine": "obj"},
    "3mf": {"mesh": True, "engine": "3mf"},
    "ply": {"mesh": True, "engine": "ply"},
    "step": {"mesh": False, "engine": None},
    "stp": {"mesh": False, "engine": None},
    "urdf": {"mesh": False, "engine": None},
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _utc_stamp() -> str:
    """UTC timestamp for gate filenames, to the millisecond.

    Second precision meant two runs finishing in the same second wrote the
    same gate file and the second one silently won.
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%S") + f"{now.microsecond // 1000:03d}Z"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _split_numbers(text: str):
    return [float(p) for p in text.replace(";", ",").split(",") if p.strip()]


def _gate(status: str, reason: str, artifacts, data, evidence="EMPIRICAL") -> dict:
    return {
        "skill": SKILL,
        "status": status,
        "evidence_level": evidence,
        "reason": reason,
        "artifacts": [str(a) for a in artifacts],
        "timestamp": _iso_now(),
        "data": data,
    }


def _write_json(path: pathlib.Path, payload: dict) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _write_gate(args, gate: dict):
    if not getattr(args, "root", None):
        return None
    path = pathlib.Path(args.root) / "process" / "gates" / f"{SKILL}_{_utc_stamp()}.json"
    _write_json(path, gate)
    return path


def _fmt_vec(values) -> str:
    return ", ".join(f"{float(v):.3f}" for v in values)


def _emit(gate: dict, args, human=None) -> None:
    if getattr(args, "json", False):
        print(json.dumps(gate, ensure_ascii=False))
    elif human is not None:
        print(human)


def _transform_from_args(mesh, args) -> tuple:
    """Apply the shared geometry flags; returns (mesh, errors)."""
    errors: list = []
    if not any([args.scale, args.scale_xyz, args.translate, args.rotate, args.center]):
        return mesh, errors
    try:
        mesh = engine.transform(
            mesh,
            scale=args.scale,
            scale_xyz=_split_numbers(args.scale_xyz) if args.scale_xyz else None,
            translate=_split_numbers(args.translate) if args.translate else None,
            rotate_deg=_split_numbers(args.rotate) if args.rotate else None,
            center=args.center,
        )
    except engine.MeshError as exc:
        errors.append(str(exc))
    return mesh, errors


# ---------------------------------------------------------------------------
# report printing
# ---------------------------------------------------------------------------

def _print_report(analysis: dict) -> None:
    g, t, p = analysis["geometry"], analysis["topology"], analysis["printability"]

    def flag(value, good=True):
        if value is None:
            return "n/a"
        return "OK" if bool(value) is bool(good) else "!!"

    print("3d-fabric · inspect")
    print(f"  file          {analysis.get('source') or '-'}  ({analysis.get('format') or '?'})")
    print(f"  size          {_fmt_vec(g['extents'])}  {analysis['assumed_units']} (assumed)")
    print(f"  vertices      {g['vertex_count']}   faces {g['face_count']}   "
          f"bodies {g['body_count'] if g['body_count'] is not None else '?'}")
    print(f"  volume        "
          f"{g['signed_volume'] if g['signed_volume'] is not None else 'n/a (open)'} "
          f"{analysis['assumed_units']}^3")
    print(f"  surface area  {g['surface_area']} {analysis['assumed_units']}^2")
    print("  topology      "
          f"watertight[{flag(t['watertight'])}] "
          f"winding[{flag(t['winding_consistent'])}] "
          f"outward[{flag(t['normals_outward'])}] "
          f"manifold[{flag(t['is_manifold'])}]")
    print("  defects       "
          f"holes {t['hole_loop_count']}   boundary edges {t['boundary_edge_count']}   "
          f"non-manifold edges {t['nonmanifold_edge_count']}   "
          f"degenerate faces {t['degenerate_face_count']}")
    print(f"  verdict       {p['verdict']}")
    for issue in p["issues"]:
        count = f" x{issue['count']}" if "count" in issue else ""
        print(f"    - [{issue['severity']}] {issue['code']}{count}: {issue['message']}")


def _print_probe(probe: dict) -> None:
    print("3d-fabric · probe")
    if probe["installed"]:
        print(f"  solidcraft    {probe['path']}")
        print(f"  version       {probe['version']}")
        print(f"  found via     {probe['source']}")
    else:
        print(f"  solidcraft    not found")
        print(f"  message       {probe['message']}")
        for path in probe.get("tried", []):
            print(f"    tried       {path}")


def _print_repair_report(report: dict, out_path, report_path, gate_path=None) -> None:
    before, after = report["before"], report["after"]
    print("3d-fabric · repair")
    print(f"  file          {report.get('source') or '-'}")
    print("  steps")
    for step in report["steps"]:
        print(f"    - {step['step']:<28} changed {step['changed']}")
    for note in report.get("notes", []):
        print(f"    ! {note}")
    print("  before        "
          f"watertight={before['topology']['watertight']} "
          f"holes={before['topology']['hole_loop_count']} "
          f"non-manifold={before['topology']['nonmanifold_edge_count']} "
          f"verdict={before['printability']['verdict']}")
    print("  after         "
          f"watertight={after['topology']['watertight']} "
          f"holes={after['topology']['hole_loop_count']} "
          f"non-manifold={after['topology']['nonmanifold_edge_count']} "
          f"verdict={after['printability']['verdict']}")
    if after["geometry"]["signed_volume"] is not None:
        print(f"  volume        {after['geometry']['signed_volume']} "
              f"{after['assumed_units']}^3")
    print(f"  written       {out_path}")
    if report_path:
        print(f"  report        {report_path}")
    if gate_path:
        print(f"  gate          {gate_path}")
    if not report["success"]:
        print("  result        repair incomplete — the remaining defects are listed "
              "in the report; this file is written but should not go straight to a printer")


# ---------------------------------------------------------------------------
# action: probe
# ---------------------------------------------------------------------------

def action_probe(args) -> int:
    info = sc.probe(args.solidcraft)
    status = "PASS" if info["installed"] else "UNVERIFIED"
    gate = _gate(
        status,
        info["message"] if not info["installed"] else f"SolidCraft {info['version']} ready",
        [], {"probe": info},
        evidence="EXACT" if info["installed"] else "UNVERIFIED",
    )
    gate_path = _write_gate(args, gate)
    if gate_path:
        gate["artifacts"] = [str(gate_path)]
    _emit(gate, args, human=None)
    if not args.json:
        _print_probe(info)
        if gate_path:
            print(f"  gate          {gate_path}")
    return PASS if info["installed"] else UNVERIFIED


# ---------------------------------------------------------------------------
# action: model
# ---------------------------------------------------------------------------

def _resolve_output(args, req: dict, req_dir: pathlib.Path) -> pathlib.Path:
    if args.output:
        out = pathlib.Path(args.output)
    elif req.get("output"):
        out = (req_dir / str(req["output"])).resolve()
    elif args.root:
        out = pathlib.Path(args.root) / "process" / "models" / f"model_{_utc_stamp()}.stl"
    else:
        stem = args.script and pathlib.Path(args.script).stem or "model"
        out = req_dir / f"{stem}.stl"
    if args.format:
        fmt = args.format.lower()
        if out.suffix.lower().lstrip(".") not in (fmt, "stp" if fmt == "step" else fmt):
            out = out.with_suffix("." + fmt)
    return out.resolve()


def _resolve_source(args) -> tuple:
    """Return (source_path, request_dict, req_dir, inline_commands).

    ``inline_commands`` is a list when the requirement carried the commands
    itself; it is materialised next to the output so the exact script that
    built the part is kept.
    """
    if args.script:
        p = pathlib.Path(args.script).resolve()
        if not p.is_file():
            raise sc.SolidCraftError(f"script not found: {p}")
        if p.suffix.lower() == ".json":
            req = sc.load_requirement(p)
            if "commands" in req:
                return p, req, p.parent, None
            return p, req, p.parent, None
        return p, {}, p.parent, None

    if not args.input:
        raise sc.SolidCraftError(
            "the model action needs --script <file> or --input <requirement.json>"
        )

    p = pathlib.Path(args.input).resolve()
    if not p.is_file():
        raise sc.SolidCraftError(f"requirement not found: {p}")
    if p.suffix.lower() != ".json":
        return p, {}, p.parent, None  # a .sc / .step passed as --input

    req = sc.load_requirement(p)
    if "commands" in req:
        commands = req["commands"]
        if not isinstance(commands, list):
            raise sc.SolidCraftError("'commands' must be a list")
        return p, req, p.parent, commands

    if "script" in req:
        value = req["script"]
        if isinstance(value, str):
            target = (p.parent / value).resolve()
            if not target.is_file():
                raise sc.SolidCraftError(f"script not found: {target}")
            return target, req, p.parent, None
        if isinstance(value, dict) and isinstance(value.get("commands"), list):
            return p, req, p.parent, value["commands"]
        raise sc.SolidCraftError("'script' must be a path or {commands: [...]}")

    if "design" in req:
        target = (p.parent / str(req["design"])).resolve()
        if not target.is_file():
            raise sc.SolidCraftError(f"design not found: {target}")
        return target, req, p.parent, None

    raise sc.SolidCraftError(
        "requirement JSON needs one of 'commands', 'script' or 'design'"
    )


def _step_warnings(results) -> list:
    if not isinstance(results, list):
        return []
    warnings = []
    for step in results:
        if isinstance(step, dict) and step.get("warning"):
            warnings.append(f"{step.get('name', 'step')}: {step['warning']}")
    return warnings


def action_model(args) -> int:
    probe = sc.probe(args.solidcraft)
    blocked = _require_solidcraft(args, probe, "model")
    if blocked is not None:
        return blocked

    try:
        source, req, req_dir, inline = _resolve_source(args)
        out = _resolve_output(args, req, req_dir)
    except sc.SolidCraftError as exc:
        return _fail_input(str(exc), args)

    fmt = out.suffix.lower().lstrip(".")
    if fmt not in _MODEL_EXPORTS:
        return _fail_input(
            f"SolidCraft cannot export '{fmt}'; use one of "
            + ", ".join(sorted(_MODEL_EXPORTS)), args)

    prompt = args.prompt or req.get("prompt") or ""
    quality = (args.quality or req.get("quality") or "standard").lower()
    if quality not in ("standard", "fine", "finest"):
        return _fail_input(f"unknown quality {quality!r}; use standard|fine|finest", args)
    timeout = args.timeout
    notes: list = []

    design_in = None
    if args.design_in:
        design_in = pathlib.Path(args.design_in).resolve()
        if not design_in.is_file():
            return _fail_input(f"design not found: {design_in}", args, probe=probe)
        notes.append(f"script applied on top of existing design: {design_in.name}")
    save_design = None
    if not args.no_save_design:
        save_design = pathlib.Path(args.save_design) if args.save_design else out.with_suffix(".sc")

    # Commands carried by the requirement are written out so the exact script
    # survives next to the model and can be reopened/edited in SolidCraft.
    if inline is not None:
        script_path = (pathlib.Path(args.script_out) if args.script_out
                       else out.parent / f"{out.stem}.solidcraft.json")
        try:
            source = sc.materialize_script(inline, script_path)
        except sc.SolidCraftError as exc:
            return _fail_input(str(exc), args)

    # Fine/finest tessellation is a per-command setting in SolidCraft, so the
    # export has to move into the script when the caller asks for it.
    expected = [out]
    export_via_script = False
    if quality != "standard" and fmt in sc.QUALITY_FORMATS:
        commands = sc.read_commands(source)
        if commands is not None:
            script_path = (pathlib.Path(args.script_out) if args.script_out
                           else out.parent / f"{out.stem}.solidcraft.json")
            try:
                source = sc.materialize_script(
                    sc.with_export(commands, out, fmt, quality), script_path)
            except sc.SolidCraftError as exc:
                return _fail_input(str(exc), args, probe=probe)
            export_via_script = True
        else:
            notes.append(
                f"--quality {quality} 需要 JSON 脚本；"
                f"{source.suffix} 只能使用 SolidCraft 的默认网格精度")

    try:
        result = sc.run(
            probe["path"], source, [] if export_via_script else [out],
            expected=expected,
            timeout=timeout,
            save_design=save_design,
            design_in=design_in,
            cwd=source.parent if source.parent.is_dir() else None,
            keep_results=args.keep_results,
        )
    except sc.SolidCraftError as exc:
        return _fail_input(str(exc), args, probe=probe)

    artifacts = [p for p in (out, save_design, source) if p and pathlib.Path(p).is_file()]
    data = {
        "probe": probe,
        "prompt": prompt,
        "script": str(source),
        "design": str(save_design) if save_design else None,
        "output": str(out),
        "quality": quality,
        "solidcraft": {
            "returncode": result["returncode"],
            "error": result["error"],
            "stderr_tail": result["stderr"][-1500:],
            "step_count": len(result["results"]) if isinstance(result["results"], list) else None,
            "warnings": _step_warnings(result["results"]),
        },
        "inspection": None,
        "notes": notes,
    }

    if not result["ok"]:
        gate = _gate("FAIL", result["error"] or "SolidCraft failed", artifacts, data,
                     evidence="UNVERIFIED")
        gate_path = _write_gate(args, gate)
        if gate_path:
            artifacts.append(gate_path)  # printed only; the gate file must not list itself
        if args.json:
            print(json.dumps(gate, ensure_ascii=False))
        else:
            print("3d-fabric · model")
            print(f"  solidcraft    {probe['path']}  ({probe['version']})")
            print(f"  script        {source}")
            print(f"  result        FAILED — {result['error']}")
            if result["stderr"]:
                for line in result["stderr"].splitlines()[-6:]:
                    print(f"    {line}")
        return FAIL

    if not _MODEL_EXPORTS[fmt]["mesh"]:
        notes.append(
            f"{fmt.upper()} 是 B-rep 模型，没有三角网格；"
            "要做打印前网格体检，请再导出 .stl 后运行 --action inspect"
        )
        gate = _gate("PASS", f"built {out.name} ({fmt})", artifacts, data,
                     evidence="SYMBOLIC")
        gate_path = _write_gate(args, gate)
        if gate_path:
            artifacts.append(gate_path)  # printed only; the gate file must not list itself
        if args.json:
            print(json.dumps(gate, ensure_ascii=False))
        else:
            print("3d-fabric · model")
            print(f"  solidcraft    {probe['path']}  ({probe['version']})")
            print(f"  script        {source}")
            print(f"  exported      {out}")
            print(f"  mesh check    skipped ({fmt} is a B-rep format)")
        return PASS

    # --- automatic post-build print QC -----------------------------------
    try:
        mesh = engine.load_mesh(out)
    except engine.MeshError as exc:
        return _fail_input(f"exported file is unreadable: {exc}", args, probe=probe)

    mesh, transform_errors = _transform_from_args(mesh, args)
    if transform_errors:
        notes.extend(transform_errors)
    if any([args.scale, args.scale_xyz, args.translate, args.rotate, args.center]):
        engine.export_mesh(mesh, out, ascii_stl=args.ascii,
                           file_type=_MODEL_EXPORTS[fmt]["engine"])

    analysis = engine.analyze(mesh, source=str(out), fmt=fmt)
    data["inspection"] = analysis
    status = _VERDICT_TO_STATUS[analysis["printability"]["verdict"]]
    reason = (
        f"built {out.name}: {analysis['printability']['verdict'].replace('_', ' ')}, "
        f"{analysis['geometry']['face_count']} faces, "
        f"{analysis['topology']['hole_loop_count']} holes"
    )

    gate = _gate(status, reason, artifacts, data)
    gate_path = _write_gate(args, gate)
    if gate_path:
        artifacts.append(gate_path)  # printed only; the gate file must not list itself

    if args.json:
        print(json.dumps(gate, ensure_ascii=False))
    else:
        print("3d-fabric · model")
        print(f"  solidcraft    {probe['path']}  ({probe['version']})")
        if prompt:
            print(f"  prompt        {prompt}")
        print(f"  script        {source}")
        if save_design:
            print(f"  design        {save_design}")
        print(f"  exported      {out}")
        steps = data["solidcraft"]["step_count"]
        print(f"  steps         {steps if steps is not None else '?'} ok")
        for warning in data["solidcraft"]["warnings"]:
            print(f"    ! {warning}")
        print()
        _print_report(analysis)
        if gate_path:
            print(f"  gate          {gate_path}")

    return {"PASS": PASS, "FAIL": FAIL, "UNVERIFIED": UNVERIFIED}[status]


# ---------------------------------------------------------------------------
# action: inspect
# ---------------------------------------------------------------------------

def action_inspect(args) -> int:
    probe = sc.probe(args.solidcraft)
    try:
        mesh = engine.load_mesh(args.input)
    except engine.MeshError as exc:
        return _fail_input(str(exc), args, probe=probe)

    mesh, transform_errors = _transform_from_args(mesh, args)
    analysis = engine.analyze(mesh, source=str(args.input),
                              fmt=pathlib.Path(args.input).suffix.lstrip(".").lower())
    status = _VERDICT_TO_STATUS[analysis["printability"]["verdict"]]
    reason = analysis["printability"]["verdict"].replace("_", " ")
    if transform_errors:
        reason += "; " + "; ".join(transform_errors)

    artifacts = []
    if args.report:
        artifacts.append(_write_json(pathlib.Path(args.report), analysis))

    data = {"inspection": analysis, "solidcraft": probe,
            "solidcraft_required": False}
    gate = _gate(status, reason, artifacts, data)
    gate_path = _write_gate(args, gate)
    if gate_path:
        artifacts.append(gate_path)  # printed only; the gate file must not list itself

    if args.json:
        print(json.dumps(gate, ensure_ascii=False))
    else:
        _print_report(analysis)
        for path in artifacts:
            print(f"  written       {path}")
        for err in transform_errors:
            print(f"  transform     {err}")
        if not probe["installed"]:
            print(f"  solidcraft    not installed (inspect does not need it)")

    return {"PASS": PASS, "FAIL": FAIL, "UNVERIFIED": UNVERIFIED}[status]


# ---------------------------------------------------------------------------
# action: repair
# ---------------------------------------------------------------------------

def action_repair(args) -> int:
    probe = sc.probe(args.solidcraft)
    try:
        mesh = engine.load_mesh(args.input)
    except engine.MeshError as exc:
        return _fail_input(str(exc), args, probe=probe)

    mesh, transform_errors = _transform_from_args(mesh, args)

    repaired, report = engine.repair(
        mesh,
        fill_holes=not args.no_fill_holes,
        max_loop_vertices=args.max_hole_loop,
        planarity_tol=args.planarity_tol,
    )
    report["source"] = str(args.input)
    report["solidcraft"] = probe

    out_path = pathlib.Path(args.output) if args.output else _default_output(args)
    try:
        engine.export_mesh(repaired, out_path, ascii_stl=args.ascii,
                           file_type=args.format)
    except engine.MeshError as exc:
        print(f"3d-fabric: {exc}", file=sys.stderr)
        return FAIL

    report["artifacts"] = [str(out_path)]
    artifacts = [out_path]

    status = "PASS" if report["success"] else (
        "UNVERIFIED" if report["after"]["topology"]["watertight"] else "FAIL"
    )
    after = report["after"]
    reason = (
        f"{after['topology']['watertight'] and 'watertight' or 'still open'}; "
        f"holes {after['topology']['hole_loop_count']}, "
        f"non-manifold edges {after['topology']['nonmanifold_edge_count']}"
    )
    if transform_errors:
        reason += "; " + "; ".join(transform_errors)

    report_path = None
    if args.report:
        report_path = _write_json(pathlib.Path(args.report), report)
        artifacts.append(report_path)

    gate = _gate(status, reason, artifacts, report)
    gate_path = _write_gate(args, gate)
    if gate_path:
        artifacts.append(gate_path)  # printed only; the gate file must not list itself

    if args.json:
        print(json.dumps(gate, ensure_ascii=False))
    else:
        _print_repair_report(report, out_path, report_path, gate_path)

    return {"PASS": PASS, "FAIL": FAIL, "UNVERIFIED": UNVERIFIED}[status]


def _require_solidcraft(args, probe: dict, action: str):
    """Return an exit code when the CLI is missing, else None."""
    if probe["installed"]:
        return None
    gate = _gate("UNVERIFIED", sc.MISSING_MESSAGE, [],
                 {"probe": probe, "action": action}, evidence="UNVERIFIED")
    gate_path = _write_gate(args, gate)
    if gate_path:
        gate["artifacts"] = [str(gate_path)]
    if args.json:
        print(json.dumps(gate, ensure_ascii=False))
    else:
        print(f"3d-fabric: {sc.MISSING_MESSAGE}", file=sys.stderr)
        _print_probe(probe)
    return UNVERIFIED


def _design_source(args):
    """Resolve --input for the design-based actions; returns (path, error)."""
    if not args.input:
        return None, "this action needs --input <design.sc|part.step>"
    source = pathlib.Path(args.input).resolve()
    if not source.is_file():
        return None, f"design not found: {source}"
    return source, None


# ---------------------------------------------------------------------------
# action: measure
# ---------------------------------------------------------------------------

def action_measure(args) -> int:
    probe = sc.probe(args.solidcraft)
    blocked = _require_solidcraft(args, probe, "measure")
    if blocked is not None:
        return blocked

    source, error = _design_source(args)
    if error or source is None:
        return _fail_input(error or "design not found", args, probe=probe)

    try:
        result = sc.eval_design(probe["path"], source, timeout=args.timeout)
    except sc.SolidCraftError as exc:
        return _fail_input(str(exc), args, probe=probe)

    if not result["ok"]:
        gate = _gate("FAIL", result["error"] or "SolidCraft eval failed", [],
                     {"probe": probe, "design": str(source)},
                     evidence="UNVERIFIED")
        gate_path = _write_gate(args, gate)
        if gate_path:
            gate["artifacts"] = [str(gate_path)]
        if args.json:
            print(json.dumps(gate, ensure_ascii=False))
        else:
            print(f"3d-fabric: {result['error']}", file=sys.stderr)
        return FAIL

    measurements = result["measurements"] or {}
    bodies = measurements.get("bodies") or []
    all_closed = bool(bodies) and all(bool(b.get("closed")) for b in bodies)
    totals = {
        "body_count": measurements.get("body_count", len(bodies)),
        "volume_mm3": round(sum(float(b.get("volume_mm3") or 0) for b in bodies), 3),
        "mass_g": round(sum(float(b.get("mass_g") or 0) for b in bodies), 3),
        "area_mm2": round(sum(float(b.get("area_mm2") or 0) for b in bodies), 3),
        "all_closed": all_closed,
    }
    status = "PASS" if all_closed else "UNVERIFIED"
    reason = (f"{totals['body_count']} body(ies), {totals['volume_mm3']} mm^3, "
              f"{totals['mass_g']} g, "
              + ("all closed" if all_closed else "some bodies are open"))

    artifacts = []
    if args.report:
        artifacts.append(_write_json(pathlib.Path(args.report),
                                     {"design": str(source), **measurements}))
    data = {"probe": probe, "design": str(source), "totals": totals,
            "measurements": measurements}
    gate = _gate(status, reason, artifacts, data,
                 evidence="EXACT" if all_closed else "UNVERIFIED")
    gate_path = _write_gate(args, gate)
    if gate_path:
        artifacts.append(gate_path)

    if args.json:
        print(json.dumps(gate, ensure_ascii=False))
    else:
        print("3d-fabric · measure")
        print(f"  design        {source}")
        print(f"  bodies        {totals['body_count']}")
        for body in bodies:
            bbox = body.get("bbox") or {}
            lo, hi = bbox.get("min"), bbox.get("max")
            closed = "OK" if body.get("closed") else "!!"
            print(f"  {body.get('name', 'Body'):<13} "
                  f"volume {body.get('volume_mm3', 0):.3f} mm^3   "
                  f"area {body.get('area_mm2', 0):.3f} mm^2   "
                  f"mass {body.get('mass_g', 0):.3f} g   closed[{closed}]")
            if lo and hi:
                print(f"                bbox {_fmt_vec(lo)} .. {_fmt_vec(hi)}")
            types = body.get("face_types") or {}
            if types:
                print(f"                faces {body.get('faces')} ("
                      + ", ".join(f"{k} {v}" for k, v in sorted(types.items())) + ")")
        params = measurements.get("params") or []
        if params:
            print(f"  parameters    {len(params)}")
        for path in artifacts:
            print(f"  written       {path}")

    return {"PASS": PASS, "FAIL": FAIL, "UNVERIFIED": UNVERIFIED}[status]


# ---------------------------------------------------------------------------
# action: snapshot
# ---------------------------------------------------------------------------

def action_snapshot(args) -> int:
    probe = sc.probe(args.solidcraft)
    blocked = _require_solidcraft(args, probe, "snapshot")
    if blocked is not None:
        return blocked

    source, error = _design_source(args)
    if error or source is None:
        return _fail_input(error or "design not found", args, probe=probe)

    out = (pathlib.Path(args.output) if args.output
           else source.with_suffix(".png")).resolve()

    try:
        result = sc.snapshot(
            probe["path"], source, out,
            view=args.view, width=args.width, height=args.height,
            section=args.section, bodies=args.body, timeout=args.timeout,
        )
    except sc.SolidCraftError as exc:
        return _fail_input(str(exc), args, probe=probe)

    data = {"probe": probe, "design": str(source), "image": result["path"],
            "bytes": result["bytes"], "info": result["info"]}
    if not result["ok"]:
        gate = _gate("FAIL", result["error"] or "snapshot failed", [],
                     data, evidence="UNVERIFIED")
        gate_path = _write_gate(args, gate)
        if gate_path:
            gate["artifacts"] = [str(gate_path)]
        if args.json:
            print(json.dumps(gate, ensure_ascii=False))
        else:
            print(f"3d-fabric: {result['error']}", file=sys.stderr)
        return FAIL

    artifacts = [out]
    info = result["info"] or {}
    size = ""
    if info.get("width") and info.get("height"):
        size = f" ({info['width']}x{info['height']})"
    gate = _gate("PASS", f"rendered {out.name}{size}", artifacts, data)
    gate_path = _write_gate(args, gate)
    if gate_path:
        artifacts.append(gate_path)

    if args.json:
        print(json.dumps(gate, ensure_ascii=False))
    else:
        print("3d-fabric · snapshot")
        print(f"  design        {source}")
        print(f"  image         {out}{size}")
        print(f"  bytes         {result['bytes']}")
        if info.get("renderer"):
            print(f"  renderer      {info['renderer']}")
        if gate_path:
            print(f"  gate          {gate_path}")
    return PASS


# ---------------------------------------------------------------------------
# action: script
# ---------------------------------------------------------------------------

def action_script(args) -> int:
    probe = sc.probe(args.solidcraft)
    blocked = _require_solidcraft(args, probe, "script")
    if blocked is not None:
        return blocked

    source, error = _design_source(args)
    if error or source is None:
        return _fail_input(error or "design not found", args, probe=probe)

    out = (pathlib.Path(args.output) if args.output
           else source.with_suffix(".script.json")).resolve()

    try:
        result = sc.extract_script(probe["path"], source, out, timeout=args.timeout)
    except sc.SolidCraftError as exc:
        return _fail_input(str(exc), args, probe=probe)

    data = {"probe": probe, "design": str(source), "script": result["path"],
            "step_count": result["step_count"], "about": result["about"]}
    if not result["ok"]:
        gate = _gate("FAIL", result["error"] or "script extraction failed", [],
                     data, evidence="UNVERIFIED")
        gate_path = _write_gate(args, gate)
        if gate_path:
            gate["artifacts"] = [str(gate_path)]
        if args.json:
            print(json.dumps(gate, ensure_ascii=False))
        else:
            print(f"3d-fabric: {result['error']}", file=sys.stderr)
        return FAIL

    notes = []
    about = result["about"] or {}
    if about.get("replay"):
        notes.append(str(about["replay"]))

    data["notes"] = notes
    artifacts = [out]
    gate = _gate("PASS", f"extracted {result['step_count']} step(s)", artifacts, data)
    gate_path = _write_gate(args, gate)
    if gate_path:
        artifacts.append(gate_path)

    if args.json:
        print(json.dumps(gate, ensure_ascii=False))
    else:
        print("3d-fabric · script")
        print(f"  design        {source}")
        print(f"  script        {out}")
        print(f"  steps         {result['step_count']}")
        for note in notes:
            print(f"  note          {note}")
        if gate_path:
            print(f"  gate          {gate_path}")
    return PASS


def _default_output(args) -> pathlib.Path:
    src = pathlib.Path(args.input)
    suffix = (args.format or src.suffix.lstrip(".") or "stl").lower()
    if suffix == "stl_ascii":
        suffix = "stl"
    base = pathlib.Path(args.root) / "process" / "models" if args.root else src.parent
    return base / f"{src.stem}_repaired.{suffix}"


# ---------------------------------------------------------------------------
# shared failure path
# ---------------------------------------------------------------------------

def _fail_input(message: str, args, probe=None) -> int:
    data = {"error": message}
    if probe is not None:
        data["probe"] = probe
    payload = _gate("UNVERIFIED", message, [], data, evidence="UNVERIFIED")
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"3d-fabric: {message}", file=sys.stderr)
    if getattr(args, "root", None):
        path = pathlib.Path(args.root) / "process" / "gates" / f"{SKILL}_{_utc_stamp()}.json"
        _write_json(path, payload)
    return UNVERIFIED


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="3d-fabric",
        description="Natural-language 3D modelling through the local SolidCraft "
                    "CLI, plus print QC (trimesh) before slicing.",
    )
    p.add_argument("--action", required=True,
                   choices=["probe", "model", "measure", "snapshot", "script",
                            "inspect", "repair"],
                   help="probe: find SolidCraft; model: build + auto-inspect; "
                        "measure: B-rep measurements; snapshot: render a PNG; "
                        "script: extract a design's command list; "
                        "inspect: mesh report; repair: fix and export")
    p.add_argument("--input",
                   help="inspect/repair: mesh file; model: requirement JSON "
                        "(or a .sc/.step design); measure/snapshot/script: a "
                        "design (.sc) or STEP file")
    p.add_argument("--in", "--design", dest="design_in", metavar="DESIGN",
                   help="model: apply the script on top of this existing design")
    p.add_argument("--script",
                   help="model: SolidCraft script (.json) or design (.sc/.step)")
    p.add_argument("--output", help="output path for --action model/repair")
    p.add_argument("--format", help="export format (model: stl|step|3mf|obj; "
                                    "repair: stl|obj|ply|3mf|glb|stl_ascii)")
    p.add_argument("--quality", default=None, choices=["standard", "fine", "finest"],
                   help="SolidCraft tessellation quality (default standard)")
    p.add_argument("--prompt", help="the natural-language request, recorded in the report")
    p.add_argument("--script-out", help="where to write a materialised script "
                                        "(default: <output>.solidcraft.json)")
    p.add_argument("--save-design", help="SolidCraft .sc design path "
                                         "(default: <output>.sc)")
    p.add_argument("--no-save-design", action="store_true",
                   help="do not keep an editable .sc next to the export")
    p.add_argument("--timeout", type=float, default=300.0,
                   help="SolidCraft run timeout in seconds (default 300)")
    p.add_argument("--keep-results", action="store_true",
                   help="keep SolidCraft's per-step results JSON next to the export")
    p.add_argument("--solidcraft", help="explicit path to solidcraft-cli")
    p.add_argument("--root", help="workspace root; outputs land under "
                                  "<root>/process/{models,gates}")
    p.add_argument("--report", help="write the JSON report to this exact path")
    p.add_argument("--json", action="store_true",
                   help="print one machine-readable gate JSON line to stdout")

    t = p.add_argument_group("geometry transforms (applied after build/inspect)")
    t.add_argument("--scale", type=float, help="uniform scale factor (e.g. 25.4 for in->mm)")
    t.add_argument("--scale-xyz", help="per-axis scale, e.g. 1,1,2")
    t.add_argument("--translate", help="translation in model units, e.g. 10,0,-2.5")
    t.add_argument("--rotate", help="Euler XYZ rotation in degrees, e.g. 0,0,90")
    t.add_argument("--center", action="store_true",
                   help="move the bounding-box centre to the origin")

    r = p.add_argument_group("repair options")
    r.add_argument("--no-fill-holes", action="store_true", help="skip hole filling")
    r.add_argument("--max-hole-loop", type=int, default=256,
                   help="largest boundary loop (vertex count) to fan-fill (default 256)")
    r.add_argument("--planarity-tol", type=float, default=0.05,
                   help="reject a loop whose out-of-plane thickness exceeds this "
                        "fraction of its radius (default 0.05)")
    r.add_argument("--ascii", action="store_true", help="write ASCII STL instead of binary")

    v = p.add_argument_group("snapshot options")
    v.add_argument("--view", help="iso | front | back | top | bottom | left | right "
                                 "(or a view saved in the design)")
    v.add_argument("--width", type=int, help="image width in pixels")
    v.add_argument("--height", type=int, help="image height in pixels")
    v.add_argument("--section", help="cut the model, e.g. z=27 or XY")
    v.add_argument("--body", action="append", default=[],
                   help="draw one body as NAME:opacity=0.3,color=#rrggbb (repeatable)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.action == "probe":
        return action_probe(args)
    if args.action == "model":
        return action_model(args)
    if args.action == "measure":
        return action_measure(args)
    if args.action == "snapshot":
        return action_snapshot(args)
    if args.action == "script":
        return action_script(args)
    if args.action == "inspect":
        return action_inspect(args)
    return action_repair(args)


def _force_utf8_output() -> None:
    """Write UTF-8 whatever the console codepage is.

    The human report uses ``·``; on a cp936 console those bytes decode as
    U+FFFD for any caller reading the subprocess output as UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # not a TextIOWrapper (redirected / captured)
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except ValueError:  # already detached
            pass


if __name__ == "__main__":
    _force_utf8_output()
    sys.exit(main())
