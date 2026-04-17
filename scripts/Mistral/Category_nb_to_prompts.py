import json
import argparse
import sys

def create_clean_prompt_file(input_filename, output_filename):
    try:
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

        print(f"✅ Suksess! Ren fil opprettet: {output_filename}")
        
    except FileNotFoundError:
        print(f"❌ FEIL: Fant ikke input-filen: {input_filename}")
    except Exception as e:
        print(f"❌ En uventet feil oppstod: {e}")

if __name__ == "__main__":
    # Sett opp argument-parser
    parser = argparse.ArgumentParser(description="Vasker JSONL-data for Mistral Batch.")
    
    # Legg til flaggene dine
    parser.add_argument("-i", "--input", required=True, help="Sti til input JSONL-fil")
    parser.add_argument("-o", "--output", required=True, help="Sti til output JSONL-fil")
    
    args = parser.parse_args()

    # Kjør funksjonen med parameterne fra CMD
    create_clean_prompt_file(args.input, args.output)