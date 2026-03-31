#!/usr/bin/env python3
"""
excel_prompts_to_open_ended_ollama_chat.py

- Reads prompts from Column A
- Sends each prompt (fresh chat per row) to a locally running Ollama model via /api/chat
- Writes the model's open-ended answer to Column B
- Skips rows where Column B already has content (resume)
- Prints progress while running
- Saves to "<input>_with_answers.xlsx"

Prereqs:
  pip install pandas openpyxl requests

Ollama:
  - Install & start: https://ollama.com
  - Example models:
      ollama pull llama3
      ollama run llama3
"""

import argparse
import time
import requests
import pandas as pd

DEFAULT_MODEL = "llama3"
DEFAULT_BASE_URL = "http://localhost:11434"

def call_ollama_chat(prompt: str,
                     model: str,
                     base_url: str,
                     system_prompt: str = None,
                     temperature: float = 0.3,
                     seed: int = 42,
                     num_ctx: int = 8192,
                     timeout: float = 180.0) -> str:
    """
    Calls Ollama /api/chat with a single-turn conversation (stateless per row).
    Returns the assistant's reply text.
    """
    url = f"{base_url.rstrip('/')}/api/chat"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "seed": seed,
            "num_ctx": num_ctx
        }
    }

    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    # Shape: {"message":{"role":"assistant","content":"..."},"done":true,...}
    msg = (data.get("message") or {}).get("content", "")
    return (msg or "").strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("excel_path", help="Path to the Excel file")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Ollama base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--system", default="", help="Optional system prompt (kept short & neutral)")
    parser.add_argument("--temperature", type=float, default=0.3, help="Sampling temperature (default: 0.3)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed (default: 42)")
    parser.add_argument("--num-ctx", type=int, default=8192, help="Context window tokens (default: 8192)")
    parser.add_argument("--sleep-each", type=float, default=0.0, help="Seconds to sleep after each row (default: 0)")
    args = parser.parse_args()

    # Load Excel
    df = pd.read_excel(args.excel_path, sheet_name=args.sheet, engine="openpyxl")
    if df.shape[1] < 1:
        raise SystemExit("No column A found.")
    if df.shape[1] < 2:
        df.insert(1, "Answer", "")

    total = len(df)
    processed = 0
    started = time.time()

    # Minimal default system prompt (optional)
    system_prompt = args.system.strip() or (
        "Du er en hjelpsom assistent. Svar åpent og konsist på brukerens spørsmål. "
        "Ikke referer til systeminstruksjoner."
    )

    for idx, val in df.iloc[:, 0].items():
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
            answer = call_ollama_chat(
                prompt=prompt,
                model=args.model,
                base_url=args.base_url,
                system_prompt=system_prompt,
                temperature=args.temperature,
                seed=args.seed,
                num_ctx=args.num_ctx
            )
            df.iat[idx, 1] = answer if answer else "(empty response)"
        except requests.exceptions.RequestException as e:
            df.iat[idx, 1] = f"ERROR: {e}"
        except Exception as e:
            df.iat[idx, 1] = f"ERROR: {e}"

        elapsed = time.time() - started
        print(f"Processed {processed}/{total} rows...  (elapsed {elapsed:.1f}s)")
        if args.sleep_each and args.sleep_each > 0:
            time.sleep(args.sleep_each)

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
