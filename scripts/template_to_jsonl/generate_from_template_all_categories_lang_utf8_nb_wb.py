import pandas as pd
import numpy as np
import io
import json
import csv
import random
import re
import ast
import os
from pathlib import Path

# Utils import (støtter begge repo-oppsett)
try:
    from utils import * # type: ignore
except ImportError:
    from BBQ_Full.utils import * # type: ignore

def debug_csv_lines(path):
    last_err = None
    for enc in ("utf-8-sig", "cp1252"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample, delimiters=";\t,")
                delim = dialect.delimiter
                for lineno, line in enumerate(f, start=1):
                    try:
                        next(csv.reader([line], delimiter=delim, quotechar='"'))
                    except Exception:
                        print(f"\nFeil i CSV-linje {lineno} ({enc}): {line}")
                        return
                return
        except Exception as e:
            last_err = e
    raise last_err

def read_template_csv(path):
    for enc in ("utf-8-sig", "cp1252"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                sample = f.read(4096); f.seek(0)
                sep = csv.Sniffer().sniff(sample, delimiters=";\t,").delimiter
            return pd.read_csv(path, na_filter=False, encoding=enc, sep=sep, engine="python")
        except Exception: continue
    raise Exception(f"Kunne ikke lese {path}")

def parse_list_cell(val):
    if not val or str(val).lower() in ("nan", "none"): return []
    s = str(val).strip().replace('""', '"')
    try: return json.loads(s) if "[" in s else []
    except:
        try: return ast.literal_eval(s)
        except: return []

def parse_kv_lists(cell: str) -> dict:
    if not cell or str(cell).lower() in ("nan", "none"): return {}
    out = {}
    for m in re.finditer(r'([^:;\s]+)\s*:\s*\[([^\]]*)\]', str(cell)):
        key, inner = m.group(1).strip(), m.group(2).strip()
        try: out[key] = ast.literal_eval("[" + inner + "]")
        except: out[key] = [v.strip() for v in inner.split(",") if v.strip()]
    return out

# Oppsett av stier og språk
LANG = os.environ.get("BBQ_LANG", "nb").lower()
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = ROOT_DIR / "templates"
DATA_DIR = ROOT_DIR / ("data" if LANG == "en" else "data_nb")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _pick_csv(stem: str) -> str:
    p = TEMPLATES_DIR / f"{stem}_nb.csv"
    return str(p) if p.exists() else str(TEMPLATES_DIR / f"{stem}.csv")

# all possible values of cat
cats = [
#    "Disability_status",
#    "Age",
#    "Physical_appearance",
#    "SES",
    "Gender_identity",
#    "Race_ethnicity",
#    "Religion",
#    "Nationality",
#    "Sexual_orientation",
]

vocab = pd.read_csv(_pick_csv("vocabulary_nb"), encoding="utf-8-sig")
vocab.columns = [c.lstrip("\ufeff").strip() for c in vocab.columns]
names_vocab = pd.read_csv(_pick_csv("vocabulary_proper_names_nb"), encoding="utf-8-sig")

def _get_vocab_value(df, name, col, fallback):
    try:
        hit = df.loc[df["Name"] == name, col]
        return hit.iloc[0] if not hit.empty and hit.iloc[0] else fallback
    except: return fallback

def _replace_slots_in_rowdf(row_df, replacements):
    for col in row_df.columns:
        if row_df[col].dtype == object:
            row_df[col] = row_df[col].apply(lambda x: _replace_many(x, replacements) if isinstance(x, str) else x)
    return row_df

def _replace_many(text, repl):
    for k, v in repl.items(): text = text.replace(k, str(v))
    return text

def apply_extra_name_slots(row_df, words_df, name1, name2):
    n1b = _get_vocab_value(words_df, name1, "Name_nb_def", name1)
    n2b = _get_vocab_value(words_df, name2, "Name_nb_def", name2)
    return _replace_slots_in_rowdf(row_df, {"{{NAME1b}}": n1b, "{{NAME2b}}": n2b})

need_stereotyping_subset = ["Race_ethnicity", "Religion", "Nationality", "Sexual_orientation"]
unknown_options_lang = ["Ukjent", "Kan ikke avgjøres", "Kan ikke fastslås", "Ikke mulig å avgjøre", "Kan ikke besvares", "Ikke kjent", "Ikke nok info", "Ikke nok informasjon", "Kan ikke svare", "Uavklart"]

for cat in cats:
    tpl_path = _pick_csv(cat)
    if not Path(tpl_path).exists(): continue
    
    frames = read_template_csv(tpl_path)
    the_frames = frames[frames.Ambiguous_Context != ""].reset_index()
    dat_file = io.open(DATA_DIR / f"{cat}.jsonl", "w", encoding="utf-8", newline="\n")
    nn = 0

    for i in range(len(the_frames)):
        cat_match = cat.replace("_", "").lower()
        words = vocab[vocab["Category"].str.replace("_", "").str.lower() == cat_match]
        
        bias_targets = parse_list_cell(the_frames.Known_stereotyped_groups[i])
        prop_val = str(the_frames.Proper_nouns_only[i]).strip().upper()
        has_proper_name = (prop_val == "TRUE")

        if "Subcategory" in the_frames.columns and len(str(the_frames.Subcategory[i])) > 1:
            this_subcat = the_frames.Subcategory[i]
            words = words[words.SubCat == this_subcat]
        else: this_subcat = "None"

        possible_word_list = words.Name.unique().tolist()
        if (len(bias_targets) > 0) and (cat in need_stereotyping_subset):
            targeted_word_list = [x for x in possible_word_list if x in bias_targets]
        else: targeted_word_list = possible_word_list

        word_list = random.sample(targeted_word_list, min(len(targeted_word_list), 5)) if len(targeted_word_list) > 4 else targeted_word_list

        names_override = parse_kv_lists(the_frames.Names[i]) if "Names" in the_frames.columns else {}
        
        if has_proper_name:
            words = names_vocab 
            if cat == "Race_ethnicity":
                f_names = names_vocab[(names_vocab.First_last == "first") & (names_vocab.ethnicity.isin(bias_targets))] if bias_targets else names_vocab[names_vocab.First_last == "first"]
                word_list = random.sample(f_names.Name.tolist(), min(len(f_names), 5))
            elif cat == "Gender_identity":
                f_names = names_vocab[(names_vocab.First_last == "first_only") & (names_vocab.gender == "F")]
                word_list = random.sample(f_names.Name.tolist(), min(len(f_names), 5))
            else:
                f_names = names_vocab[names_vocab.First_last == "first_only"]
                word_list = random.sample(f_names.Name.tolist(), min(len(f_names), 6))

        for j in range(len(word_list)):
            this_word = word_list[j]
            lex_div = the_frames.Lexical_diversity[i]
            if len(str(lex_div)) > 1:
                names_override.update(parse_kv_lists(lex_div))

            if cat == "SES" and not has_proper_name:
                w_info = words.loc[words["Name"] == this_word, "Info"].iloc[0]
                new_word_list = words[words.Info != w_info].Name.unique().tolist()
            elif cat == "Gender_identity" and has_proper_name:
                w_gen = names_vocab.loc[names_vocab["Name"] == this_word, "gender"].iloc[0]
                new_word_list = names_vocab[names_vocab.gender != w_gen].Name.unique().tolist()
            else:
                new_word_list = [n for n in word_list if n != this_word]
            
            new_word_list = random.sample(new_word_list, min(len(new_word_list), 5))

            for k in range(len(new_word_list)):
                this_word_2 = new_word_list[k]
                
                for flip in [False, True]:
                    w1, w2 = (this_word_2, this_word) if flip else (this_word, this_word_2)
                    idx1, idx2 = (k, j) if flip else (j, k)
                    
                    row = the_frames.iloc[[i]].reset_index()
                    rand_w1 = ""; rand_w2 = ""
                    if len(str(lex_div)) > 1:
                        l1, l2 = return_list_from_string(lex_div)
                        rand_w1 = random.choice(l1) if l1 else ""
                        rand_w2 = random.choice(l2) if l2 else ""

                    row = do_slotting(row, the_frames.columns, w1, None, w2, None, lex_div, rand_w1, rand_w2, lang=LANG)

                    repl = {}
                    for key, values in names_override.items():
                        if not values: continue
                        if key in ("NAME1b", "WORD1b", "KJØNN1", "POSS1", "WORD1"):
                            if idx1 < len(values): repl[f"{{{{{key}}}}}"] = values[idx1]
                        elif key in ("NAME2b", "WORD2b", "KJØNN2", "POSS2", "WORD2"):
                            if idx2 < len(values): repl[f"{{{{{key}}}}}"] = values[idx2]
                        elif key not in ("NAME1", "NAME2"):
                            repl[f"{{{{{key}}}}}"] = values[0] if len(values)==1 else random.choice(values)
                    
                    if repl: row = _replace_slots_in_rowdf(row, repl)
                    if (not names_override) or ("NAME1b" not in names_override):
                        row = apply_extra_name_slots(row, words, w1, w2)

                    n1_info = _get_vocab_value(words, w1, "gender" if has_proper_name else "Info", w1)
                    n2_info = _get_vocab_value(words, w2, "gender" if has_proper_name else "Info", w2)
                    
                    data = create_templating_dicts(cat, row, this_subcat, unknown_options_lang, the_frames.columns, bias_targets, w1, w2, n1_info, n2_info, nn)
                    
                    # FIKS: Bruker default=str for å håndtere int64-problemer
                    for item in data:
                        dat_file.write(json.dumps(item, default=str, ensure_ascii=False) + "\n")
                    nn += 4; dat_file.flush()

    print(f"Genererte {nn} linjer for {cat}")
    dat_file.close()