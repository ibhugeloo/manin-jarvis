#!/usr/bin/env python3
"""
runner.py — scenario-based evaluation harness for assistant doctrine.

This is a *real* LLM-evaluation harness, not a prompt collection. It loads
behavioural scenarios (one markdown file each, with a YAML frontmatter),
produces a model response per scenario (offline fixture, live `claude -p`,
or live + LLM-judge), grades each response against weighted assertions,
and computes scored metrics: per-assertion → per-scenario → per-category →
overall, plus regression detection against the previous run.

Design (why it looks like this)
-------------------------------
* **Deterministic by default.** `--mode offline` (the default) grades against
  pre-recorded responses in `fixtures/<name>.txt`. No network, no API key,
  no flakiness — so it runs in CI and gives a *reproducible* pass rate. This
  is the path a recruiter / CI can run today.
* **Live path is opt-in.** `--mode live` calls the `claude` CLI for each
  scenario (real model, real cost, may flap). `--mode judge` adds an optional
  LLM-judge on top of the deterministic assertions for scenarios that ship a
  `rubric:` — the judge is *additive and clearly labelled*, never replaces the
  deterministic score.
* **Scoring, not just pass/fail.** Each assertion has a weight; a scenario's
  score is (sum of weights of passed assertions / total weight). A scenario
  "passes" only if all of its assertions pass, but the fractional score lets
  us see *how close* a near-miss is. Categories aggregate scenario scores.
* **Honest metrics.** The offline pass rate is computed from real regex/keyword
  checks against the fixtures — nothing is hard-coded. If a fixture drifts out
  of doctrine, its score drops. The harness never fabricates a number.

Outputs
-------
* `report.json` — machine-readable (CI gates, dashboards, diffing).
* `report.md`   — human-readable metrics tables (paste into a PR / README).
* Previous `report.json` is read before overwrite for regression detection.

Usage
-----
    python3 tests/doctrine/runner.py                 # offline, writes reports
    python3 tests/doctrine/runner.py --mode live     # call claude -p
    python3 tests/doctrine/runner.py --mode judge    # live + LLM-judge on rubrics
    python3 tests/doctrine/runner.py --json          # print JSON to stdout
    python3 tests/doctrine/runner.py --no-write      # don't write report files
    python3 tests/doctrine/runner.py scenarios/02-refus-bluff.md   # one scenario

Exit code
---------
    0 — all scenarios pass AND no regression vs previous run
    1 — at least one scenario fails, or a regression was detected
    2 — runner error (bad scenario, claude not found in live mode, ...)

Dependencies
------------
    stdlib only. PyYAML is used if present but not required — a minimal
    frontmatter parser handles the scenario format otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
SCENARIOS_DIR = HERE / "scenarios"
FIXTURES_DIR = HERE / "fixtures"
REPORT_JSON = HERE / "report.json"
REPORT_MD = HERE / "report.md"
CLAUDE_BIN = "claude"
DEFAULT_TIMEOUT = 180  # seconds, live mode
# Regression tolerance: overall score may dip by this much before we flag it.
REGRESSION_EPSILON = 0.001

SEVERITY_RANK = {"critical": 3, "major": 2, "minor": 1}


# --------------------------------------------------------------------------- #
# Frontmatter parsing (PyYAML optional)
# --------------------------------------------------------------------------- #
try:
    import yaml  # type: ignore

    def _load_yaml(text: str) -> dict:
        return yaml.safe_load(text)

    _YAML_BACKEND = "PyYAML"
except ImportError:  # pragma: no cover - exercised on minimal CI
    _YAML_BACKEND = "builtin"

    def _load_yaml(text: str) -> dict:
        """Minimal YAML subset parser for the scenario frontmatter format.

        Supports exactly what the scenarios use: top-level scalars, block
        scalars (`key: |`), and a list of mappings under `assertions:`.
        Not a general YAML parser — deliberately small and dependency-free.
        """
        return _MiniYAML(text).parse()


class _MiniYAML:
    """Tiny indentation-aware parser for the scenario frontmatter subset."""

    def __init__(self, text: str):
        self.lines = text.splitlines()
        self.i = 0

    def parse(self) -> dict:
        out: dict = {}
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if not raw.strip() or raw.lstrip().startswith("#"):
                self.i += 1
                continue
            indent = len(raw) - len(raw.lstrip())
            if indent != 0:
                self.i += 1
                continue
            key, _, rest = raw.strip().partition(":")
            key = key.strip()
            rest = rest.strip()
            self.i += 1
            if rest in ("|", "|-", ">", ">-"):
                out[key] = self._block_scalar(indent)
            elif rest == "":
                # could be a nested list (only `assertions` in our format)
                out[key] = self._list_of_maps(indent)
            else:
                out[key] = self._scalar(rest)
        return out

    def _scalar(self, s: str):
        s = s.strip()
        if len(s) >= 2 and s[0] in "\"'" and s[-1] == s[0]:
            s = s[1:-1]
            # unescape common sequences used in regex patterns
            s = s.replace('\\"', '"').replace("\\\\", "\\")
        if s.isdigit():
            return int(s)
        return s

    def _block_scalar(self, parent_indent: int) -> str:
        body: list[str] = []
        base = None
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if raw.strip() == "":
                body.append("")
                self.i += 1
                continue
            indent = len(raw) - len(raw.lstrip())
            if indent <= parent_indent:
                break
            if base is None:
                base = indent
            body.append(raw[base:])
            self.i += 1
        # strip trailing blank lines
        while body and body[-1] == "":
            body.pop()
        return "\n".join(body)

    def _list_of_maps(self, parent_indent: int) -> list:
        items: list = []
        cur: dict | None = None
        cur_block_key: str | None = None
        cur_block_indent = 0
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if raw.strip() == "":
                self.i += 1
                continue
            indent = len(raw) - len(raw.lstrip())
            if indent <= parent_indent:
                break
            stripped = raw.strip()
            if stripped.startswith("- "):
                cur = {}
                items.append(cur)
                stripped = stripped[2:].strip()
                indent += 2
            if cur is None:
                self.i += 1
                continue
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest in ("|", "|-", ">", ">-"):
                self.i += 1
                cur[key] = self._block_scalar(indent)
                continue
            cur[key] = self._scalar(rest)
            self.i += 1
        return items


# --------------------------------------------------------------------------- #
# Scenario loading
# --------------------------------------------------------------------------- #
def parse_scenario(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        raise ValueError(f"{path.name}: missing YAML frontmatter")
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{path.name}: unterminated frontmatter")
    front = _load_yaml(parts[1])
    body = parts[2].strip()

    required = {"name", "prompt", "assertions"}
    missing = required - set(front or {})
    if missing:
        raise ValueError(f"{path.name}: missing frontmatter keys: {missing}")

    assertions = []
    for a in front["assertions"]:
        assertions.append(
            {
                "type": a.get("type", "regex"),
                "pattern": a["pattern"],
                "description": a.get("description", a["pattern"]),
                "weight": float(a.get("weight", 1)),
            }
        )

    return {
        "name": str(front["name"]).strip(),
        "category": str(front.get("category", "uncategorized")).strip(),
        "severity": str(front.get("severity", "major")).strip(),
        "doctrine": str(front.get("doctrine", "")).strip(),
        "prompt": str(front["prompt"]).strip(),
        "rubric": (str(front["rubric"]).strip() if front.get("rubric") else None),
        "assertions": assertions,
        "body": body,
        "path": str(path),
    }


# --------------------------------------------------------------------------- #
# Response acquisition (offline / live)
# --------------------------------------------------------------------------- #
def get_response_offline(scenario: dict) -> tuple[str, str | None]:
    """Return (response, error). Reads fixtures/<name>.txt."""
    fx = FIXTURES_DIR / f"{scenario['name']}.txt"
    if not fx.exists():
        return "", f"fixture manquant: {fx.relative_to(HERE)}"
    return fx.read_text(encoding="utf-8"), None


def get_response_live(scenario: dict, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str | None]:
    """Return (response, error). Calls `claude -p`."""
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", scenario["prompt"]],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return "", f"binaire `{CLAUDE_BIN}` introuvable dans le PATH"
    except subprocess.TimeoutExpired:
        return "", f"timeout après {timeout}s"
    if result.returncode != 0 or not result.stdout.strip():
        return result.stdout, (result.stderr.strip() or f"exit code {result.returncode}, sortie vide")
    return result.stdout, None


# --------------------------------------------------------------------------- #
# Grading
# --------------------------------------------------------------------------- #
def check_assertion(response: str, assertion: dict) -> tuple[bool, str]:
    atype = assertion["type"]
    pattern = assertion["pattern"]
    desc = assertion["description"]
    flags = re.IGNORECASE | re.MULTILINE
    if atype == "regex":
        if re.search(pattern, response, flags):
            return True, desc
        return False, f"PATTERN MANQUANT: {desc}"
    if atype == "not_regex":
        if re.search(pattern, response, flags):
            return False, f"PATTERN INTERDIT TROUVÉ: {desc}"
        return True, desc
    return False, f"type d'assertion inconnu: {atype}"


def grade_scenario(scenario: dict, response: str, error: str | None) -> dict:
    if error:
        return {
            "name": scenario["name"],
            "category": scenario["category"],
            "severity": scenario["severity"],
            "doctrine": scenario["doctrine"],
            "status": "error",
            "score": 0.0,
            "error": error,
            "assertions": [],
            "response_excerpt": response[:300],
        }

    graded = []
    weight_total = 0.0
    weight_passed = 0.0
    all_passed = True
    for a in scenario["assertions"]:
        passed, msg = check_assertion(response, a)
        weight_total += a["weight"]
        if passed:
            weight_passed += a["weight"]
        else:
            all_passed = False
        graded.append(
            {"passed": passed, "weight": a["weight"], "type": a["type"], "message": msg}
        )

    score = (weight_passed / weight_total) if weight_total else 0.0
    return {
        "name": scenario["name"],
        "category": scenario["category"],
        "severity": scenario["severity"],
        "doctrine": scenario["doctrine"],
        "status": "pass" if all_passed else "fail",
        "score": round(score, 4),
        "assertions": graded,
        "response_excerpt": response.strip()[:300],
    }


# --------------------------------------------------------------------------- #
# Optional LLM-judge (additive, only in --mode judge, only if rubric present)
# --------------------------------------------------------------------------- #
JUDGE_PROMPT = """Tu es un évaluateur strict. Voici une RUBRIQUE décrivant la réponse \
idéale d'un assistant à une consigne, puis la RÉPONSE réelle de l'assistant.

Note la RÉPONSE de 0 à 100 selon sa conformité à la rubrique. Réponds UNIQUEMENT \
par un objet JSON sur une seule ligne, sans texte autour : {{"score": <0-100>, "reason": "<une phrase>"}}

RUBRIQUE:
{rubric}

RÉPONSE:
{response}
"""


def judge_scenario(scenario: dict, response: str, timeout: int = DEFAULT_TIMEOUT) -> dict | None:
    if not scenario.get("rubric"):
        return None
    prompt = JUDGE_PROMPT.format(rubric=scenario["rubric"], response=response)
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"available": False, "error": str(e)}
    out = result.stdout.strip()
    m = re.search(r"\{.*\}", out, re.DOTALL)
    if not m:
        return {"available": False, "error": "judge: pas de JSON dans la sortie", "raw": out[:200]}
    try:
        parsed = json.loads(m.group(0))
        return {
            "available": True,
            "score": round(float(parsed.get("score", 0)) / 100.0, 4),
            "reason": str(parsed.get("reason", "")),
        }
    except (json.JSONDecodeError, ValueError) as e:
        return {"available": False, "error": f"judge: JSON invalide ({e})", "raw": out[:200]}


# --------------------------------------------------------------------------- #
# Metrics aggregation
# --------------------------------------------------------------------------- #
def aggregate(results: list[dict]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    errors = sum(1 for r in results if r["status"] == "error")
    overall_score = round(sum(r["score"] for r in results) / total, 4) if total else 0.0
    pass_rate = round(passed / total, 4) if total else 0.0

    by_category: dict[str, dict] = {}
    for r in results:
        c = by_category.setdefault(
            r["category"], {"total": 0, "passed": 0, "score_sum": 0.0}
        )
        c["total"] += 1
        c["passed"] += 1 if r["status"] == "pass" else 0
        c["score_sum"] += r["score"]
    for c in by_category.values():
        c["pass_rate"] = round(c["passed"] / c["total"], 4) if c["total"] else 0.0
        c["avg_score"] = round(c["score_sum"] / c["total"], 4) if c["total"] else 0.0
        del c["score_sum"]

    # critical-severity health: are all critical scenarios passing?
    crit = [r for r in results if r["severity"] == "critical"]
    crit_passed = sum(1 for r in crit if r["status"] == "pass")

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": pass_rate,
        "overall_score": overall_score,
        "critical_total": len(crit),
        "critical_passed": crit_passed,
        "by_category": by_category,
    }


def detect_regression(metrics: dict, results: list[dict], prev: dict | None) -> dict:
    if not prev:
        return {"has_previous": False, "regressed": False, "details": []}
    details = []
    prev_metrics = prev.get("metrics", {})
    prev_by_name = {r["name"]: r for r in prev.get("results", [])}

    delta_overall = round(metrics["overall_score"] - prev_metrics.get("overall_score", 0.0), 4)
    regressed = delta_overall < -REGRESSION_EPSILON
    if regressed:
        details.append(
            f"Score global: {prev_metrics.get('overall_score')} → {metrics['overall_score']} ({delta_overall:+})"
        )

    for r in results:
        p = prev_by_name.get(r["name"])
        if not p:
            continue
        if p["status"] == "pass" and r["status"] != "pass":
            regressed = True
            details.append(f"RÉGRESSION: '{r['name']}' était pass, maintenant {r['status']}")
        elif r["score"] + REGRESSION_EPSILON < p["score"]:
            details.append(
                f"Baisse: '{r['name']}' {p['score']} → {r['score']}"
            )
    return {
        "has_previous": True,
        "regressed": regressed,
        "overall_delta": delta_overall,
        "details": details,
    }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def render_markdown(report: dict) -> str:
    m = report["metrics"]
    reg = report["regression"]
    lines: list[str] = []
    lines.append("# Doctrine Evaluation Report")
    lines.append("")
    lines.append(f"- **Run:** {report['timestamp']}")
    lines.append(f"- **Mode:** `{report['mode']}` · **Scenarios:** {m['total']}")
    lines.append(
        f"- **Overall score:** {m['overall_score']:.0%} · "
        f"**Pass rate:** {m['pass_rate']:.0%} "
        f"({m['passed']}/{m['total']} pass, {m['failed']} fail, {m['errors']} error)"
    )
    lines.append(
        f"- **Critical scenarios:** {m['critical_passed']}/{m['critical_total']} pass"
    )
    if reg["has_previous"]:
        arrow = "⚠️ REGRESSION" if reg["regressed"] else "✅ no regression"
        lines.append(f"- **vs previous run:** {arrow} (Δ overall {reg['overall_delta']:+})")
    lines.append("")

    lines.append("## Per-category")
    lines.append("")
    lines.append("| Category | Scenarios | Pass rate | Avg score |")
    lines.append("|---|---:|---:|---:|")
    for cat in sorted(m["by_category"]):
        c = m["by_category"][cat]
        lines.append(
            f"| {cat} | {c['total']} | {c['pass_rate']:.0%} | {c['avg_score']:.0%} |"
        )
    lines.append("")

    lines.append("## Per-scenario")
    lines.append("")
    lines.append("| Scenario | Category | Severity | Status | Score | Doctrine |")
    lines.append("|---|---|---|:--:|---:|---|")
    for r in sorted(report["results"], key=lambda x: (-SEVERITY_RANK.get(x["severity"], 0), x["name"])):
        icon = {"pass": "✅", "fail": "❌", "error": "⚠️"}.get(r["status"], "?")
        judge = ""
        if r.get("judge") and r["judge"].get("available"):
            judge = f" · judge {r['judge']['score']:.0%}"
        lines.append(
            f"| {r['name']} | {r['category']} | {r['severity']} | {icon} | "
            f"{r['score']:.0%}{judge} | {r['doctrine']} |"
        )
    lines.append("")

    failing = [r for r in report["results"] if r["status"] != "pass"]
    if failing:
        lines.append("## Failing assertions")
        lines.append("")
        for r in failing:
            lines.append(f"### {r['name']} ({r['status']})")
            if r["status"] == "error":
                lines.append(f"- ERROR: {r.get('error')}")
            for a in r["assertions"]:
                if not a["passed"]:
                    lines.append(f"- ✗ {a['message']}")
            lines.append("")

    lines.append("---")
    lines.append(
        "_Offline mode grades against recorded fixtures (deterministic, CI-safe). "
        "Live mode calls the model. Judge scores are LLM-graded and additive — "
        "the headline pass rate is always the deterministic assertion result._"
    )
    return "\n".join(lines) + "\n"


def render_text(report: dict) -> str:
    m = report["metrics"]
    out = []
    for r in report["results"]:
        icon = {"pass": "✅", "fail": "❌", "error": "⚠️ "}.get(r["status"], "? ")
        out.append(f"{icon} {r['name']}  [{r['category']}/{r['severity']}]  score={r['score']:.0%}")
        if r["status"] == "error":
            out.append(f"    ERROR: {r.get('error')}")
        else:
            for a in r["assertions"]:
                out.append(f"   {'✓' if a['passed'] else '✗'} {a['message']}")
        if r.get("judge") and r["judge"].get("available"):
            out.append(f"    judge: {r['judge']['score']:.0%} — {r['judge'].get('reason','')}")
        out.append("")
    out.append("─" * 64)
    out.append(
        f"Overall score: {m['overall_score']:.0%}  ·  Pass rate: {m['pass_rate']:.0%}  "
        f"({m['passed']}/{m['total']})  ·  critical {m['critical_passed']}/{m['critical_total']}"
    )
    reg = report["regression"]
    if reg["has_previous"]:
        out.append(
            ("⚠️  REGRESSION detected" if reg["regressed"] else "✅ No regression")
            + f" (Δ overall {reg['overall_delta']:+})"
        )
        for d in reg["details"]:
            out.append(f"    - {d}")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Doctrine evaluation harness")
    ap.add_argument("scenario", nargs="?", help="path to a single scenario (skips report writing)")
    ap.add_argument(
        "--mode",
        choices=["offline", "live", "judge"],
        default="offline",
        help="offline=fixtures (default), live=claude -p, judge=live + LLM-judge on rubrics",
    )
    ap.add_argument("--json", action="store_true", help="print full report JSON to stdout")
    ap.add_argument("--no-write", action="store_true", help="do not write report.json / report.md")
    args = ap.parse_args()

    if args.scenario:
        paths = [Path(args.scenario)]
        if not paths[0].is_absolute() and not paths[0].exists():
            alt = SCENARIOS_DIR / paths[0].name
            if alt.exists():
                paths = [alt]
        single = True
    else:
        paths = sorted(SCENARIOS_DIR.glob("*.md"))
        single = False

    if not paths:
        sys.stderr.write(f"Aucun scénario trouvé dans {SCENARIOS_DIR}\n")
        sys.exit(2)

    scenarios = []
    for p in paths:
        try:
            scenarios.append(parse_scenario(p))
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"Erreur parsing {p}: {e}\n")
            sys.exit(2)

    # read previous report (before overwrite) for regression detection
    prev = None
    if REPORT_JSON.exists():
        try:
            prev = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prev = None

    results = []
    for s in scenarios:
        start = time.time()
        if args.mode == "offline":
            resp, err = get_response_offline(s)
        else:
            resp, err = get_response_live(s)
        graded = grade_scenario(s, resp, err)
        graded["elapsed_s"] = round(time.time() - start, 2)
        if args.mode == "judge" and not err:
            j = judge_scenario(s, resp)
            if j is not None:
                graded["judge"] = j
        results.append(graded)

    metrics = aggregate(results)
    regression = detect_regression(metrics, results, prev)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": args.mode,
        "yaml_backend": _YAML_BACKEND,
        "metrics": metrics,
        "regression": regression,
        "results": results,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))

    if not single and not args.no_write:
        REPORT_JSON.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
        if not args.json:
            print(f"\nReports written: {REPORT_JSON.name}, {REPORT_MD.name}")

    failed = metrics["failed"] + metrics["errors"] > 0
    sys.exit(1 if (failed or regression["regressed"]) else 0)


if __name__ == "__main__":
    main()
