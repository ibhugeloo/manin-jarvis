#!/usr/bin/env python3
"""
runner.py — runner de tests doctrine Jarvis.

Parse les scénarios markdown (frontmatter YAML), invoque `claude -p` sur chaque
prompt, vérifie les assertions (regex inclusion/exclusion), reporte les résultats.

Usage:
    python3 runner.py                          # tous les scénarios
    python3 runner.py scenarios/01-xxx.md      # un seul
    python3 runner.py --verbose                # affiche réponses Claude
    python3 runner.py --json                   # output JSON

Exit code:
    0 — tous les tests passent
    1 — au moins une assertion échoue
    2 — erreur runner (claude introuvable, parsing, etc.)
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("Erreur: PyYAML requis (`pip install PyYAML`).\n")
    sys.exit(2)


SCENARIOS_DIR = Path(__file__).parent / "scenarios"
CLAUDE_BIN = "claude"
DEFAULT_TIMEOUT = 180  # seconds


def parse_scenario(path: Path) -> dict:
    """Parse un fichier markdown avec frontmatter YAML."""
    content = path.read_text()
    if not content.startswith("---\n"):
        raise ValueError(f"{path.name}: pas de frontmatter YAML en tête")

    parts = content.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"{path.name}: frontmatter mal fermé")

    front = yaml.safe_load(parts[1])
    body = parts[2].strip()

    required = {"name", "prompt", "assertions"}
    missing = required - set(front.keys())
    if missing:
        raise ValueError(f"{path.name}: clés manquantes dans frontmatter: {missing}")

    return {
        "name": front["name"],
        "prompt": front["prompt"].strip(),
        "assertions": front["assertions"],
        "body": body,
        "path": str(path),
    }


def invoke_claude(prompt: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str, int]:
    """Lance claude -p et retourne (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        raise RuntimeError(f"binaire `{CLAUDE_BIN}` introuvable dans le PATH")
    except subprocess.TimeoutExpired:
        return "", f"timeout après {timeout}s", 124


def check_assertion(response: str, assertion: dict) -> tuple[bool, str]:
    """Vérifie une assertion. Retourne (passed, message)."""
    atype = assertion.get("type", "regex")
    pattern = assertion["pattern"]
    desc = assertion.get("description", pattern)

    if atype == "regex":
        if re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
            return True, desc
        return False, f"PATTERN MANQUANT: {desc} (regex: `{pattern}`)"
    elif atype == "not_regex":
        if re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
            return False, f"PATTERN INTERDIT TROUVÉ: {desc} (regex: `{pattern}`)"
        return True, desc
    else:
        return False, f"type d'assertion inconnu: {atype}"


def run_scenario(scenario: dict, verbose: bool = False) -> dict:
    """Lance un scénario complet. Retourne un dict de résultat."""
    start = time.time()
    stdout, stderr, rc = invoke_claude(scenario["prompt"])
    elapsed = time.time() - start

    if rc != 0 or not stdout.strip():
        return {
            "name": scenario["name"],
            "status": "error",
            "elapsed": elapsed,
            "error": stderr.strip() or f"exit code {rc}, sortie vide",
            "assertions": [],
            "response": stdout,
        }

    results = []
    all_passed = True
    for a in scenario["assertions"]:
        passed, msg = check_assertion(stdout, a)
        results.append({"passed": passed, "message": msg})
        if not passed:
            all_passed = False

    return {
        "name": scenario["name"],
        "status": "pass" if all_passed else "fail",
        "elapsed": elapsed,
        "assertions": results,
        "response": stdout if verbose else stdout[:200] + ("..." if len(stdout) > 200 else ""),
    }


def render_text(results: list[dict]) -> str:
    """Format texte humain pour les résultats."""
    lines = []
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    errors = sum(1 for r in results if r["status"] == "error")

    for r in results:
        icon = {"pass": "✅", "fail": "❌", "error": "⚠️ "}[r["status"]]
        lines.append(f"{icon} {r['name']}  ({r['elapsed']:.1f}s)")
        if r["status"] == "error":
            lines.append(f"    ERROR: {r['error']}")
        else:
            for a in r["assertions"]:
                sub_icon = "  ✓" if a["passed"] else "  ✗"
                lines.append(f"   {sub_icon} {a['message']}")
        if r["status"] != "pass":
            lines.append(f"    Réponse: {r['response'][:300]}")
        lines.append("")

    lines.append("─" * 60)
    lines.append(f"Total: {total}  ·  ✅ {passed}  ·  ❌ {failed}  ·  ⚠️ {errors}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Runner tests doctrine Jarvis")
    ap.add_argument("scenario", nargs="?", help="chemin d'un scénario unique")
    ap.add_argument("--verbose", action="store_true", help="affiche les réponses Claude complètes")
    ap.add_argument("--json", action="store_true", help="output JSON au lieu de texte")
    args = ap.parse_args()

    if args.scenario:
        paths = [Path(args.scenario)]
    else:
        paths = sorted(SCENARIOS_DIR.glob("*.md"))

    if not paths:
        sys.stderr.write(f"Aucun scénario trouvé dans {SCENARIOS_DIR}\n")
        sys.exit(2)

    scenarios = []
    for p in paths:
        try:
            scenarios.append(parse_scenario(p))
        except Exception as e:
            sys.stderr.write(f"Erreur parsing {p}: {e}\n")
            sys.exit(2)

    results = [run_scenario(s, verbose=args.verbose) for s in scenarios]

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(render_text(results))

    any_fail = any(r["status"] != "pass" for r in results)
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
