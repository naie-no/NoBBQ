#!/usr/bin/env python3
"""
excel_prompts_to_answers.py

- Reads prompts from Column A in an Excel sheet
- Sends each prompt to OpenAI (gpt-4o by default)
- Writes the model's answer into Column B
- Skips rows where Column B already has an answer (resume)
- Saves results to a new file with "_with_answers.xlsx" suffix
- Prints progress while running
"""

import argparse
import time
import pandas as pd
from openai import OpenAI

# API key comes from environment variable OPENAI_API_KEY
client = OpenAI()

DEFAULT_MODEL = "gpt-4o"

def call_openai(prompt: str, model: str) -> str:
    """Send one prompt to OpenAI and return the answer text."""
    resp = client.responses.create(
        model=model,
        input=prompt
    )
    if getattr(resp, "output_text", None):
        return resp.output_text.strip()
    pieces = []
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            if getattr(c, "type", "") in {"output_text", "text"} and getattr(c, "text", ""):
                pieces.append(c.text)
    return "".join(pieces).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("excel_path", help="Path to the Excel file")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model to use (default: gpt-4o)")
    args = parser.parse_args()

    # Load Excel
    df = pd.read_excel(args.excel_path, sheet_name=args.sheet, engine="openpyxl")
    if df.shape[1] < 1:
        raise SystemExit("No column A found.")
    if df.shape[1] < 2:
        df.insert(1, "Answer", "")

    total = len(df)
    processed = 0

    for idx, val in df.iloc[:, 0].items():
        if pd.isna(val) or not str(val).strip():
            processed += 1
            continue
        if not pd.isna(df.iat[idx, 1]) and str(df.iat[idx, 1]).strip():
            processed += 1
            continue  # skip already filled (resume)

        prompt = str(val).strip()
        try:
            answer = call_openai(prompt, args.model)
            df.iat[idx, 1] = answer
        except Exception as e:
            df.iat[idx, 1] = f"ERROR: {e}"
            time.sleep(1)

        processed += 1
        print(f"Processed {processed}/{total} rows...")
        time.sleep(0.3)  # gentle pacing

    # Save new file
    out_path = args.excel_path.replace(".xlsx", "_with_answers.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(
            writer,
            sheet_name=args.sheet if isinstance(args.sheet, str) else writer.book.sheetnames[0],
            index=False,
        )

    print(f"✅ Done. Answers written to {out_path}")


if __name__ == "__main__":
    main()
