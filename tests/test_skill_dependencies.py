"""Every third-party module a skill script imports has to be declared somewhere.

The security review in 1.1.2 found twelve skills importing `cv2`, `PIL` and
`skimage` while no manifest in the repository mentioned any of them: on a clean
install those scripts stopped at `No module named 'cv2'` and `install.py
--check` still reported the plugin ready. A declaration nobody checks decays the
same way again, so the imports are read back out of the AST here.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Import name -> the distribution that provides it. Only the names whose two
# forms differ; `numpy` is `numpy`.
IMPORT_TO_PACKAGE = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "skimage": "scikit-image",
}

# Import names that are not distributions: the stdlib, Blender's own modules,
# and the plugin's own packages.
NOT_A_DISTRIBUTION = {"bpy", "bmesh", "mathutils", "scripts", "tests"}


def _normalize(spec: str) -> str:
    """`opencv-python>=4.8` -> `opencv-python`."""
    name = spec
    for marker in (">", "<", "=", ";", "["):
        name = name.split(marker, 1)[0]
    return name.strip().lower()


def _package_for(module: str) -> str:
    """`cv2` -> `opencv-python`; anything unlisted is its own distribution."""
    return _normalize(IMPORT_TO_PACKAGE.get(module) or module)


def _manifest() -> dict:
    return json.loads((PLUGIN_ROOT / "manifest.json").read_text(encoding="utf-8"))


def _declared() -> set[str]:
    """Required plus optional distributions from manifest.json."""
    data = _manifest()
    names = {_normalize(item) for item in data["dependencies"]}
    for group in data.get("optional_dependencies", {}).values():
        names |= {_normalize(item) for item in group["packages"]}
    return names


def _skill_imports() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in sorted((PLUGIN_ROOT / "skills").glob("*/scripts/*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module.split(".")[0]]
            else:
                continue
            for module in modules:
                if module in sys.stdlib_module_names or module in NOT_A_DISTRIBUTION:
                    continue
                found.setdefault(module, set()).add(str(path.relative_to(PLUGIN_ROOT)))
    return found


def test_every_third_party_import_in_a_skill_script_is_declared():
    declared = _declared()
    missing = {
        module: sorted(files)
        for module, files in _skill_imports().items()
        if _package_for(module) not in declared
    }
    assert not missing, "imported but declared nowhere: " + json.dumps(missing, indent=2)


def test_the_optional_extras_are_listed_in_every_place_that_sells_them():
    manifest = _manifest()
    skills = manifest["optional_dependencies"]["skills"]
    packages = [_normalize(item) for item in skills["packages"]]

    pyproject = (PLUGIN_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "[project.optional-dependencies]" in pyproject and "skills = [" in pyproject
    requirements = (PLUGIN_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for package in packages:
        assert package in pyproject, f"{package} missing from pyproject.toml"
        assert package in requirements, f"{package} missing from requirements.txt"

    # Every import named in the manifest has to map to one of those packages.
    for module in skills["imports"]:
        assert _package_for(module) in packages, module


def test_the_latest_changelog_entry_is_this_version():
    text = (PLUGIN_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = _manifest()["version"]
    assert f"## [{version}]" in text, f"CHANGELOG has no section for {version}"
