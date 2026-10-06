"""Check documentation links, repository references and phase/decision bookkeeping.

Run from any directory with Python 3.12+. Uses only the standard library and
never changes files or accesses the network. External links are syntax-checked
only; their availability is not claimed.
"""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\n]+)\)")
REFERENCE = re.compile(r"`((?:src|tests|scripts|docs|data|notebooks)/[^`\n]+)`")


def check() -> int:
    """Return nonzero on a broken local reference, orphan or incomplete ADR."""
    documents = set((ROOT / "docs").rglob("*.md")) | set(ROOT.glob("*.md"))
    edges: dict[Path, set[Path]] = {}
    failures: list[str] = []
    reference_count = 0
    agent_file = ROOT / "AGENTS.md"
    phase_match = (
        re.search(
            r"^- Completed implementation phases: \*\*([0-9, ]+)\*\*",
            agent_file.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if agent_file.exists()
        else None
    )
    completed = (
        tuple(int(item.strip()) for item in phase_match.group(1).split(",")) if phase_match else ()
    )
    if not completed or max(completed) > 12 or completed != tuple(range(1, max(completed) + 1)):
        failures.append("AGENTS.md must list contiguous completed implementation phases 1–12")
    for document in sorted(documents):
        body = document.read_text(encoding="utf-8")
        edges[document] = set()
        for match in LINK.finditer(body):
            target = match.group(1).strip().strip("<>")
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            local = unquote(target.split("#", 1)[0])
            destination = (document.parent / local).resolve()
            if not destination.is_relative_to(ROOT) or not destination.exists():
                failures.append(f"{document.relative_to(ROOT)}: broken link {target}")
            elif destination.suffix == ".md":
                edges[document].add(destination)
        for match in REFERENCE.finditer(body):
            target = match.group(1)
            if any(token in target for token in ("*", "...", "<", " ")):
                continue  # Explicit patterns, not concrete file references.
            reference_count += 1
            if not (ROOT / target).exists():
                failures.append(f"{document.relative_to(ROOT)}: absent code/path {target}")
    reached: set[Path] = set()
    pending = [ROOT / "docs/INDEX.md"]
    while pending:
        current = pending.pop()
        if current not in reached:
            reached.add(current)
            pending.extend(edges.get(current, set()))
    for orphan in sorted(documents - reached):
        failures.append(f"{orphan.relative_to(ROOT)}: unreachable from docs/INDEX.md")
    decisions = sorted((ROOT / "docs/decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))
    identifiers = [document.name[:4] for document in decisions]
    if len(set(identifiers)) != len(identifiers):
        failures.append("Canonical decision IDs are duplicated")
    register = ROOT / "docs/decisions/README.md"
    register_body = register.read_text(encoding="utf-8") if register.exists() else ""
    count_match = re.search(r"There are \*\*(\d+) canonical ADRs\*\*", register_body)
    phase_count = re.search(r"\*\*(\d+) of 12 implementation phases", register_body)
    if not count_match or int(count_match.group(1)) != len(decisions):
        failures.append("Decision register ADR count does not match its files")
    if not phase_count or int(phase_count.group(1)) != len(completed):
        failures.append("Decision register completed-phase count does not match AGENTS.md")
    for phase in completed:
        if f"| Phase {phase} |" not in register_body:
            failures.append(f"Decision register is missing the phase {phase} ledger entry")
    for decision in decisions:
        body = decision.read_text(encoding="utf-8")
        for required in (
            "**Status:**",
            "## Context",
            "## Decision",
            "## Risks",
            "## Related code",
            "## Phase history",
        ):
            if required not in body:
                failures.append(f"{decision.relative_to(ROOT)}: missing {required}")
        for phase in completed:
            if f"| {phase} |" not in body:
                failures.append(f"{decision.relative_to(ROOT)}: missing phase {phase} review")
    if failures:
        print("\n".join(failures))
        return 1
    print(
        f"Documentation checks passed: {len(documents)} Markdown files, "
        f"{len(decisions)} canonical ADRs, {reference_count} concrete path references; "
        "all local links and index reachability valid. External URLs were not fetched."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
