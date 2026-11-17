#!/usr/bin/env python3
"""Gather evidence for a review of the current git changes.

Looks at what changed (committed on this branch plus uncommitted work), then
reports:

  * a suggested risk level (low, standard, high) and the reasons for it
  * which Review Playbook checklists apply
  * warnings found in the added lines, with file and line number
    (possible secrets, skipped tests, disabled safety checks, debug output...)
  * the build, test and lint commands this project appears to use

It only reads; it never changes files. It needs Python 3.9+ and git, and has
no other dependencies.

Usage:
    python3 review_context.py                # compare against the default branch
    python3 review_context.py --base HEAD~3  # compare against a specific ref
    python3 review_context.py --json         # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

CODE_EXT = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".swift", ".kt", ".java",
    ".go", ".rs", ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".m",
    ".mm", ".scala", ".dart", ".vue", ".svelte", ".sh", ".sql",
}
UI_EXT = {".html", ".css", ".scss", ".sass", ".less", ".jsx", ".tsx", ".vue", ".svelte",
          ".storyboard", ".xib"}
UI_PATH = re.compile(r"(^|/)(views?|components?|screens?|pages?|ui|templates?|layouts?|styles?)(/|$)", re.I)
SWIFT_UI = re.compile(r"(View|Screen|Cell)\.swift$")
BACKEND_PATH = re.compile(
    r"(^|/)(api|server|backend|routes?|controllers?|handlers?|services?|models?|migrations?|"
    r"supabase|db|database|prisma|functions|lambdas?|middleware)(/|$)", re.I)
BACKEND_EXT = {".sql", ".prisma"}
WRITING_EXT = {".md", ".mdx", ".rst", ".txt", ".adoc", ".tex", ".docx"}
DATA_EXT = {".csv", ".tsv", ".ipynb", ".parquet", ".xlsx", ".xls", ".jsonl"}
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs|Tests|UITests)(/|$)|"
                       r"(^|/)test_[^/]+$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$|Tests?\.swift$")
DEPENDENCY_FILES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "requirements.txt",
    "pyproject.toml", "poetry.lock", "Pipfile", "Pipfile.lock", "Package.swift",
    "Package.resolved", "Podfile", "Podfile.lock", "go.mod", "go.sum", "Cargo.toml",
    "Cargo.lock", "Gemfile", "Gemfile.lock", "build.gradle", "pom.xml", "composer.json",
}
CONFIG_PATH = re.compile(r"(^|/)(\.github/|\.gitlab-ci|Dockerfile|docker-compose|netlify\.toml|"
                         r"vercel\.json|terraform|k8s|helm|\.env)", re.I)

# Paths that raise the risk level on their own.
HIGH_RISK_PATH = [
    (re.compile(r"auth|login|logout|signin|signup|session|password|oauth|jwt|token", re.I),
     "touches authentication"),
    (re.compile(r"permission|role|acl|policy|policies|rls|access", re.I), "touches permissions"),
    (re.compile(r"payment|billing|invoice|checkout|stripe|price|pricing|wallet|refund", re.I),
     "touches money"),
    (re.compile(r"migration|migrate|schema\.(sql|prisma|rb)", re.I), "includes a schema migration"),
    (re.compile(r"(^|/)\.env|secret|credential|keychain", re.I), "touches secrets or credentials"),
    (re.compile(r"(^|/)(\.github/workflows|Dockerfile|terraform|k8s|helm)|netlify\.toml|vercel\.json", re.I),
     "changes deployment or CI configuration"),
]

# ---------------------------------------------------------------------------
# Patterns checked in added lines
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bsk-(proj-|ant-)?[A-Za-z0-9_-]{20,}"), "API secret key (sk-...)"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), "Google API key"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JWT"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token|service[_-]?role)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
     "hard-coded credential"),
]

LINE_CHECKS = [
    # (pattern, severity, message)
    (re.compile(r"(\bit|\bdescribe|\btest)\.(skip|only)\(|\bxit\(|\bxdescribe\(|@pytest\.mark\.skip|"
                r"@unittest\.skip|XCTSkip|\.skip\(\)"), "major", "test skipped or focused (.only)"),
    (re.compile(r"eslint-disable|@ts-ignore|@ts-nocheck|#\s*type:\s*ignore|#\s*noqa|"
                r"swiftlint:disable|//\s*nolint|rubocop:disable"), "major", "lint or type check disabled"),
    (re.compile(r"--no-verify|verify\s*=\s*False|rejectUnauthorized\s*:\s*false|"
                r"InsecureSkipVerify\s*:\s*true|NODE_TLS_REJECT_UNAUTHORIZED"), "major",
     "safety check switched off (hooks or TLS verification)"),
    (re.compile(r"\beval\s*\(|new Function\(|dangerouslySetInnerHTML|"
                r"\.(inner|outer)HTML\s*=(?!\s*(\"\"|''|``)\s*;?\s*$)|"
                r"pickle\.loads?\(|yaml\.load\((?!.*Loader)|shell\s*=\s*True"), "major",
     "dynamic code execution or unsafe HTML/deserialization"),
    (re.compile(r"(?i)\b(drop\s+table|truncate\s+table|delete\s+from\s+\w+\s*;)"), "major",
     "destructive SQL"),
    (re.compile(r"(?i)disable\s+row\s+level\s+security|service_role"), "major",
     "row level security off or service role key referenced"),
    (re.compile(r"except\s*:\s*(pass)?\s*$|except\s+Exception\s*:\s*pass|catch\s*\([^)]*\)\s*\{\s*\}|"
                r"catch\s*\{\s*\}"), "major", "error swallowed by an empty catch"),
    (re.compile(r"\btry!|as!\s"), "minor", "Swift force try or forced cast"),
    (re.compile(r"\b(TODO|FIXME|XXX|HACK)\b"), "minor", "TODO or FIXME left in"),
    (re.compile(r"console\.(log|debug)\(|\bdebugger\b|^\s*print\(|^\s*(var_)?dump\(|^\s*pp\s"), "minor",
     "debug output left in"),
]

CHECKLISTS = {
    "code": "references/code.md",
    "ui": "references/ui.md",
    "backend": "references/backend.md",
    "writing": "references/writing.md",
    "data": "references/research.md",
}

BINARY_LIMIT = 1_000_000  # bytes; larger added files are flagged


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    severity: str
    message: str
    file: str
    line: Optional[int] = None
    excerpt: str = ""


@dataclass
class Report:
    base: str
    files_changed: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    areas: List[str] = field(default_factory=list)
    checklists: List[str] = field(default_factory=list)
    risk: str = "low"
    risk_reasons: List[str] = field(default_factory=list)
    warnings: List[Finding] = field(default_factory=list)
    commands: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(args: List[str], cwd: Path) -> Tuple[int, str]:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout


def repo_root(start: Path) -> Optional[Path]:
    code, out = git(["rev-parse", "--show-toplevel"], start)
    return Path(out.strip()) if code == 0 else None


def default_base(root: Path) -> str:
    """Merge base with the default branch, or HEAD when on it / no branch exists."""
    _, branch = git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    branch = branch.strip()
    for cand in ("origin/main", "origin/master", "main", "master"):
        code, _ = git(["rev-parse", "--verify", "--quiet", cand], root)
        if code != 0:
            continue
        if cand.split("/")[-1] == branch:
            return "HEAD"
        code, mb = git(["merge-base", "HEAD", cand], root)
        if code == 0 and mb.strip():
            return mb.strip()
    return "HEAD"


def collect_diff(root: Path, base: str) -> str:
    """Unified diff of base..working tree (committed and uncommitted), plus untracked files."""
    code, _ = git(["rev-parse", "--verify", "--quiet", "HEAD"], root)
    if code != 0:  # no commits yet: everything is new
        diff = ""
    else:
        _, diff = git(["diff", "--no-color", "--unified=0", "--no-ext-diff", base, "--"], root)
    _, untracked = git(["ls-files", "--others", "--exclude-standard"], root)
    for rel in [u for u in untracked.splitlines() if u]:
        path = root / rel
        try:
            if path.stat().st_size > BINARY_LIMIT:
                diff += f"diff --git a/{rel} b/{rel}\nnew file\n+++ b/{rel}\n"
                continue
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            diff += f"diff --git a/{rel} b/{rel}\nnew file\n+++ b/{rel}\n"
            continue
        lines = text.splitlines()
        diff += f"diff --git a/{rel} b/{rel}\nnew file\n+++ b/{rel}\n@@ -0,0 +1,{len(lines)} @@\n"
        diff += "".join(f"+{l}\n" for l in lines)
    return diff


def parse_diff(diff: str) -> Tuple[Dict[str, List[Tuple[int, str]]], int, int]:
    """Return {file: [(line_number, added_text)]}, lines added, lines removed."""
    added: Dict[str, List[Tuple[int, str]]] = {}
    current: Optional[str] = None
    line_no = 0
    n_add = n_del = 0
    hunk = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            m = re.match(r"diff --git a/(.+?) b/(.+)$", raw)
            current = m.group(2) if m else None
            if current is not None:
                added.setdefault(current, [])
            continue
        if raw.startswith("+++ "):
            target = raw[4:]
            if target == "/dev/null":  # deleted file
                continue
            current = target[2:] if target.startswith("b/") else target
            added.setdefault(current, [])
            continue
        if raw.startswith("--- "):
            continue
        m = hunk.match(raw)
        if m:
            line_no = int(m.group(1))
            continue
        if current is None:
            continue
        if raw.startswith("+"):
            added[current].append((line_no, raw[1:]))
            line_no += 1
            n_add += 1
        elif raw.startswith("-"):
            n_del += 1
    return added, n_add, n_del


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def classify(path: str) -> List[str]:
    p = Path(path)
    ext = p.suffix.lower()
    areas = set()
    if ext in CODE_EXT:
        areas.add("code")
    if ext in UI_EXT or SWIFT_UI.search(p.name) or (ext in CODE_EXT and UI_PATH.search(path)):
        areas.add("ui")
    if ext in BACKEND_EXT or (ext in CODE_EXT and BACKEND_PATH.search(path)):
        areas.add("backend")
    if ext in WRITING_EXT and p.name.lower() not in {"requirements.txt"}:
        areas.add("writing")
    if ext in DATA_EXT and p.name not in DEPENDENCY_FILES and not p.name.endswith(("tsconfig.json",)) \
            and not path.startswith((".claude-plugin/", ".vscode/", ".github/")):
        areas.add("data")
    if p.name in DEPENDENCY_FILES or CONFIG_PATH.search(path):
        areas.add("code")
    return sorted(areas)


def mask(secret_line: str) -> str:
    """Hide the middle of anything that looks like a secret before printing it."""
    def _hide(m: re.Match) -> str:
        s = m.group(0)
        return s if len(s) <= 8 else s[:4] + "…" + s[-2:]
    return re.sub(r"[A-Za-z0-9_\-+/=]{12,}", _hide, secret_line.strip())[:120]


def scan_lines(added: Dict[str, List[Tuple[int, str]]]) -> List[Finding]:
    out: List[Finding] = []
    for file, lines in added.items():
        is_test = bool(TEST_PATH.search(file))
        is_doc = Path(file).suffix.lower() in WRITING_EXT
        for no, text in lines:
            for pat, label in SECRET_PATTERNS:
                if pat.search(text) and not re.search(r"(?i)example|placeholder|your[_-]?(key|token)|<.*>|\$\{|os\.environ|process\.env|getenv", text):
                    out.append(Finding("blocker", f"possible {label}", file, no, mask(text)))
                    break
            if is_doc:
                continue
            for pat, sev, msg in LINE_CHECKS:
                if msg == "debug output left in" and (is_test or file.endswith((".sh", ".md"))):
                    continue
                if msg.startswith("Swift") and not file.endswith(".swift"):
                    continue
                if pat.search(text):
                    out.append(Finding(sev, msg, file, no, text.strip()[:120]))
    return out


def file_size(root: Path, rel: str) -> int:
    try:
        return (root / rel).stat().st_size
    except OSError:
        return 0


def detect_commands(root: Path) -> Dict[str, str]:
    cmds: Dict[str, str] = {}
    pkg = root / "package.json"
    if pkg.exists():
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
        except (ValueError, OSError):
            scripts = {}
        runner = "pnpm" if (root / "pnpm-lock.yaml").exists() else \
                 "yarn" if (root / "yarn.lock").exists() else "npm run"
        for key, name in (("build", "build"), ("test", "test"), ("lint", "lint"),
                          ("typecheck", "typecheck"), ("type-check", "typecheck")):
            if key in scripts and name not in cmds:
                cmds[name] = f"{runner} {key}"
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or \
            (root / "setup.py").exists():
        has_tests = any(root.glob("test*")) or any(root.glob("**/test_*.py"))
        if has_tests:
            cmds.setdefault("test", "python -m pytest")
        pyproject = (root / "pyproject.toml")
        text = pyproject.read_text(encoding="utf-8", errors="replace") if pyproject.exists() else ""
        if "ruff" in text:
            cmds.setdefault("lint", "ruff check .")
        if "mypy" in text:
            cmds.setdefault("typecheck", "mypy .")
    if (root / "Package.swift").exists():
        cmds.setdefault("build", "swift build")
        cmds.setdefault("test", "swift test")
    xcode = sorted(root.glob("*.xcodeproj")) + sorted(root.glob("*.xcworkspace"))
    if xcode:
        cmds.setdefault("test", f"xcodebuild test -scheme <Scheme> -destination 'platform=iOS Simulator,name=iPhone 16'  # {xcode[0].name}")
    if (root / "go.mod").exists():
        cmds.setdefault("build", "go build ./...")
        cmds.setdefault("test", "go test ./...")
    if (root / "Cargo.toml").exists():
        cmds.setdefault("build", "cargo build")
        cmds.setdefault("test", "cargo test")
        cmds.setdefault("lint", "cargo clippy")
    makefile = root / "Makefile"
    if makefile.exists():
        targets = re.findall(r"^([A-Za-z][\w-]*):", makefile.read_text(encoding="utf-8", errors="replace"), re.M)
        for t in ("build", "test", "lint"):
            if t in targets:
                cmds.setdefault(t, f"make {t}")
    return cmds


def analyse(root: Path, base: str) -> Report:
    report = Report(base=base)
    diff = collect_diff(root, base)
    added, report.lines_added, report.lines_removed = parse_diff(diff)
    report.files_changed = sorted(added)

    areas = set()
    for f in report.files_changed:
        areas.update(classify(f))
    report.areas = sorted(areas)
    report.checklists = [CHECKLISTS[a] for a in ("code", "ui", "backend", "writing", "data") if a in areas]

    report.warnings = scan_lines(added)

    reasons: List[str] = []
    for f in report.files_changed:
        for pat, why in HIGH_RISK_PATH:
            if pat.search(f) and why not in reasons:
                reasons.append(why)
        if file_size(root, f) > BINARY_LIMIT:
            report.warnings.append(Finding("major", "large file added (over 1 MB)", f))

    if any(w.severity == "blocker" for w in report.warnings):
        reasons.append("possible secret in the changes")
    if any(w.message == "destructive SQL" or w.message.startswith("row level security")
           for w in report.warnings):
        reasons.append("destructive or security-sensitive database change")

    code_files = [f for f in report.files_changed if "code" in classify(f) and not TEST_PATH.search(f)
                  and Path(f).name not in DEPENDENCY_FILES]
    test_files = [f for f in report.files_changed if TEST_PATH.search(f)]
    deps = [f for f in report.files_changed if Path(f).name in DEPENDENCY_FILES]

    if code_files and not test_files:
        report.notes.append("Code changed but no test files changed. New behaviour or a bug fix usually needs a test.")
    if deps:
        report.notes.append("Dependencies changed (" + ", ".join(deps) + "). Verify each new package name and pin versions.")

    total = report.lines_added + report.lines_removed
    if reasons:
        report.risk = "high"
    elif total > 25 or len(code_files) > 1 or any(w.severity == "major" for w in report.warnings):
        report.risk = "standard"
        reasons.append(f"{len(report.files_changed)} files and {total} changed lines")
    else:
        report.risk = "low"
        reasons.append("small change with no sensitive paths")
    report.risk_reasons = reasons

    report.commands = detect_commands(root)
    if not report.commands and code_files:
        report.notes.append("No build or test command detected. Ask the user how the project is run and tested.")

    order = {"blocker": 0, "major": 1, "minor": 2}
    report.warnings.sort(key=lambda w: (order.get(w.severity, 3), w.file, w.line or 0))
    return report


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def render(report: Report) -> str:
    out: List[str] = []
    if not report.files_changed:
        return f"No changes found compared with {report.base}. Pass --base <ref> to compare with something else."
    out.append(f"Changes vs {report.base}: {len(report.files_changed)} files, "
               f"+{report.lines_added} / -{report.lines_removed} lines")
    out.append("")
    out.append(f"Suggested risk: {report.risk.upper()}")
    out.extend(f"  - {r}" for r in report.risk_reasons)
    out.append("")
    out.append("Checklists to load: " + (", ".join(report.checklists) or "none (core routine only)"))
    out.append("")
    if report.warnings:
        out.append(f"Warnings in added lines ({len(report.warnings)}):")
        for w in report.warnings:
            loc = f"{w.file}:{w.line}" if w.line else w.file
            out.append(f"  [{w.severity}] {loc}  {w.message}")
            if w.excerpt:
                out.append(f"      {w.excerpt}")
    else:
        out.append("Warnings in added lines: none found by pattern checks (this is not proof of correctness).")
    out.append("")
    if report.commands:
        out.append("Commands to run after the last edit:")
        out.extend(f"  {k:<9} {v}" for k, v in report.commands.items())
    else:
        out.append("Commands to run: none detected.")
    if report.notes:
        out.append("")
        out.append("Notes:")
        out.extend(f"  - {n}" for n in report.notes)
    out.append("")
    out.append("Files changed:")
    out.extend(f"  {f}" for f in report.files_changed)
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Gather review evidence for the current git changes.")
    parser.add_argument("--base", help="git ref to compare against (default: merge base with the main branch)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--path", default=".", help="path inside the repository (default: current directory)")
    args = parser.parse_args(argv)

    root = repo_root(Path(args.path).resolve())
    if root is None:
        print("Not inside a git repository. Review the files directly using the checklists.", file=sys.stderr)
        return 2
    base = args.base or default_base(root)
    code, _ = git(["rev-parse", "--verify", "--quiet", base], root)
    if code != 0 and base != "HEAD":
        print(f"Unknown git ref: {base}", file=sys.stderr)
        return 2

    report = analyse(root, base)
    if args.json:
        data = asdict(report)
        print(json.dumps(data, indent=2))
    else:
        print(render(report))
    return 1 if any(w.severity == "blocker" for w in report.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
