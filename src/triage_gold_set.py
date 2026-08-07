"""
triage_gold_set.py

For each paper in the gold set, fetches full text (via ar5iv's HTML
rendering of the arXiv source) and searches for phrasings related to each
checklist element. Outputs short excerpts with surrounding context so a
human can judge disclosed / absent / ambiguous without reading the whole
paper.

This does NOT label anything automatically. It only surfaces where to
look. The disclosed/absent/ambiguous/not_applicable call is still made
by hand, in data/gold_set/gold_set_sample.csv -- this script's output is
a reading aid, not a substitute for that judgment.

Note: a paper with zero keyword matches across all five elements is not
automatically "absent" on all five -- check first whether the paper is
an empirical backtest at all. Governance frameworks, discretionary case
studies, and purely theoretical papers can legitimately have nothing to
disclose, in which case the correct label is not_applicable, not absent.
See notes/ for the decision record on this distinction.

If ar5iv has no rendering for a paper (happens for some, especially very
recent submissions), that paper is flagged as "no full text available"
and falls back to needing a manual PDF read -- logged, not silently
skipped.

Usage:
    python src/triage_gold_set.py
"""

import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

GOLD_PATH = Path("data/gold_set/gold_set_sample.csv")
OUT_DIR = Path("data/gold_set/excerpts")

# Checklist element -> regex patterns (case-insensitive) to search for.
# These are intentionally broad; the point is recall of candidate sentences,
# not precision -- the human reader filters false positives.
CHECKLIST_PATTERNS = {
    "walk_forward_validation": [
        r"walk[\s-]?forward",
        r"rolling[\s-]?window\s+(validation|evaluation|test)",
        r"expanding[\s-]?window",
    ],
    "purged_embargoed_cv": [
        r"purged\s+cross[\s-]?validation",
        r"embargo(ed)?",
        r"purg(e|ed|ing)\s+.{0,20}(cross[\s-]?validation|fold)",
    ],
    "out_of_sample_cost_modeling": [
        r"transaction\s+cost",
        r"out[\s-]?of[\s-]?sample\s+.{0,20}cost",
        r"slippage",
        r"bid[\s-]?ask\s+spread",
        r"market\s+impact",
    ],
    "multiple_testing_correction": [
        r"multiple[\s-]?(testing|comparisons?)",
        r"bonferroni",
        r"false\s+discovery\s+rate",
        r"family[\s-]?wise\s+error",
        r"data[\s-]?snoop(ing)?",
    ],
    "multi_window_validation": [
        r"multiple\s+(time\s+)?(periods?|windows?|regimes?)",
        r"out[\s-]?of[\s-]?sample\s+period",
        r"second\s+(window|period|dataset)",
        r"robustness\s+.{0,20}(period|window|sample)",
    ],
}

AR5IV_URL = "https://ar5iv.labs.arxiv.org/html/{arxiv_id}"


def fetch_fulltext(arxiv_id: str) -> str | None:
    """Fetch ar5iv HTML rendering and strip to plain text. Returns None
    if unavailable."""
    url = AR5IV_URL.format(arxiv_id=arxiv_id)
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "systematic-uncertainty-research/0.1"})
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    # Drop references/bibliography to reduce noise
    for tag in soup.find_all(["bibliography", "table"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_excerpts(text: str, patterns: list[str], context_chars: int = 200) -> list[str]:
    """Return short excerpts around each pattern match, deduplicated."""
    excerpts = []
    seen_spans = []
    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            start = max(0, m.start() - context_chars)
            end = min(len(text), m.end() + context_chars)
            # skip near-duplicate spans (overlapping matches)
            if any(abs(start - s) < context_chars for s in seen_spans):
                continue
            seen_spans.append(start)
            excerpt = text[start:end].strip()
            excerpts.append(f"...{excerpt}...")
    return excerpts


def build_excerpt_file(arxiv_id: str, title: str, text: str | None) -> str:
    lines = [f"# {arxiv_id} — {title}", ""]

    if text is None:
        lines.append("**No full text available via ar5iv. Read the PDF manually.**")
        return "\n".join(lines)

    any_hits = False
    for element, patterns in CHECKLIST_PATTERNS.items():
        excerpts = find_excerpts(text, patterns)
        lines.append(f"## {element}")
        if excerpts:
            any_hits = True
            for e in excerpts[:5]:  # cap to avoid dumping the whole paper
                lines.append(f"- {e}")
        else:
            lines.append("- (no keyword matches found)")
        lines.append("")

    if not any_hits:
        lines.append("**No checklist terms matched anywhere. Worth a manual skim to confirm absence.**")

    return "\n".join(lines)


def main():
    if not GOLD_PATH.exists():
        raise FileNotFoundError(f"{GOLD_PATH} not found. Run pull_arxiv.py first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(GOLD_PATH)
    no_fulltext = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Triaging"):
        arxiv_id = row["arxiv_id"]
        title = row["title"]

        text = fetch_fulltext(arxiv_id)
        if text is None:
            no_fulltext.append(arxiv_id)

        content = build_excerpt_file(arxiv_id, title, text)
        out_path = OUT_DIR / f"{arxiv_id.replace('/', '_')}.md"
        out_path.write_text(content)

        time.sleep(1)  # be polite to ar5iv

    print(f"\nWrote excerpt files to {OUT_DIR}/")
    if no_fulltext:
        print(f"\n{len(no_fulltext)} papers had no ar5iv rendering, need manual PDF read:")
        for aid in no_fulltext:
            print(f"  - {aid}")


if __name__ == "__main__":
    main()