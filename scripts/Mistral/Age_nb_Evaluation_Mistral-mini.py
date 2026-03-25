import os
from mistralai import Mistral

def start_batch_evaluation():
    # 1. Sett opp klienten med API-nøkkel fra miljøvariabler
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("Feil: Fant ikke MISTRAL_API_KEY i environment variables.")
        return

    client = Mistral(api_key=api_key)

    # 2. Definer filene som skal sendes
    files_to_send = [
        "Age_nb_evalutation_prompts_max3.jsonl",
        "Age_nb_evalutation_prompts_vanilla.jsonl"
    ]

    print(f"--- Starter Mistral Batch Prosessering ---")

    for file_path in files_to_send:
        if not os.path.exists(file_path):
            print(f"Skipper {file_path} - filen ble ikke funnet i mappen.")
            continue

        try:
            # Last opp filen til Mistral
            print(f"Laster opp: {file_path}...")
            
            # OPPDATERT: Mistral SDK v1+ krever dette formatet:
            with open(file_path, "rb") as f:
                uploaded_file = client.files.upload(
                    file={
                        "file_name": file_path,
                        "content": f.read(),
                    }
                )

            # Opprett batch-jobben
            print(f"Oppretter batch-jobb for {file_path}...")
            batch_job = client.batch.jobs.create(
                input_files=[uploaded_file.id],
                model="mistral-small-latest",
                endpoint="/v1/chat/completions",
                metadata={"source": file_path}
            )

            print(f"Suksess!")
            print(f"Jobb-ID: {batch_job.id}")
            print(f"Status: {batch_job.status}")
            print("-" * 40)

        except Exception as e:
            print(f"Det oppstod en feil med {file_path}: {e}")

if __name__ == "__main__":
    start_batch_evaluation()