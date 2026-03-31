import os
import ssl
import json
import requests
from pathlib import Path

# --- SSL-FIX FOR JOBB-PC ---
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

def start_batch_evaluation():
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("❌ FEIL: MISTRAL_API_KEY mangler.")
        return

    headers = {"Authorization": f"Bearer {api_key}"}

    # Filene som skal sendes
    files_to_send = [
        "Age_nb_evalutation_prompts_max3.jsonl",
        "Age_nb_evalutation_prompts_vanilla.jsonl"
    ]

    for file_name in files_to_send:
        file_path = Path(file_name)
        if not file_path.exists():
            print(f"⚠️ Fant ikke: {file_name}")
            continue

        try:
            # 1. LAST OPP FIL
            print(f"📤 Laster opp {file_name}...")
            upload_url = "https://api.mistral.ai/v1/files"
            with open(file_path, "rb") as f:
                response = requests.post(
                    upload_url, 
                    headers=headers, 
                    files={"file": (file_path.name, f), "purpose": (None, "batch")}, 
                    verify=False
                )
            
            if response.status_code != 200:
                print(f"❌ Opplasting feilet for {file_name}: {response.text}")
                continue

            file_id = response.json()["id"]

            # 2. START BATCH-JOBB
            print(f"🚀 Starter batch for {file_name}...")
            batch_url = "https://api.mistral.ai/v1/batch/jobs"
            batch_data = {
                "input_files": [file_id],
                "model": "mistral-small-latest",
                "endpoint": "/v1/chat/completions"
            }
            
            batch_response = requests.post(batch_url, headers=headers, json=batch_data, verify=False)

            if batch_response.status_code == 200:
                job_id = batch_response.json()["id"]
                print(f"✅ Suksess! Jobb-ID: {job_id}")
            else:
                print(f"❌ Kunne ikke starte jobb: {batch_response.text}")

            print("-" * 30)

        except Exception as e:
            print(f"❌ Feil med {file_name}: {e}")

if __name__ == "__main__":
    start_batch_evaluation()