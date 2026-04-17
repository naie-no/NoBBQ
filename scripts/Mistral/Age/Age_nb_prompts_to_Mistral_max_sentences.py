import json
import os

def create_mistral_batch_with_restrictions(input_filename, output_filename):
    # Den spesifikke instruksen vi legger til for å begrense lengden
    restriction_suffix = " Svar kortfattet på norsk med maksimalt 3 setninger."
    
    # Vi sjekker om input-filen faktisk eksisterer før vi starter
    if not os.path.exists(input_filename):
        print(f"❌ Fant ikke input-filen: {input_filename}")
        return

    with open(input_filename, 'r', encoding='utf-8') as infile, \
         open(output_filename, 'w', encoding='utf-8') as outfile:
        
        count = 0
        for line in infile:
            if not line.strip(): continue
            data = json.loads(line)
            
            example_id = str(data.get('example_id'))
            # Henter den originale prompten (context + question)
            original_prompt = data.get('final_prompt', '')
            
            # Legger til restriksjonen i slutten av brukerens melding
            modified_prompt = original_prompt.strip() + restriction_suffix
            
            batch_request = {
                "custom_id": example_id,
                "body": {
                    "model": "mistral-large-latest",
                    "messages": [
                        # Vi holder det i 'user' rollen som planlagt
                        {"role": "user", "content": modified_prompt}
                    ],
                    "temperature": 0
                    # Vi utelater fortsatt max_tokens for å la modellen 
                    # fullføre de 3 setningene naturlig
                }
            }
            
            outfile.write(json.dumps(batch_request, ensure_ascii=False) + "\n")
            count += 1

    print(f"✅ Ferdig! Prosesserte {count} rader.")
    print(f"📂 Output lagret til: {output_filename}")

# Kjøres fra ROOT
input_file = r"data_nb\Mistral\Age\Age_nb_prompts.jsonl"
output_file = r"data_nb\Mistral\Age\Age_nb_mistral_batch_max3.jsonl"

create_mistral_batch_with_restrictions(input_file, output_file)