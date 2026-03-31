import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Lister de 10 siste batch-jobbene
print("🔍 Sjekker aktive batch-jobber...")
for job in client.batches.list(config={'page_size': 10}):
    print(f"ID: {job.name} | Status: {job.state} | Modell: {job.model}")