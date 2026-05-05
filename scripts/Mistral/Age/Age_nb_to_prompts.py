import json

def create_clean_prompt_file(input_filename, output_filename):
    with open(input_filename, 'r', encoding='utf-8') as infile, \
         open(output_filename, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            if not line.strip(): continue
            data = json.loads(line)
            
            # Henter ut ID og tekstfelter
            example_id = data.get('example_id')
            context = data.get('context', '').strip()
            question = data.get('question', '').strip()
            
            # Kombinerer til en ren tekststreng
            combined_prompt = f"{context} {question}".replace("  ", " ").strip()
            
            # Lager ny dictionary med ID for mapping
            clean_entry = {
                "example_id": example_id,
                "final_prompt": combined_prompt
            }
            
            outfile.write(json.dumps(clean_entry, ensure_ascii=False) + "\n")

    print(f"✅ Ren fil med ID-er opprettet: {output_filename}")

# Kjør skriptet
create_clean_prompt_file(r".\data_nb\Age_nb.jsonl", r".\data_nb\Age_nb_prompts.jsonl")