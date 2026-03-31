#!/usr/bin/env python3
"""
excel_prompts_to_answers_gemini25.py

- Reads prompts from Column A in an Excel sheet
- Sends each prompt to Google Gemini 2.5 Flash (default) as a fresh, stateless call
- Writes the model's answer into Column B
- Skips rows where Column B already has an answer (resume)
- Prints progress while running
- Handles rate limits with backoff + periodic pauses
- Saves to "<input>_with_answers.xlsx"

Prereqs:
  pip install google-generativeai pandas openpyxl
Env:
  export GOOGLE_API_KEY="your_key"    # or set via PowerShell: $env:GOOGLE_API_KEY="..."
"""

import argparse
import os
import time
import random
import pandas as pd
import google.generativeai as genai

DEFAULT_MODEL = "gemini-2.5-flash"   # switch with --model if you want "gemini-2.5-pro", etc.

def init_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Missing GOOGLE_API_KEY environment variable.")
    genai.configure(api_key=api_key)

def call_gemini_safe(prompt: str, model_name: str, retries: int = 6) -> str:
    """Single prompt -> answer with exponential backoff on rate limits."""
    for attempt in range(retries):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            # Prefer resp.text when present
            if getattr(resp, "text", None):
                return resp.text.strip()
            # Fallback: concatenate any text parts from candidates
            parts = []
            for c in getattr(resp, "candidates", []) or []:
                for p in getattr(c, "content", {}).get("parts", []) or []:
                    t = getattr(p, "text", "")
                    if t:
                        parts.append(t)
            return "".join(parts).strip() or "(empty response)"
        except Exception as e:
            msg = str(e).lower()
            # Handle rate limit / quota / busy
            if "429" in msg or "rate" in msg or "quota" in msg or "resource exhausted" in msg:
                # Exponential backoff with jitter
                wait = (2 ** attempt) + random.uniform(0.0, 1.0)
                # Cap the backoff to something reasonable
                wait = min(wait, 30.0)
                print(f"⚠️  Rate limited (attempt {attempt+1}/{retries}). Sleeping {wait:.1f}s...")
                time.sleep(wait)
                continue
            # Safety blocks or other expected API exceptions—brief wait and continue once
            if "safety" in msg or "blocked" in msg:
                print("⚠️  Prompt blocked by safety filters. Returning '(blocked)'.")
                return "(blocked)"
            # Anything else: re-raise
            raise
    return "ERROR: too many retries due to rate limits"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("excel_path", help="Path to the Excel file")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default: {DEFAULT_MODEL})")
    parser.add_argument("--sleep-each", type=float, default=1.0, help="Seconds to sleep after each row (default: 1.0)")
    parser.add_argument("--pause-every", type=int, default=10, help="Pause after every N processed rows (default: 10)")
    parser.add_argument("--pause-seconds", type=float, default=30.0, help="How long to pause (default: 30s)")
    args = parser.parse_args()

    init_client()

    # Load Excel
    df = pd.read_excel(args.excel_path, sheet_name=args.sheet, engine="openpyxl")
    if df.shape[1] < 1:
        raise SystemExit("No column A found.")
    if df.shape[1] < 2:
        df.insert(1, "Answer", "")

    total = len(df)
    processed = 0
    started = time.time()

    try:
        for idx, val in df.iloc[:, 0].items():
            # Always move the counter so total reflects full sheet progress
            processed += 1

            # Skip empty prompts
            if pd.isna(val) or not str(val).strip():
                print(f"Processed {processed}/{total} (skipped empty A)")
                continue

            # Resume: skip if B already filled
            if not pd.isna(df.iat[idx, 1]) and str(df.iat[idx, 1]).strip():
                print(f"Processed {processed}/{total} (resume skip)")
                continue

            prompt = str(val).strip()
            try:
                answer = call_gemini_safe(prompt, args.model)
                df.iat[idx, 1] = answer if answer else "(empty response)"
            except KeyboardInterrupt:
                print("\n⏹️  Interrupted. Saving partial results...")
                break
            except Exception as e:
                df.iat[idx, 1] = f"ERROR: {e}"

            # Progress line
            elapsed = time.time() - started
            print(f"Processed {processed}/{total} rows...  (elapsed {elapsed:.1f}s)")

            # Light pacing each call
            time.sleep(args.sleep_each if args.sleep_each >= 0 else 0)

            # Bigger pause every N calls (helps avoid 429s)
            if args.pause_every > 0 and processed % args.pause_every == 0:
                print(f"⏸️  Pausing {args.pause_seconds:.0f}s to stay under rate limits...")
                time.sleep(args.pause_seconds)


    finally:
        # Save to a new file
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
