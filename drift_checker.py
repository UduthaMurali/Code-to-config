#!/usr/bin/env python3
"""
drift_checker.py
────────────────
Detects code-to-config drift between Python source files and deployment
configuration files (docker-compose.yml, .env.example, Kubernetes YAML).

Exit codes:
  0 – no critical drift found
  1 – drift detected (missing variables); blocks the Pull Request
"""

import ast
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Run: pip install pyyaml")
    sys.exit(2)


# ── Helpers ────────────────────────────────────────────────────────────────

def scan_python_files(root: Path) -> dict[str, str]:
    """Return {VAR_NAME: source_file} for every os.getenv / os.environ ref."""
    found: dict[str, str] = {}
    skip = {"drift_checker.py", "setup.py", "conf.py"}
    for py_file in root.rglob("*.py"):
        if py_file.name in skip:
            continue
        if any(p in py_file.parts for p in ("test", "tests", ".venv", "venv")):
            continue
        found.update(_extract_from_file(py_file))
    return found


def _extract_from_file(filepath: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return found

    rel = str(filepath)
    for node in ast.walk(tree):
        # os.getenv("VAR") / os.getenv("VAR", "default")
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                found[node.args[0].value] = rel
                continue
            # os.environ.get("VAR")
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "environ"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                found[node.args[0].value] = rel
                continue
        # os.environ["VAR"]
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "environ"
            and isinstance(node.slice, ast.Constant)
        ):
            found[node.slice.value] = rel
    return found


def scan_docker_compose(path: Path) -> set[str]:
    declared: set[str] = set()
    if not path.exists():
        return declared
    data = yaml.safe_load(path.read_text()) or {}
    for svc in data.get("services", {}).values():
        env = svc.get("environment", {})
        if isinstance(env, dict):
            declared.update(env.keys())
        elif isinstance(env, list):
            for item in env:
                key = item.split("=")[0].strip() if "=" in item else item.strip()
                declared.add(key)
    return declared


def scan_dotenv(path: Path) -> set[str]:
    declared: set[str] = set()
    if not path.exists():
        return declared
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            declared.add(line.split("=")[0].strip())
    return declared


def scan_k8s(k8s_dir: Path) -> set[str]:
    declared: set[str] = set()
    if not k8s_dir.is_dir():
        return declared
    for yml in list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml")):
        try:
            for doc in yaml.safe_load_all(yml.read_text()):
                if not isinstance(doc, dict):
                    continue
                kind = doc.get("kind", "")
                if kind == "Deployment":
                    spec = doc.get("spec", {}).get("template", {}) \
                               .get("spec", {})
                    for container in spec.get("containers", []):
                        for entry in container.get("env", []):
                            if "name" in entry:
                                declared.add(entry["name"])
                elif kind == "ConfigMap":
                    declared.update((doc.get("data") or {}).keys())
        except Exception:
            pass
    return declared


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> int:
    root = Path(".")

    # --- Scan code ---
    code_vars = scan_python_files(root)

    # --- Scan configs ---
    config_vars: set[str] = set()
    config_sources: list[str] = []

    compose = root / "docker-compose.yml"
    env_example = root / ".env.example"
    k8s_dir = root / "k8s"

    if compose.exists():
        config_vars |= scan_docker_compose(compose)
        config_sources.append("`docker-compose.yml`")
    if env_example.exists():
        config_vars |= scan_dotenv(env_example)
        config_sources.append("`.env.example`")
    if k8s_dir.is_dir():
        config_vars |= scan_k8s(k8s_dir)
        config_sources.append("`k8s/`")

    if not config_sources:
        print("⚠️  No configuration files found. Skipping drift check.")
        return 0

    # --- Diff ---
    missing  = {v: f for v, f in code_vars.items() if v not in config_vars}
    unused   = config_vars - set(code_vars.keys())

    # --- Report ---
    lines: list[str] = []

    if missing:
        lines.append("## ❌ Config Drift Detected!\n")
        lines.append(
            "The following environment variables are **referenced in code** "
            "but **not declared** in any deployment configuration:\n"
        )
        lines.append("| Variable | Source File |")
        lines.append("|----------|-------------|")
        for var, src in sorted(missing.items()):
            lines.append(f"| `{var}` | `{src}` |")
        lines.append("")
        lines.append(
            "> **Action Required:** Add the missing variables to your "
            "deployment configuration before this PR can be merged."
        )
    else:
        lines.append("## ✅ No Drift Detected\n")
        lines.append(
            "All environment variables referenced in code are declared "
            "in the deployment configuration."
        )

    if unused:
        lines.append("\n### ⚠️ Unused Config Variables\n")
        lines.append(
            "These variables are declared in config but never referenced "
            "in code (consider removing them):\n"
        )
        for var in sorted(unused):
            lines.append(f"- `{var}`")

    lines.append(f"\n**Config files checked:** {', '.join(config_sources)}")
    lines.append(
        f"**Python files scanned:** "
        + ", ".join(f"`{f}`" for f in sorted(set(code_vars.values())))
    )

    print("\n".join(lines))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
