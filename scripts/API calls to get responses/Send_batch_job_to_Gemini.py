import os
import sys
from pathlib import Path
from google import genai
from google.genai import types

def start_gemini_batch():
    # 1. Sjekk argumenter fra CMD
    if len(sys.argv) < 2:
        print("❌ FEIL: Oppgi filsti.")
        print(f"Bruk: python {sys.argv[0]} <din_gemini_fil>.jsonl")
        return

    file_path_str = sys.argv[1]
    file_path = Path(file_path_str)

    if not file_path.exists():
        print(f"❌ Fant ikke fila: {file_path}")
        return

    # 2. API-nøkkel
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ FEIL: Mangler GEMINI_API_KEY i environment variables.")
        return

    client = genai.Client(api_key=api_key)

    # 3. Last opp filen
    print(f"📤 Laster opp {file_path.name} til Google Cloud...")
    
    uploaded_file = client.files.upload(
        file=str(file_path),
        config=types.UploadFileConfig(
            display_name=file_path.stem,
            mime_type='text/plain'  # <--- LEGG TIL DENNE LINJEN
        )
    )

    # 4. Opprett batch-jobben
    # Bruker gemini-2.5-flash eller gemini-1.5-flash (3.0 er ikke et API-id ennå)
    model_id = "gemini-2.5-flash" 
    print(f"🚀 Starter batch-jobb på {model_id}...")
    
    batch_job = client.batches.create(
        model=model_id,
        src=uploaded_file.name,
        config=types.CreateBatchJobConfig(
            display_name=f"Evaluation_{file_path.stem}"
        )
    )

    print("\n" + "="*50)
    print(f"✅ BATCH OPPRETTET!")
    print(f"Fil:        {file_path.name}")
    print(f"Jobb-navn:  {batch_job.name}")
    print("="*50)
    print("Du kan se status i Google AI Studio (Batch Jobs).")

if __name__ == "__main__":
    start_gemini_batch()