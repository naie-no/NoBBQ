import pandas as pd
import json
import os
import re
import random

# --- CONFIGURATION ---
BASE_DIR = os.getcwd()
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
MAIN_TEMPLATE = os.path.join(TEMPLATE_DIR, "Gender_identity_nb.csv")
VOCAB_NB = os.path.join(TEMPLATE_DIR, "vocabulary_nb.csv")
PROPER_NB = os.path.join(TEMPLATE_DIR, "vocabulary_proper_names_nb.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "Gender_identity_expanded.jsonl")

UNKNOWN_STR = "Kan ikke avgjøres"
TOTAL_TARGET = 5760
VARIANTS_PER_INST = 4 

def parse_kv_pairs(text):
    if not text or pd.isna(text) or str(text).strip() == "":
        return None
    pairs = {}
    parts = str(text).split(';')
    for part in parts:
        if ':' in part:
            key, val_str = part.split(':', 1)
            key = key.strip().replace('{', '').replace('}', '')
            match = re.search(r'\[(.*?)\]', val_str)
            if match:
                vals = [v.strip().strip("'").strip('"') for v in match.group(1).split(',')]
                pairs[key] = vals
    return pairs

def get_fallback_pool(is_proper, subcat):
    pool = []
    if is_proper:
        if os.path.exists(PROPER_NB):
            p_df = pd.read_csv(PROPER_NB).fillna("")
            males = p_df[p_df['gender'] == 'M']['Name'].tolist()
            females = p_df[p_df['gender'] == 'F']['Name'].tolist()
            random.shuffle(males); random.shuffle(females)
            for m, f in zip(males, females):
                pool.append({"NAME1": f, "NAME1b": f, "NAME2": m, "NAME2b": m})
    else:
        if os.path.exists(VOCAB_NB):
            v_df = pd.read_csv(VOCAB_NB).fillna("")
            subset = v_df[v_df['Category'] == 'Gender_identity']
            if subcat: subset = subset[subset['SubCat'] == subcat]
            if len(subset) >= 2:
                # We use the raw name (e.g. "mann") and let the template provide the "en"
                n1, n2 = subset.iloc[0], subset.iloc[1]
                pool.append({"NAME1": n1['Name'], "NAME1b": n1['Name_nb_def'], 
                             "NAME2": n2['Name'], "NAME2b": n2['Name_nb_def']})
    return pool

def apply_template(text, replacements):
    if not text: return ""
    # Sort keys by length descending to replace NAME1b before NAME1
    for k in sorted(replacements.keys(), key=len, reverse=True):
        text = text.replace(f"{{{{{k}}}}}", str(replacements[k]))
    return text

def run_generator():
    # Detect delimiter and read
    df = pd.read_csv(MAIN_TEMPLATE, sep=';', encoding='utf-8-sig').fillna("")
    num_rows = len(df[df['Q_id'] != ""])
    instances_per_row = (TOTAL_TARGET // num_rows) // VARIANTS_PER_INST
    
    all_entries = []
    example_id = 0

    for idx, row in df.iterrows():
        if not str(row['Q_id']).strip(): continue

        is_proper = str(row['Proper_nouns_only']).upper() == "TRUE"
        subcat = row['Subcategory']
        
        name_map = parse_kv_pairs(row['Names'])
        word_map = parse_kv_pairs(row['Lexical_diversity']) or {"WORD1": [""]}
        
        row_instances = []
        # Priority 1: Specific Name overrides from the CSV
        if name_map and 'NAME1' in name_map:
            for i in range(len(name_map['NAME1'])):
                inst = {k: v_list[i] for k, v_list in name_map.items() if i < len(v_list)}
                row_instances.append(inst)
        
        # Priority 2: Expansion using Vocab files
        fallback_pool = get_fallback_pool(is_proper, subcat)
        num_words = len(word_map.get('WORD1', [""]))
        target_instances = instances_per_row // num_words

        while len(row_instances) < target_instances:
            if not fallback_pool: break
            row_instances.append(random.choice(fallback_pool).copy())

        for name_repl in row_instances:
            # CLEANUP: Remove any "en " prefix that might have been 
            # accidentally added to the variable to prevent "en en"
            for k in ["NAME1", "NAME2"]:
                if isinstance(name_repl.get(k), str) and name_repl[k].startswith("en "):
                    name_repl[k] = name_repl[k][3:]

            for w_idx in range(num_words):
                curr = name_repl.copy()
                for wk, wv in word_map.items():
                    curr[wk] = wv[w_idx] if w_idx < len(wv) else wv[0]

                ambig_t = apply_template(row['Ambiguous_Context'], curr)
                disam_t = apply_template(row['Disambiguating_Context'], curr)

                for cond in ["ambig", "disambig"]:
                    full_ctx = f"{ambig_t} {disam_t}".strip() if cond == "disambig" else ambig_t
                    for pol in ["neg", "nonneg"]:
                        q_tmpl = row['Question_negative_stereotype'] if pol == "neg" else row['Question_non_negative']
                        q_text = apply_template(q_tmpl, curr)
                        if not q_text.strip(): continue

                        ans_unk = UNKNOWN_STR
                        ans_non = apply_template(row['Answer_non_negative'], curr)
                        ans_neg = apply_template(row['Answer_negative'], curr)
                        
                        target = ans_non if pol == "nonneg" else ans_neg
                        answers = [ans_unk, ans_non, ans_neg]
                        random.shuffle(answers)
                        
                        entry = {
                            "example_id": example_id,
                            "question_index": str(row['Q_id']),
                            "question_polarity": pol,
                            "context_condition": cond,
                            "category": "Gender_identity",
                            "context": full_ctx,
                            "question": q_text,
                            "ans0": answers[0], "ans1": answers[1], "ans2": answers[2],
                            "label": answers.index(ans_unk if cond == "ambig" else target),
                            "metadata": {"subcategory": row['Subcategory']}
                        }
                        all_entries.append(entry)
                        example_id += 1

    # Final count check
    all_entries = all_entries[:TOTAL_TARGET]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"Dataset generated: {len(all_entries)} entries. 'en en' issue resolved.")

if __name__ == "__main__":
    run_generator()