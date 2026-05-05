import json
import argparse
import sys

def create_mistral_batch_upload_vanilla(input_filename, output_filename):
    try:
        with open(input_filename, 'r', encoding='utf-8') as infile, \
             open(output_filename, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                if not line.strip(): continue
                data = json.loads(line)
                
                example_id = str(data.get('example_id'))
                # Vi bruker final_prompt som inneholder context + question fra forrige steg
                prompt = data.get('final_prompt', '')
                
                batch_request = {
                    "custom_id": example_id,
                    "body": {
                        "model": "mistral-large-latest",
                        "messages": [
                            # Legger til instruksen her for å holde svarene korte
                            {"role": "system", "content": "Answer in maximum 3 sentences."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0
                    }
                }
                
                outfile.write(json.dumps(batch_request, ensure_ascii=False) + "\n")
        
        print(f"✅ Batch-fil klar for opplasting: {output_filename}")

    except FileNotFoundError:
        print(f"❌ FEIL: Fant ikke filen {input_filename}")
    except Exception as e:
        print(f"❌ En uventet feil oppstod: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Konverterer vaskede prompts til Mistral Batch format.")
    
    # Legger til -i og -o argumenter
    parser.add_argument("-i", "--input", required=True, help="Input jsonl-fil (vaskede prompts)")
    parser.add_argument("-o", "--output", required=True, help="Output jsonl-fil (klar for Mistral)")
    
    args = parser.parse_args()

    create_mistral_batch_upload_vanilla(args.input, args.output)