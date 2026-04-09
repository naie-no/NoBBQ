import os
from google import genai

def clear_all_batches():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    print("🔍 Henter liste over alle batch-jobber...")
    
    # Vi henter de siste 50 jobbene for å være sikre på å ta alt
    jobs = list(client.batches.list(config={'page_size': 50}))
    
    if not jobs:
        print("Minst ingen jobber å slette.")
        return

    print(f"Fant {len(jobs)} jobber. Starter sletting...")

    for job in jobs:
        # Vi sletter jobben uavhengig av status (PENDING, RUNNING, FAILED)
        # Sletting av en aktiv jobb vil avbryte den umiddelbart.
        try:
            print(f"🗑️ Sletter {job.name} (Status: {job.state})...")
            client.batches.delete(name=job.name)
        except Exception as e:
            print(f"❌ Kunne ikke slette {job.name}: {e}")

    print("\n✅ Alle batch-jobber er fjernet fra køen.")

if __name__ == "__main__":
    clear_all_batches()