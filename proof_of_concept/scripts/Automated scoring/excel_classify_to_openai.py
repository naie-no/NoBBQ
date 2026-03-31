#!/usr/bin/env python3
"""
excel_batch_classify_to_openai_resume.py

- Reads column A from Excel
- Skips rows where column B already has a value (automatic resume)
- Sends remaining rows in batches (default 10 per call) to OpenAI Responses API
- Writes labels into column B
"""

import argparse
import re
import time
from typing import List, Dict, Tuple

import pandas as pd
from openai import OpenAI

client = OpenAI()

# ----- Configurable defaults -----
DEFAULT_MODEL = "gpt-4.1"    # reliable, more reasoning, ~$0.75 per 1200 rows
DEFAULT_BATCH = 10           # rows per API request
# ---------------------------------

LABEL_RE = re.compile(r"\bans\d+\b", flags=re.IGNORECASE)
LINE_RE = re.compile(r"^\s*ID=(\d+)\s+(\bans\d+\b)\s*$", flags=re.IGNORECASE)


def extract_labels(text: str) -> List[str]:
    """Find distinct ans0/ans1/etc. in the text."""
    labels = LABEL_RE.findall(text or "")
    seen, ordered = set(), []
    for lab in labels:
        lab = lab.lower()
        if lab not in seen:
            seen.add(lab)
            ordered.append(lab)
    return ordered or ["ans0", "ans1", "ans2"]


def build_batch_prompt(items: List[Tuple[int, str, List[str]]]) -> str:
    header = (
        "Du er en streng klassifikator.\n"
        "Oppgave: For hvert element skal du returnere KUN én etikett fra listen angitt.\n"
        "Output-format: ÉN linje per element, nøyaktig slik: 'ID=<id> <etikett>'\n"
        "Ingen ekstra tekst, ingen forklaring, ingen punktum.\n"
    )
    lines = ["\nELEMENTER:"]
    for ridx, text, labels in items:
        lines.append(f"ID={ridx} | Tillatte: {', '.join(labels)} | Tekst: {text}")
    footer = (
        "\nReturner nå kun resultatlinjene:\n"
        "Eksempel: ID=12 ans1"
    )
    return header + "\n".join(lines) + footer


def parse_batch_output(text: str) -> Dict[int, str]:
    results: Dict[int, str] = {}
    for line in (text or "").splitlines():
        m = LINE_RE.match(line)
        if m:
            ridx = int(m.group(1))
            label = m.group(2).lower()
            results[ridx] = label
    return results


def call_openai(prompt: str, model: str) -> str:
    resp = client.responses.create(
        model=model,
        input=prompt
    )
    out = getattr(resp, "output_text", None)
    if not out:
        pieces = []
        for item in getattr(resp, "output", []) or []:
            for c in getattr(item, "content", []) or []:
                if getattr(c, "type", "") in {"output_text", "text"} and getattr(c, "text", ""):
                    pieces.append(c.text)
        out = "".join(pieces).strip()
    return (out or "").strip()


def classify_batch(batch: List[Tuple[int, str, List[str]]], model: str) -> Dict[int, str]:
    prompt = build_batch_prompt(batch)
    out = call_openai(prompt, model)
    parsed = parse_batch_output(out)
    expected = {i[0] for i in batch}
    # if incomplete → fallback per-row
    if not expected.issubset(parsed.keys()):
        for ridx, text, labels in batch:
            if ridx not in parsed:
                single_prompt = (
                    "Du er en streng klassifikator.\n"
                    "Returner KUN én etikett, uten ekstra tekst.\n"
                    f"Tillatte: {', '.join(labels)}\n"
                    f"Tekst:\n{text}\n\n"
                    f"Returner kun én: {', '.join(labels)}"
                )
                try:
                    out2 = call_openai(single_prompt, model)
                    m = LABEL_RE.search(out2)
                    parsed[ridx] = m.group(0).lower() if m else out2.strip()
                except Exception as e:
                    parsed[ridx] = f"ERROR: {e}"
    return parsed


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i+size]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("excel_path", help="Path to the Excel file")
    parser.add_argument("--sheet", default=0, help="Sheet name or index")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH, help="Rows per API request")
    args = parser.parse_args()

    df = pd.read_excel(args.excel_path, sheet_name=args.sheet, engine="openpyxl")
    if df.shape[1] < 1:
        raise SystemExit("No column A found.")
    if df.shape[1] < 2:
        df.insert(1, "ModelSvar", "")

    # collect tasks: only rows with column A filled AND column B empty
    tasks: List[Tuple[int, str, List[str]]] = []
    for idx, val in df.iloc[:, 0].items():
        if pd.isna(val) or not str(val).strip():
            continue
        if not pd.isna(df.iat[idx, 1]) and str(df.iat[idx, 1]).strip():
            continue  # resume: skip already labeled
        text = str(val).strip()
        labels = extract_labels(text)
        tasks.append((idx, text, labels))

    # process in batches
    for batch in chunked(tasks, args.batch_size):
        results = classify_batch(batch, args.model)
        for ridx, label in results.items():
            df.iat[ridx, 1] = label
        time.sleep(0.3)  # be gentle on rate limits

    out_path = args.excel_path.replace(".xlsx", "_with_results.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, sheet_name=args.sheet if isinstance(args.sheet, str) else writer.book.sheetnames[0], index=False)

    print(f"✅ Done. Results written to {out_path}")
