import os
import sys
import ssl
import json
import requests
from pathlib import Path

# --- SSL FIX FOR JOBB-PC ---
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

def start_batch():
    if len(sys.argv) < 2:
        print("❌ FEIL: Oppgi filsti.")
        return

    input_file_path = Path(sys.argv[1]).resolve()
    api_key = os.environ.get("MISTRAL_API_KEY")

    if not api_key:
        print("❌ FEIL: MISTRAL_API_KEY mangler i terminalen.")
        print("Kjør: set MISTRAL_API_KEY=din_nøkkel")
        return

    # 1. LAST OPP FIL (Bruker requests direkte)
    print(f"📤 Laster opp {input_file_path.name}...")
    upload_url = "https://api.mistral.ai/v1/files"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        with open(input_file_path, "rb") as f:
            files = {
                "file": (input_file_path.name, f),
                "purpose": (None, "batch")
            }
            # verify=False pga bedriftens proxy
            response = requests.post(upload_url, headers=headers, files=files, verify=False)

        if response.status_code != 200:
            print(f"❌ Opplasting feilet: {response.text}")
            return

        file_id = response.json()["id"]
        print(f"✅ Fil lastet opp! ID: {file_id}")

        # 2. START BATCH-JOBB (Bruker requests direkte - dropper SDK)
        print(f"🚀 Starter batch-jobb hos Mistral...")
        batch_url = "https://api.mistral.ai/v1/batch/jobs"
        
        batch_data = {
            "input_files": [file_id],
            "model": "mistral-large-latest",
            "endpoint": "/v1/chat/completions"
        }
        
        batch_response = requests.post(batch_url, headers=headers, json=batch_data, verify=False)

        if batch_response.status_code != 200:
            print(f"❌ Kunne ikke starte jobb: {batch_response.text}")
            return

        job_info = batch_response.json()
        
        print("\n" + "="*60)
        print(f"🎉 ENDELIG! BATCH-JOBB OPPRETTET")
        print(f"Jobb-ID:  {job_info['id']}")
        print(f"Status:   {job_info['status']}")
        print("="*60)
        print("Lagre Jobb-ID for å hente resultater i morgen.")

    except Exception as e:
        print(f"❌ En uventet feil oppstod: {e}")

if __name__ == "__main__":
    start_batch()