#!/usr/bin/env python3
import argparse
import re
import time
import os
import sys
from typing import List, Dict, Tuple
import pandas as pd
from openai import OpenAI

# Sørg for at OPENAI_API_KEY er satt i terminalen før kjøring
client = OpenAI()

# ----- Innstillinger -----
DEFAULT_MODEL = "gpt-4o-mini"  # Rask, billig og god på klassifisering
DEFAULT_BATCH = 25             # Antall rader per API-kall (effektivt for 3000+ rader)
# -------------------------

LABEL_RE = re.compile(r"\b(ans\d+|flagg)\b", flags=re.IGNORECASE)
LINE_RE = re.compile(r"ID=(\d+)\s+(ans\d+|flagg)", flags=re.IGNORECASE)

def extract_labels(text: str) -> List[str]:
    """Henter ut svaralternativer (ans0, ans1...) fra teksten."""
    labels = LABEL_RE.findall(text or "")
    seen, ordered = set(), []
    for lab in labels:
        lab = lab.lower()
        if lab not in seen:
            seen.add(lab)
            ordered.append(lab)
    return ordered if ordered else ["ans0", "ans1", "ans2"]

def build_batch_prompt(items: List[Tuple[int, str, List[str]]]) -> str:
    header = (
        "Du er en streng klassifikator.\n"
        "Oppgave: For hvert element skal du returnere KUN én etikett fra listen.\n"
        "Output-format: ÉN linje per element, nøyaktig slik: 'ID=<id> <etikett>'\n"
        "Ingen forklaring, ingen ekstra tekst.\n\n"
        "ELEMENTER:\n"
    )
    lines = []
    for ridx, text, labels in items:
        # Korter ned teksten litt for å spare tokens og unngå støy
        clean_text = text.replace('\n', ' ')[:700]
        lines.append(f"ID={ridx} | Valg: {', '.join(labels)} | Tekst: {clean_text}")
    
    footer = "\n\nReturner nå kun resultatlinjene (f.eks: ID=12 ans1):"
    return header + "\n".join(lines) + footer

def parse_batch_output(text: str) -> Dict[int, str]:
    results: Dict[int, str] = {}
    for line in (text or "").splitlines():
        m = LINE_RE.search(line)
        if m:
            ridx = int(m.group(1))
            label = m.group(2).lower()
            results[ridx] = label
    return results

def call_openai(prompt: str, model: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Du returnerer kun ID og etikett."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"\n  ❌ API-feil: {e}")
        return ""

def classify_batch(batch: List[Tuple[int, str, List[str]]], model: str) -> Dict[int, str]:
    prompt = build_batch_prompt(batch)
    out = call_openai(prompt, model)
    parsed = parse_batch_output(out)
    
    # Sjekk om alle rader i batchen ble besvart
    for ridx, text, labels in batch:
        if ridx not in parsed:
            print(f"  ⚠️  Mangler ID={ridx}, prøver enkeltkall...")
            single_p = f"Klassifiser som {', '.join(labels)} eller FLAGG.\nTekst: {text}"
            res = call_openai(single_p, model)
            m = LABEL_RE.search(res)
            parsed[ridx] = m.group(0).lower() if m else "error"
            
    return parsed

def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i+size]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("excel_path", help="Sti til Excel-filen")
    parser.add_argument("--sheet", default=0, help="Ark-navn eller index")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI modell")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH, help="Rader per kall")
    args = parser.parse_args()

    # 1. Last inn data
    if not os.path.exists(args.excel_path):
        print(f"❌ Fant ikke filen: {args.excel_path}")
        sys.exit(1)

    print(f"📖 Leser {args.excel_path}...")
    df = pd.read_excel(args.excel_path, sheet_name=args.sheet, engine="openpyxl")
    
    if df.shape[1] < 2:
        df.insert(1, "ModelSvar", "")

    # 2. Finn rader som mangler svar (Resume-logikk)
    tasks = []
    for idx, row in df.iterrows():
        text_a = row.iloc[0]
        svar_b = row.iloc[1]
        
        if pd.isna(text_a) or not str(text_a).strip():
            continue
        if not pd.isna(svar_b) and str(svar_b).strip():
            continue # Allerede besvart
            
        text = str(text_a).strip()
        labels = extract_labels(text)
        tasks.append((idx, text, labels))

    total_tasks = len(tasks)
    if total_tasks == 0:
        print("✅ Alle rader er allerede ferdig utfylt.")
        sys.exit(0)

    print(f"🚀 Starter prosessering av {total_tasks} rader på {args.model}...")
    print(f"📦 Batch-størrelse: {args.batch_size} rader per forespørsel.\n")

    # 3. Batch-prosessering med feedback
    processed = 0
    start_time = time.time()

    for batch in chunked(tasks, args.batch_size):
        results = classify_batch(batch, args.model)
        
        for ridx, label in results.items():
            df.iat[ridx, 1] = label
        
        processed += len(batch)
        
        # Beregn fremdrift og tid
        elapsed = time.time() - start_time
        avg_speed = processed / elapsed
        remaining = (total_tasks - processed) / avg_speed if avg_speed > 0 else 0
        
        print(f"📈 [{processed:4d}/{total_tasks:4d}] Ferdig | "
              f"Fremdrift: {int((processed/total_tasks)*100):>3}% | "
              f"Gjenstår ca: {int(remaining/60)} min {int(remaining%60)} sek")
        
        time.sleep(0.1) # Kort pause for å være snill mot APIet

    # 4. Lagre til ny fil
    out_path = args.excel_path.replace(".xlsx", "_with_results.xlsx")
    print(f"\n💾 Lagrer resultater til: {out_path}...")
    
    try:
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            s_name = args.sheet if isinstance(args.sheet, str) else "Klassifisering"
            df.to_excel(writer, sheet_name=s_name, index=False)
        print("🎉 Suksess! Alt er lagret.")
    except Exception as e:
        print(f"❌ Kunne ikke lagre: {e}")