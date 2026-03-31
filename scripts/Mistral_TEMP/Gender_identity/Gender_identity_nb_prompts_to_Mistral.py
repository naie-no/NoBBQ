import json

def create_mistral_batch_upload_vanilla(input_filename, output_filename):
    with open(input_filename, 'r', encoding='utf-8') as infile, \
         open(output_filename, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            if not line.strip(): continue
            data = json.loads(line)
            
            example_id = str(data.get('example_id'))
            # Vi bruker final_prompt som inneholder context + question
            prompt = data.get('final_prompt', '')
            
            batch_request = {
                "custom_id": example_id,
                "body": {
                    "model": "mistral-large-latest",
                    "messages": [
                        # KUN brukermelding, ingen system-instruks overhodet
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0
                    # Vi utelater max_tokens helt for ubegrenset lengde
                }
            }
            
            outfile.write(json.dumps(batch_request, ensure_ascii=False) + "\n")

create_mistral_batch_upload_vanilla(r".\data_nb\Gender_identity_nb_prompts.jsonl", r".\data_nb\Gender_identity_mistral_batch.jsonl")