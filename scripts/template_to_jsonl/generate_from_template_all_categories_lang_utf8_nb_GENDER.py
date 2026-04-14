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


def read_csv_auto(path, default_sep=","):
    """
    Read CSV with a sensible separator guess.
    Templates are semicolon-separated, vocab files are comma-separated.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required file: {path}")

    with open(path, "r", encoding="utf-8-sig") as f:
        first_line = f.readline()

    sep = ";" if first_line.count(";") > first_line.count(",") else default_sep
    return pd.read_csv(path, sep=sep, encoding="utf-8-sig").fillna("")


def parse_kv_pairs(text):
    if not text or pd.isna(text) or str(text).strip() == "":
        return None
    pairs = {}
    parts = str(text).split(";")
    for part in parts:
        if ":" in part:
            key, val_str = part.split(":", 1)
            key = key.strip().replace("{", "").replace("}", "")
            match = re.search(r"\[(.*?)\]", val_str)
            if match:
                vals = [v.strip().strip("'").strip('"') for v in match.group(1).split(",")]
                pairs[key] = vals
    return pairs


def normalize_name_instance(inst):
    """
    Keep NAME1/NAME2 raw for templates like 'en {{NAME1}}',
    and ensure NAME1b/NAME2b exist for answer/disambiguation text.
    """
    inst = dict(inst)
    for k in ["NAME1", "NAME2", "NAME1b", "NAME2b"]:
        if k in inst and isinstance(inst[k], str):
            inst[k] = inst[k].strip()

    # Prevent accidental 'en en ...'
    for k in ["NAME1", "NAME2"]:
        if isinstance(inst.get(k), str) and inst[k].lower().startswith("en "):
            inst[k] = inst[k][3:].strip()

    if "NAME1b" not in inst or not inst["NAME1b"]:
        inst["NAME1b"] = inst.get("NAME1", "")
    if "NAME2b" not in inst or not inst["NAME2b"]:
        inst["NAME2b"] = inst.get("NAME2", "")
    return inst


def get_nonproper_pool(subcat):
    """
    For Proper_nouns_only != TRUE:
    use vocabulary_nb.csv unless Names column overrides it.
    """
    if not os.path.exists(VOCAB_NB):
        return []

    v_df = read_csv_auto(VOCAB_NB)

    # Handle either Gender_identity or GenderIdentity defensively
    cat_mask = v_df["Category"].astype(str).isin(["Gender_identity", "GenderIdentity"])
    subset = v_df[cat_mask].copy()

    if subcat and "SubCat" in subset.columns:
        sub_subset = subset[subset["SubCat"].astype(str) == str(subcat)]
        if not sub_subset.empty:
            subset = sub_subset

    if subset.empty:
        return []

    # Prefer explicit gender contrast if available
    female_rows = subset[subset["Info"].astype(str).isin(["F", "female", "Female"])]
    male_rows = subset[subset["Info"].astype(str).isin(["M", "male", "Male"])]

    pool = []
    if not female_rows.empty and not male_rows.empty:
        for _, f_row in female_rows.iterrows():
            for _, m_row in male_rows.iterrows():
                pool.append(
                    normalize_name_instance(
                        {
                            "NAME1": f_row["Name"],
                            "NAME1b": f_row.get("Name_nb_def", f_row["Name"]),
                            "NAME2": m_row["Name"],
                            "NAME2b": m_row.get("Name_nb_def", m_row["Name"]),
                        }
                    )
                )
        return pool

    # Fallback: just take distinct pairs in order from the subset
    rows = subset.to_dict(orient="records")
    for i in range(len(rows)):
        for j in range(len(rows)):
            if i == j:
                continue
            r1, r2 = rows[i], rows[j]
            pool.append(
                normalize_name_instance(
                    {
                        "NAME1": r1["Name"],
                        "NAME1b": r1.get("Name_nb_def", r1["Name"]),
                        "NAME2": r2["Name"],
                        "NAME2b": r2.get("Name_nb_def", r2["Name"]),
                    }
                )
            )
    return pool


def get_proper_pool():
    """
    For Proper_nouns_only == TRUE:
    always use real names from vocabulary_proper_names_nb.csv.
    We create female-vs-male contrast pairs, matching the original BBQ intent.
    """
    if not os.path.exists(PROPER_NB):
        return []

    p_df = read_csv_auto(PROPER_NB)

    if "First_last" in p_df.columns:
        first_vals = {"first", "first_only"}
        first_names = p_df[p_df["First_last"].astype(str).isin(first_vals)].copy()
        if first_names.empty:
            first_names = p_df.copy()
    else:
        first_names = p_df.copy()

    females = first_names[first_names["gender"].astype(str) == "F"]["Name"].dropna().astype(str).unique().tolist()
    males = first_names[first_names["gender"].astype(str) == "M"]["Name"].dropna().astype(str).unique().tolist()

    random.shuffle(females)
    random.shuffle(males)

    pool = []
    for f in females:
        for m in males:
            pool.append(normalize_name_instance({"NAME1": f, "NAME1b": f, "NAME2": m, "NAME2b": m}))
    return pool


def get_fallback_pool(is_proper, subcat):
    return get_proper_pool() if is_proper else get_nonproper_pool(subcat)


def apply_template(text, replacements):
    if not text:
        return ""
    for k in sorted(replacements.keys(), key=len, reverse=True):
        text = text.replace(f"{{{{{k}}}}}", str(replacements[k]))
    return text


def emit_variants_for_pair(row, curr, example_id, all_entries):
    ambig_t = apply_template(row["Ambiguous_Context"], curr)
    disam_t = apply_template(row["Disambiguating_Context"], curr)

    for cond in ["ambig", "disambig"]:
        full_ctx = f"{ambig_t} {disam_t}".strip() if cond == "disambig" else ambig_t
        for pol in ["neg", "nonneg"]:
            q_tmpl = row["Question_negative_stereotype"] if pol == "neg" else row["Question_non_negative"]
            q_text = apply_template(q_tmpl, curr)
            if not q_text.strip():
                continue

            ans_unk = UNKNOWN_STR
            ans_non = apply_template(row["Answer_non_negative"], curr)
            ans_neg = apply_template(row["Answer_negative"], curr)

            target = ans_non if pol == "nonneg" else ans_neg
            answers = [ans_unk, ans_non, ans_neg]
            random.shuffle(answers)

            entry = {
                "example_id": example_id,
                "question_index": str(row["Q_id"]),
                "question_polarity": pol,
                "context_condition": cond,
                "category": "Gender_identity",
                "context": full_ctx,
                "question": q_text,
                "ans0": answers[0],
                "ans1": answers[1],
                "ans2": answers[2],
                "label": answers.index(ans_unk if cond == "ambig" else target),
                "metadata": {
                    "subcategory": row["Subcategory"],
                    "proper_nouns_only": str(row.get("Proper_nouns_only", "")),
                },
            }
            all_entries.append(entry)
            example_id += 1

    return example_id


def run_generator():
    df = read_csv_auto(MAIN_TEMPLATE, default_sep=";")
    num_rows = len(df[df["Q_id"].astype(str) != ""])
    instances_per_row = (TOTAL_TARGET // num_rows) // VARIANTS_PER_INST

    all_entries = []
    example_id = 0

    for _, row in df.iterrows():
        if not str(row["Q_id"]).strip():
            continue

        is_proper = str(row.get("Proper_nouns_only", "")).strip().upper() == "TRUE"
        subcat = row.get("Subcategory", "")

        name_map = parse_kv_pairs(row.get("Names", ""))
        word_map = parse_kv_pairs(row.get("Lexical_diversity", "")) or {"WORD1": [""]}

        row_instances = []

        # Priority 1: explicit Names column overrides vocab ONLY when it is filled.
        if name_map and "NAME1" in name_map:
            for i in range(len(name_map["NAME1"])):
                inst = {k: v_list[i] for k, v_list in name_map.items() if i < len(v_list)}
                row_instances.append(normalize_name_instance(inst))

        # Priority 2:
        # - proper nouns rows => real names from vocabulary_proper_names_nb.csv
        # - non-proper rows => vocabulary_nb.csv
        fallback_pool = get_fallback_pool(is_proper, subcat)

        num_words = max(1, len(word_map.get("WORD1", [""])))
        target_instances = max(1, instances_per_row // num_words)

        # If row has explicit Names, keep them. Otherwise fill from the appropriate vocab source.
        if not row_instances:
            if fallback_pool:
                if len(fallback_pool) <= target_instances:
                    row_instances.extend(fallback_pool)
                else:
                    row_instances.extend(random.sample(fallback_pool, target_instances))

        for name_repl in row_instances:
            for w_idx in range(num_words):
                curr = dict(name_repl)
                for wk, wv in word_map.items():
                    curr[wk] = wv[w_idx] if w_idx < len(wv) else wv[0]

                # Emit normal ordering
                example_id = emit_variants_for_pair(row, curr, example_id, all_entries)

                # Emit flipped ordering to match original BBQ generator behavior
                if curr.get("NAME1") != curr.get("NAME2"):
                    flipped = curr.copy()
                    for a, b in [("NAME1", "NAME2"), ("NAME1b", "NAME2b")]:
                        flipped[a], flipped[b] = flipped.get(b, ""), flipped.get(a, "")
                    example_id = emit_variants_for_pair(row, flipped, example_id, all_entries)

    all_entries = all_entries[:TOTAL_TARGET]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Dataset generated: {len(all_entries)} entries.")


if __name__ == "__main__":
    run_generator()
