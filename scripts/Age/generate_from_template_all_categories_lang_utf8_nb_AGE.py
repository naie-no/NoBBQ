import pandas as pd
import json
import re
import ast
import os
import random

def parse_kv_lists(cell):
    """
    Forbedret parser for formatet: "KEY: [val1, val2]; KEY2: [val3]"
    Håndterer både enkle og doble anførselstegn.
    """
    if not cell or str(cell).lower() in ("nan", "none", ""):
        return {}
    
    out = {}
    # Denne regexen er mer robust for semikolon-separerte lister i én celle
    matches = re.findall(r'([\w\d]+)\s*:\s*\[(.*?)\]', str(cell))
    
    for key, inner_content in matches:
        # Vi prøver å splitte på komma, men fjerne ekstra anførselstegn manuelt
        # Dette er tryggere enn ast.literal_eval når dataene er ujevne
        vals = [v.strip().strip('"').strip("'") for v in inner_content.split(",") if v.strip()]
        out[key] = vals
    return out

def fill_template(template, replacements):
    if not isinstance(template, str) or "{{" not in template:
        return template
    res = template
    for placeholder, value in replacements.items():
        res = res.replace(f"{{{{{placeholder}}}}}", str(value))
    return res

def generate_jsonl():
    # Sjekk at stier er korrekte (juster disse hvis du kjører fra et annet sted)
    input_dir = "templates"
    input_path = os.path.join(input_dir, "Age_nb.csv")
    output_dir = "data_nb"
    output_path = os.path.join(output_dir, "Age_nb.jsonl")
    
    if not os.path.exists(input_path):
        print(f"❌ FEIL: Fant ikke {input_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    # Bruker sep=';' siden filen din er semikolon-separert
    df = pd.read_csv(input_path, sep=';', encoding='utf-8-sig', na_filter=False)
    
    print(f"📖 Leste {len(df)} maler fra CSV. Starter generering...")

    with open(output_path, 'w', encoding='utf-8') as f:
        global_id = 0
        
        for _, row in df.iterrows():
            # Henter variabler fra 'Names'-kolonnen
            vars_map = parse_kv_lists(row.get('Names', ''))
            # Legger til 'Lexical_diversity' hvis den finnes
            vars_map.update(parse_kv_lists(row.get('Lexical_diversity', '')))
            
            # Sjekk om vi faktisk fikk ut navn
            if "NAME1" not in vars_map or "NAME2" not in vars_map:
                continue

            # Generer alle kombinasjoner av navnene
            for j in range(len(vars_map["NAME1"])):
                for k in range(len(vars_map["NAME2"])):
                    repl = {}
                    for key, vals in vars_map.items():
                        # Hvis nøkkelen slutter på 2 (f.eks POSS2), bruk index k, ellers j
                        idx = k if '2' in key else j
                        repl[key] = vals[idx] if idx < len(vals) else vals[-1]

                    for condition in ['ambig', 'disambig']:
                        for polarity in ['neg', 'nonneg']:
                            
                            # Kontekst-logikk
                            context_raw = row['Ambiguous_Context']
                            if condition == 'disambig':
                                context_raw = f"{row['Ambiguous_Context']} {row['Disambiguating_Context']}"
                            
                            q_text = fill_template(row['Question_negative_stereotype'] if polarity == 'neg' else row['Question_non_negative'], repl)
                            
                            # Definer svaralternativer
                            person_a = fill_template(row['Answer_negative'], repl)
                            person_b = fill_template(row['Answer_non_negative'], repl)
                            unknown = "Ikke mulig å avgjøre"
                            
                            # Finn korrekt svar for denne runden
                            if condition == 'ambig':
                                fact_target = unknown
                            else:
                                fact_target = person_a if polarity == 'neg' else person_b
                            
                            # Full randomisering av alle tre
                            choices = [person_a, person_b, unknown]
                            random.shuffle(choices)
                            label = choices.index(fact_target)

                            entry = {
                                "example_id": global_id,
                                "question_index": str(row['Q_id']),
                                "question_polarity": polarity,
                                "context_condition": condition,
                                "category": "Age",
                                "context": fill_template(context_raw, repl),
                                "question": q_text,
                                "ans0": choices[0],
                                "ans1": choices[1],
                                "ans2": choices[2],
                                "label": label
                            }
                            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            global_id += 1

            if int(row['Q_id']) % 5 == 0:
                print(f"   ...Prosesserer Q_id {row['Q_id']}")

    print(f"\n✅ FERDIG! Genererte {global_id} rader.")
    print(f"📂 Lagret i: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    generate_jsonl()