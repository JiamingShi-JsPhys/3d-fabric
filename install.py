"""Environment check + installer for 3d-fabric.

The plugin channel installs the skill but cannot check a machine, and this
plugin has two prerequisites a package manager will not touch: the Python
geometry stack and a local SolidCraft installation.

Three jobs, one command each:

    python install.py --check                 # python, deps, SolidCraft, examples
    python install.py --deps                  # pip install -r requirements.txt
    python install.py --skill-dir             # copy into ~/.claude/skills/3d-fabric

`--skill-dir` is for hosts without a plugin channel: it copies `run.py`, the
`scripts/` package and `SKILL.md` together, because `run.py` cannot run without
them. `--dry-run` prints what would happen; `--force` overwrites an existing
skill directory.

A fourth job covers the hosts that read a *rule file* instead of a plugin:
Cursor, Windsurf, Cline, Continue, Roo Code, GitHub Copilot and the generic
`AGENTS.md` that Codex and opencode read. No vendor's installer understands
another vendor's rule file, so this one does:

    python install.py --project DIR           # every project-scoped rule file
    python install.py --global                # user-scoped rules for hosts present
    python install.py --list                  # destinations only, write nothing

Rule files are copied verbatim from this repository (`.cursor/rules/…`,
`.clinerules/…`, `.github/copilot-instructions.md`, `AGENTS.md`), so an
installed copy is byte-identical to the one the test suite checks against
`AGENTS.md`. An identical file reports `unchanged`; a differing one is left
alone unless `--force` is passed.

Exit codes: 0 everything required is present, 1 a hard problem, 2 something is
missing but optional (SolidCraft, which only `model` needs).

License: MIT. See LICENSE.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_SKILL_DIR = pathlib.Path.home() / ".claude" / "skills" / "3d-fabric"

SKILL_FILES = [
    ("run.py", "run.py"),
    ("scripts/__init__.py", "scripts/__init__.py"),
    ("scripts/engine.py", "scripts/engine.py"),
    ("scripts/solidcraft.py", "scripts/solidcraft.py"),
    ("skills/3d-fabric/SKILL.md", "SKILL.md"),
    ("requirements.txt", "requirements.txt"),
    ("LICENSE", "LICENSE"),
]

# Whole trees copied beside the skill: SKILL.md points into references/,
# and the bundled third-party licence text must travel with the code.
SKILL_TREES = [
    ("references", "references"),
    ("licenses", "licenses"),
]

REQUIRED_MODULES = ("trimesh", "numpy", "scipy", "networkx", "lxml")

# ---------------------------------------------------------------------------
# rule files for the hosts that have no plugin channel
# ---------------------------------------------------------------------------

# host key -> (destination relative to the project root, source file in repo)
PROJECT_RULES = {
    "cursor": (".cursor/rules/3d-fabric.mdc", ".cursor/rules/3d-fabric.mdc"),
    "windsurf": (".windsurf/rules/3d-fabric.md", ".windsurf/rules/3d-fabric.md"),
    "cline": (".clinerules/3d-fabric.md", ".clinerules/3d-fabric.md"),
    "continue": (".continue/rules/3d-fabric.md", ".continue/rules/3d-fabric.md"),
    "roo": (".roo/rules/3d-fabric.md", ".roo/rules/3d-fabric.md"),
    "copilot": (".github/copilot-instructions.md", ".github/copilot-instructions.md"),
    "agents": ("AGENTS.md", "AGENTS.md"),
}


def global_rules() -> dict:
    """User-scoped rule targets, keyed by host.

    Claude Code is deliberately absent: it has a plugin channel, so the
    contract reaches it through the plugin rather than through
    ``~/.claude/CLAUDE.md`` — which belongs to the user, not to this repo.
    """
    home = pathlib.Path.home()
    codex_home = pathlib.Path(
        os.environ.get("CODEX_HOME") or (home / ".codex")
    ).expanduser()
    return {
        "opencode": (home / ".config" / "opencode" / "AGENTS.md", "AGENTS.md"),
        "codex": (codex_home / "AGENTS.md", "AGENTS.md"),
    }


def _same_bytes(left: pathlib.Path, right: pathlib.Path) -> bool:
    try:
        return left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def _install_rule(source: str, destination: pathlib.Path, force: bool,
                  dry_run: bool) -> str:
    """Copy one rule file; return 'wrote', 'unchanged' or 'skipped'."""
    src = REPO_ROOT / source
    if not src.is_file():
        raise SystemExit(f"install.py: missing source rule file: {src}")
    if destination.is_file() and _same_bytes(src, destination):
        return "unchanged"
    if destination.is_file() and not force:
        return "skipped"
    if dry_run:
        return "wrote"
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(destination.parent),
                                         prefix=".3d-fabric-", suffix=".tmp")
    os.close(handle)
    try:
        shutil.copyfile(src, temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return "wrote"


def _select(only: str | None, keys) -> list:
    keys = list(keys)
    if not only:
        return keys
    wanted = [part.strip() for part in only.split(",") if part.strip()]
    unknown = [name for name in wanted if name not in keys]
    if unknown:
        raise SystemExit("install.py: unknown host(s): " + ", ".join(unknown)
                         + "\nknown: " + ", ".join(keys))
    return wanted


def action_rules(project: str | None, global_scope: bool, only: str | None,
                 force: bool, dry_run: bool, list_only: bool) -> int:
    """Copy the contract into every supported host's rule location."""
    if list_only:
        print("project scope (--project DIR):")
        for key, (relative, _source) in PROJECT_RULES.items():
            print(f"  {key:<10} {relative}")
        print("global scope (--global), written only when the host is present:")
        for key, (destination, _source) in global_rules().items():
            state = "" if destination.parent.is_dir() else "  (absent)"
            print(f"  {key:<10} {destination}{state}")
        return 0

    results = []
    if project:
        root = pathlib.Path(project).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        for key in _select(only, PROJECT_RULES):
            relative, source = PROJECT_RULES[key]
            results.append((key, root / relative,
                            _install_rule(source, root / relative, force, dry_run)))

    if global_scope:
        targets = global_rules()
        for key in _select(only, targets):
            destination, source = targets[key]
            if not destination.parent.is_dir():
                results.append((key, destination, "absent"))
                continue
            results.append((key, destination,
                            _install_rule(source, destination, force, dry_run)))

    if not results:
        print("install.py: nothing selected; pass --project DIR and/or --global.")
        return 1

    width = max(len(key) for key, _destination, _state in results)
    for key, destination, state in results:
        print(f"  {key:<{width}}  {state:<9}  {destination}")
    wrote = sum(1 for _key, _destination, state in results if state == "wrote")
    print(f"\n{wrote} file(s) written"
          + (" (dry run)" if dry_run else "")
          + ". Start a new session in the host to pick the rule up.")
    return 0



# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def _check_python() -> tuple:
    ok = sys.version_info >= (3, 10)
    return ok, f"Python {sys.version.split()[0]} (need 3.10+)"


def _check_deps() -> tuple:
    missing = []
    for name in REQUIRED_MODULES:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    if missing:
        return False, "missing Python packages: " + ", ".join(missing)
    import trimesh  # noqa: F401  (imported for the version string)

    return True, f"trimesh {trimesh.__version__}, numpy, scipy, networkx, lxml present"


def _check_solidcraft() -> tuple:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from scripts import solidcraft as sc  # pyright: ignore[reportAttributeAccessIssue]
    finally:
        sys.path.pop(0)
    info = sc.probe()
    if info["installed"]:
        return True, f"{info['path']} ({info['version']})"
    return False, sc.MISSING_MESSAGE


def _check_examples() -> tuple:
    files = ["examples/bracket_request.json", "examples/damaged_part.stl"]
    missing = [f for f in files if not (REPO_ROOT / f).is_file()]
    return (not missing), "both examples present" if not missing else "missing: " + ", ".join(missing)


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------

def action_check() -> int:
    print("3d-fabric · check")
    results = {
        "python": _check_python(),
        "geometry stack": _check_deps(),
        "solidcraft": _check_solidcraft(),
        "examples": _check_examples(),
    }
    for label, (ok, detail) in results.items():
        print(f"  {label:<16} {'OK  ' if ok else 'MISS'}  {detail}")

    hard_ok = results["python"][0] and results["geometry stack"][0]
    cad_ok = results["solidcraft"][0]
    if not hard_ok:
        print("\n  Fix the entries marked MISS before using the plugin.")
        return 1
    if not cad_ok:
        print("\n  inspect / repair work now; model needs SolidCraft installed.")
        return 2
    print("\n  Ready. Try: python run.py --action model --input examples/bracket_request.json")
    return 0


def action_deps() -> int:
    req = REPO_ROOT / "requirements.txt"
    if not req.is_file():
        print(f"3d-fabric: {req} not found", file=sys.stderr)
        return 1
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req)]
    print("running: " + " ".join(cmd))
    return subprocess.call(cmd)


def action_skill_dir(target: pathlib.Path, force: bool, dry_run: bool) -> int:
    target = target.expanduser()
    if target.exists() and not force:
        print(f"3d-fabric: {target} already exists; pass --force to overwrite", file=sys.stderr)
        return 1

    print(f"3d-fabric · install skill -> {target}")
    for source_rel, dest_rel in SKILL_FILES:
        source = REPO_ROOT / source_rel
        if not source.is_file():
            print(f"  MISS  {source_rel} (source file absent)", file=sys.stderr)
            return 1
        dest = target / dest_rel
        if dry_run:
            print(f"  would copy  {source_rel} -> {dest_rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        print(f"  copied      {source_rel} -> {dest_rel}")

    for source_rel, dest_rel in SKILL_TREES:
        source = REPO_ROOT / source_rel
        if not source.is_dir():
            print(f"  MISS  {source_rel}/ (source directory absent)", file=sys.stderr)
            return 1
        if dry_run:
            print(f"  would copy  {source_rel}/ -> {dest_rel}/")
            continue
        shutil.copytree(source, target / dest_rel, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print(f"  copied      {source_rel}/ -> {dest_rel}/")

    if dry_run:
        print("\n  dry run: nothing written")
        return 0

    print("\n  Installed. The skill triggers on 3D-printing and parametric-modelling "
          "requests; commands inside it resolve to this directory.")
    print(f"  Self-test: python {target / 'run.py'} --action probe")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="install.py",
        description="Check this machine for 3d-fabric's prerequisites, install "
                    "the skill into a host skill directory, or copy the rule "
                    "file into the hosts that read one.",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true",
                   help="report python / deps / SolidCraft / examples (default)")
    g.add_argument("--deps", action="store_true",
                   help="pip install -r requirements.txt")
    g.add_argument("--skill-dir", nargs="?", const=str(DEFAULT_SKILL_DIR),
                   metavar="PATH",
                   help=f"copy the skill into PATH (default {DEFAULT_SKILL_DIR})")
    p.add_argument("--project", metavar="DIR",
                   help="copy every project-scoped rule file into DIR")
    p.add_argument("--global", dest="global_scope", action="store_true",
                   help="copy user-scoped rules for the hosts present here")
    p.add_argument("--only", metavar="HOSTS",
                   help="comma-separated subset, e.g. cursor,codex")
    p.add_argument("--list", dest="list_rules", action="store_true",
                   help="list every rule destination, then exit")
    p.add_argument("--dry-run", action="store_true", help="print actions, write nothing")
    p.add_argument("--force", action="store_true", help="overwrite an existing target")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_rules or args.project is not None or args.global_scope:
        return action_rules(args.project, args.global_scope, args.only,
                            args.force, args.dry_run, args.list_rules)
    if args.deps:
        return action_deps()
    if args.skill_dir:
        return action_skill_dir(pathlib.Path(args.skill_dir), args.force, args.dry_run)
    return action_check()


def _force_utf8_output() -> None:
    """Write UTF-8 whatever the console codepage is.

    Windows defaults to cp936 here, which turns the ``·`` in the header into
    bytes a UTF-8 reader reports as U+FFFD.
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
