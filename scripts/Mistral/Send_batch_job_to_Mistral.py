import os
import sys
import ssl
from pathlib import Path

# --- BEDRIFTS-PC FIX START ---
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass
# --- BEDRIFTS-PC FIX SLUTT ---

try:
    from mistralai import Mistral
except ImportError:
    print("❌ FEIL: 'mistralai' er ikke installert.")
    sys.exit(1)

def start_batch():
    if len(sys.argv) < 2:
        print("❌ FEIL: Oppgi filsti.")
        return

    input_file_path = Path(sys.argv[1]).resolve()
    api_key = os.environ.get("MISTRAL_API_KEY")

    if not api_key:
        print("❌ FEIL: MISTRAL_API_KEY mangler.")
        return

    client = Mistral(api_key=api_key)

    try:
        print(f"📤 Laster opp til Mistral (via proxy-fix)...")
        with open(input_file_path, "rb") as f:
            uploaded_file = client.files.upload(
                file={"file_name": input_file_path.name, "content": f}
            )

        batch_job = client.batch.jobs.create(
            input_files=[uploaded_file.id],
            model="mistral-large-latest",
            endpoint="/v1/chat/completions"
        )

        print(f"\n✅ SUKSESS! Jobb-ID: {batch_job.id}")

    except Exception as e:
        print(f"❌ En feil oppstod: {e}")

if __name__ == "__main__":
    start_batch()