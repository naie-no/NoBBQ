import pandas as pd
import json
import re
import ast
import os

def parse_kv_lists(cell):
    """Parses 'KEY: [val1, val2]' format from CSV cells."""
    if not cell or str(cell).lower() in ("nan", "none", ""):
        return {}
    out = {}
    # Improved regex to capture keys like KJØNN2 or POSS2
    matches = re.findall(r'([\w\d]+)\s*:\s*\[(.*?)\]', str(cell))
    for key, inner_content in matches:
        try:
            vals = ast.literal_eval("[" + inner_content + "]")
        except:
            vals = [v.strip().strip('"').strip("'") for v in inner_content.split(",") if v.strip()]
        out[key] = vals
    return out

def fill_template(template, replacements):
    """Replaces {{VAR}} with values from the replacements dict."""
    if not isinstance(template, str) or "{{" not in template:
        return template
    res = template
    for placeholder, value in replacements.items():
        res = res.replace(f"{{{{{placeholder}}}}}", str(value))
    return res

def generate_jsonl():
    input_path = os.path.join("templates", "Age_nb.csv")
    output_path = os.path.join("data_nb", "Age_nb.jsonl")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df = pd.read_csv(input_path, sep=';', encoding='utf-8-sig', na_filter=False)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        global_id = 0
        
        for _, row in df.iterrows():
            vars_map = parse_kv_lists(row.get('Names', ''))
            vars_map.update(parse_kv_lists(row.get('Lexical_diversity', '')))
            
            if "NAME1" not in vars_map or "NAME2" not in vars_map:
                continue

            name1_list = vars_map["NAME1"]
            name2_list = vars_map["NAME2"]

            # Pair every Name1 with every Name2 (Cartesian Product)
            for j in range(len(name1_list)):
                for k in range(len(name2_list)):
                    
                    repl = {}
                    # Build the replacement map for THIS pair
                    for key, vals in vars_map.items():
                        # Logic: 
                        # If the key contains '2', it's tied to the second name (index k)
                        # Otherwise, it's tied to the first name or general context (index j)
                        if "2" in key:
                            idx = k
                        else:
                            idx = j
                        
                        # Fallback: if the list is shorter than the index, use the last item
                        # This handles cases where KJØNN2 might only have 1 value while NAME2 has 6.
                        repl[key] = vals[idx] if idx < len(vals) else vals[-1]

                    # Standard 4 permutations
                    for condition in ['ambig', 'disambig']:
                        for polarity in ['neg', 'nonneg']:
                            context_raw = row['Ambiguous_Context']
                            if condition == 'disambig':
                                context_raw = f"{row['Ambiguous_Context']} {row['Disambiguating_Context']}"
                            
                            if polarity == 'neg':
                                q_text = row['Question_negative_stereotype']
                                a_neg = row['Answer_negative']
                                a_nonneg = row['Answer_non_negative']
                            else:
                                q_text = row['Question_non_negative']
                                a_neg = row['Answer_non_negative']
                                a_nonneg = row['Answer_negative']

                            entry = {
                                "example_id": global_id,
                                "question_index": str(row['Q_id']),
                                "question_polarity": polarity,
                                "context_condition": condition,
                                "category": "Age",
                                "answer_info": {
                                    "ans0": [fill_template("{{NAME1}}", repl), row['NAME1_info']],
                                    "ans1": ["Ikke mulig å avgjøre", "unknown"],
                                    "ans2": [fill_template("{{NAME2}}", repl), row['NAME2_info']]
                                },
                                "additional_metadata": {
                                    "subcategory": "None",
                                    "stereotyped_groups": ast.literal_eval(row['Known_stereotyped_groups']) if row['Known_stereotyped_groups'] else [],
                                    "version": row['version'],
                                    "source": row['Notes']
                                },
                                "context": fill_template(context_raw, repl),
                                "question": fill_template(q_text, repl),
                                "ans0": fill_template(a_neg, repl),
                                "ans1": "Ikke mulig å avgjøre",
                                "ans2": fill_template(a_nonneg, repl),
                                "label": 1
                            }
                            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            global_id += 1

if __name__ == "__main__":
    generate_jsonl()
    print("Generation complete. All {{NAME}}, {{KJØNN}}, and {{POSS}} placeholders should be replaced.")