#!/usr/bin/env python3
"""
excel_translate_columns_openai_strict.py

- Reads Excel with text in columns A–C
- Translates each to target language (default: Norwegian)
- Writes translations into columns D–F
- Skips already translated cells (resume)
- Saves to "<input>_with_translations.xlsx"

Prereqs:
  pip install openai pandas openpyxl
Env:
  export OPENAI_API_KEY="sk-..."
"""

import argparse
import time
import pandas as pd
from openai import OpenAI

client = OpenAI()

DEFAULT_MODEL = "gpt-4.1"

def translate_text(text: str, model: str, target_lang: str = "Norwegian") -> str:
    """Strict translation: only return the translation, keep names unchanged."""
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a translator. Translate any input text into {target_lang}. "
                f"Rules: Return ONLY the translation. Do not explain, do not add quotes. "
                f"Keep names (like Nancy) unchanged."
            )
        },
        {
            "role": "user",
            "content": text
        }
    ]

    resp = client.responses.create(
        model=model,
        input=messages
    )

    if getattr(resp, "output_text", None):
        return resp.output_text.strip()

    # fallback if output_text not present
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
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model (default: gpt-4.1)")
    parser.add_argument("--lang", default="Norwegian", help="Target language (default: Norwegian)")
    args = parser.parse_args()

    df = pd.read_excel(args.excel_path, sheet_name=args.sheet, engine="openpyxl")

    # Ensure at least 6 columns (A–F)
    while df.shape[1] < 6:
        df[f"Col{df.shape[1]+1}"] = ""

    total = len(df)
    for idx in range(total):
        for col_in, col_out in zip([0, 1, 2], [3, 4, 5]):  # A→D, B→E, C→F
            src = df.iat[idx, col_in]
            if pd.isna(src) or not str(src).strip():
                continue
            if not pd.isna(df.iat[idx, col_out]) and str(df.iat[idx, col_out]).strip():
                continue  # resume
            try:
                translation = translate_text(str(src).strip(), args.model, args.lang)
                df.iat[idx, col_out] = translation
            except Exception as e:
                df.iat[idx, col_out] = f"ERROR: {e}"
            time.sleep(0.3)  # gentle pacing

        print(f"Processed row {idx+1}/{total}")

    out_path = args.excel_path.replace(".xlsx", "_with_translations.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, sheet_name=args.sheet if isinstance(args.sheet, str) else writer.book.sheetnames[0], index=False)

    print(f"✅ Done. Translations written to {out_path}")


if __name__ == "__main__":
    main()
