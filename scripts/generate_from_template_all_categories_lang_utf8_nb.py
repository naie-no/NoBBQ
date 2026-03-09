import pandas as pd
import numpy as np
import io
import json
# Utils import (support both repo layouts)
try:
    from utils import *  # type: ignore
except ImportError:
    from BBQ_Full.utils import *  # type: ignore
import random
import re
import ast
from pathlib import Path
import os

# Language handling: set environment variable BBQ_LANG=nb to generate Bokmål versions
LANGUAGE = "nb"

# Project root: default to current working directory (where you run the script from)
# You can override by setting BBQ_DIR to a specific path.
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parent
ROOT_DIR = Path(os.environ.get("BBQ_DIR", DEFAULT_ROOT)).resolve()
TEMPLATES_DIR = ROOT_DIR / "templates"
DATA_DIR = ROOT_DIR / "data_nb"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# all possible values of cat
CATEGORIES = [
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

UNKNOWN_OPTIONS_NB = [
    "Ukjent",
    "Kan ikke avgjøres",
    "Kan ikke fastslås",
    "Ikke mulig å avgjøre",
    "Kan ikke besvares",
    "Ikke kjent",
    "Ikke nok info",
    "Ikke nok informasjon",
    "Kan ikke svare",
    "Uavklart"
]

# these have items that need to have the argument order manually reversed
NEED_STEREOTYPING_SUBSET = [
    "Race_ethnicity",
    "Religion",
    "Nationality",
    "Sexual_orientation",
]

def parse_cell_list(val):
    """Parse a cell that should represent a list, e.g. ["F"].
    Accepts Python-literal style, JSON style, and common Excel-escaped variants.
    
    Returns a Python list. Falls back to [] if empty/unparseable.
    """
    if val is None:
        return []
    if isinstance(val, list):
        return val
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return []
    # Fix common Excel doubled-quote escaping
    s = s.replace('""', '"')
    # Try JSON first
    try:
        out = json.loads(s)
        return out if isinstance(out, list) else []
    except Exception:
        pass
    # Try Python literal
    try:
        out = ast.literal_eval(s)
        return out if isinstance(out, list) else []
    except Exception:
        return []

def _get_csv_path(csv_file_name: str) -> str:
    """Get language-specific CSV if present; otherwise fall back to default."""
    if LANGUAGE not in csv_file_name:
        suffix = ""
        if LANGUAGE in ("nb", "no", "bokmaal", "bokmål"):
            suffix = "_nb"

        csv_path = TEMPLATES_DIR / f"{csv_file_name}{suffix}.csv"
        if csv_path.exists():
            return str(csv_path)

    return str(TEMPLATES_DIR / f"{csv_file_name}.csv")


# --- Extra slotting helpers (e.g., Norwegian definite forms) ---
def _get_vocab_value(words_df: pd.DataFrame, name: str, col: str, fallback: str) -> str:
    """Safely fetch a value from the (already category/subcat-filtered) vocab dataframe."""
    try:
        if col not in words_df.columns:
            return fallback
        hit = words_df.loc[words_df["Name"] == name, col]
        if len(hit) == 0:
            return fallback
        val = hit.iloc[0]
        if isinstance(val, str) and len(val) > 0:
            return val
        return fallback
    except Exception:
        return fallback

def _replace_slots_in_rowdf(row_df: pd.DataFrame, replacements: dict) -> pd.DataFrame:
    """Replace placeholders in all string/object columns for a 1-row dataframe."""
    for col in row_df.columns:
        #if row_df[col].dtype == object:
        row_df[col] = row_df[col].apply(
            lambda x: _replace_many(x, replacements) if isinstance(x, str) else x
        )
    return row_df

def _replace_many(text: str, repl: dict) -> str:
    for k, v in repl.items():
        text = text.replace(k, v)
    return text

def _apply_extra_name_slots(row_df: pd.DataFrame, words_df: pd.DataFrame, name1: str, name2: str) -> pd.DataFrame:
    """Currently supports {{NAME1b}}/{{NAME2b}} via vocab column 'Name_nb_def'."""
    # Only do work if placeholders are present anywhere
    blob = " ".join(str(x) for x in row_df.iloc[0].tolist() if isinstance(x, str))
    if "{{NAME1b}}" not in blob and "{{NAME2b}}" not in blob:
        return row_df

    name1_def = _get_vocab_value(words_df, name1, "Name_nb_def", name1)
    name2_def = _get_vocab_value(words_df, name2, "Name_nb_def", name2)

    return _replace_slots_in_rowdf(row_df, {"{{NAME1b}}": name1_def, "{{NAME2b}}": name2_def})

# read in vocabulary files
vocab = pd.read_csv(_get_csv_path("vocabulary"), encoding="utf-8-sig")
if "Pilot_include" in vocab.columns:
    vocab = vocab[vocab["Pilot_include"] != "No"]
names_vocab = pd.read_csv(_get_csv_path("vocabulary_proper_names_nb"), encoding="utf-8-sig")


for category in CATEGORIES:    
    # open the file that all the data will be saved in
    data_file = io.open(DATA_DIR / f"{category}.jsonl", "w", encoding="utf-8", newline="\n")

    # read in the template
    template_path = _get_csv_path(f"{category}_nb")
    frames = pd.read_csv(
        template_path,
        na_filter=False,
        encoding="utf-8-sig",
        sep=";",          # auto-detect delimiter
        engine="python"    # required for sep=None
    )
    the_frames = frames[
        frames.Ambiguous_Context != ""
    ].reset_index()  # get rid of ones that are empty
    frame_cols = the_frames.columns

    # normalize headers once after reading vocab
    vocab.columns = [c.lstrip("\ufeff").strip() for c in vocab.columns]
    #relevant_vocab = vocab[vocab["Category"] == category]
    #possible_names_list = relevant_vocab.Name.unique().tolist()

    # initialize item id counter
    nn = 0

    # ---- NOTE: Loop through each row of the template ---- #
    for i in range(len(the_frames)):
        # --- NOTE: For some reason starting the loop with retrieving cateegory specific info (for the whole table) --- #
        # Take the words from the vocab that match this category
        relevant_vocab = vocab[vocab["Category"] == category] # NOTE: relevant_vocab is later on manipulated based on subcat (if there is one). Pretty sure it should be possible to filter on both at the same time
        possible_names_list = relevant_vocab.Name.unique().tolist()

        # --- NOTE: Then start using row-specific info --- #
        # Retrieve stereotyped group target(s) for this row (handles JSON/Python-literal/Excel-escaped)
        bias_targets = parse_cell_list(the_frames.Known_stereotyped_groups[i])

        # -- NOTE: Check if category needs stereotyping subset and manipulate target names if necessary. -- #
        # -- Based on line specific and category-specific info -- #
        # Stereotyped groups info is not relevant for subsetting Names in some categories
        # so only use that for creating the targeted word list when the info is provided, otherwise all possible
        # vocab items are targets
        if (len(bias_targets) > 0) and (category in NEED_STEREOTYPING_SUBSET):
            targeted_names_list = [x for x in possible_names_list if x in bias_targets] # TODO: What is the intention here
        else:
            targeted_names_list = possible_names_list
        
        # -- NOTE: Downsample to 5 target names if needed -- #
        # if the list of bias targets is too big, downsample
        # TODO: Why downsample?
        if len(targeted_names_list) > 4:
            names_list = random.sample(targeted_names_list, 5) # TODO: why 5, when the if checks for len > 4? Why not just check for len > 5?
        elif len(possible_names_list) < 2:  # these will be handled later # TODO: why now suddenly use possible_names_list, not targeted_names_list????
            names_list = []
        else:
            names_list = targeted_names_list

        # -- NOTE: Check line specific subcategory and filter out relevant vocabulary if there is a subcategory-- #
        # TODO: What is the idea here? This overrides the logic above when the row has a subcategory. NOTE: pretty sure the two logics can be combined
        # if the word list needs to be further pulled apart within subcategory, do that here
        if "Subcategory" in frame_cols:
            this_subcat = the_frames.Subcategory[i]
            if this_subcat:
                relevant_vocab = relevant_vocab[relevant_vocab.SubCat == this_subcat]
                names_list = relevant_vocab.Name.unique().tolist()
                if len(names_list) > 5:
                    names_list = random.sample(names_list, 5)  # for downsampling
            else:
                this_subcat = "None"
        else:
            this_subcat = "None"
        

        # -- NOTE: Check if there's a custom list of names in the Names column for this row and use that if so -- #
        # TODO: so here names_list is overwritten again? WHY??? How does it relate to the previous logic? Why not check for this first and otherwise use default?
        # check if there's vocab in the Names column that needs to be used
        # info in the Names column always overrides vocab that would otherwise be used
        if "Names" in frame_cols:
            custom_defined_names = the_frames.Names[i]
            if len(custom_defined_names) > 1:
                names_list, other_names_list = get_words_from_string(custom_defined_names)
        else:  # still need to initialize this variable if it's one of the cats w/out "Names"
            custom_defined_names = ""

        # -- NOTE: Then check if the names used should instead be real names -- #
        # -- Shouldn't it rather be either or? -- #
        # Determine if  NAME1 and NAME2 needs to be a proper name or not
        needs_proper_name = "Proper_nouns_only" in frame_cols and the_frames.Proper_nouns_only[i] == "TRUE"
        # check if this one needs to use proper names
        if needs_proper_name:
            # what to do if this is part of the race_ethnicity subset
            # this needs to pull from the set of first names that have ethnicity information about them
            if category == "Race_ethnicity":
                if len(bias_targets) >= 1:
                    first_names_full = names_vocab[names_vocab.First_last == "first"]
                    first_names = first_names_full[
                        first_names_full.ethnicity.isin(bias_targets)
                    ]
                else:
                    first_names = names_vocab[names_vocab.First_last == "first"]
                names_list = first_names.Name.tolist()
                names_list = random.sample(names_list, 5)  # for downsampling
            # what to do if this is part of the gender_identity subset
            # this needs to pull from the set of first names that do not have ethnicity information
            elif category == "Gender_identity":
                first_names = names_vocab[names_vocab.First_last == "first_only"]
                # specify female so that the other NAME variable can be set to male and there's always a contrast
                female_first_names = first_names[first_names.gender == "F"]
                names_list = female_first_names.Name.tolist()
                names_list = random.sample(names_list, 5)  # for downsampling
            # a handful of templates in other categories use proper nouns
            # these don't have to be specific to gender, but should not be ethnically identifying, so pull from the
            # subset that doesn't correlate strongly to one racial/ethnic category
            else:
                first_names = names_vocab[names_vocab.First_last == "first_only"]
                names_list = first_names.Name.tolist()
                names_list = random.sample(names_list, 6)  # for downsampling

        # -- NOTE: Loop over main word list (subjects) -- #
        # iterate over each word in word_list
        for name in names_list:
            # initialize variables for later
            Name1_info = None
            Name2_info = None
            random_word_1 = ""
            random_word_2 = ""
            Name2_info_dict = {}

            # - NOTE: ... - #
            # only create new_word_list here if it wasn't already created through Names column
            if len(custom_defined_names) < 2: # TODO: why check for len < 2? This is a string, not a list
                if (len(bias_targets) > 0) and (category in NEED_STEREOTYPING_SUBSET):
                    other_names_list = [
                        n for n in possible_names_list if n not in bias_targets # TODO: Why is not word_list used here?
                    ]
                    if len(other_names_list) > 4:
                        other_names_list = random.sample(
                            other_names_list, 5
                        )  # downsample when needed
                else:
                    other_names_list = [n for n in names_list if n != name]

                # - NOTE: The other_names_list is retrieved for the special cases  - #
                # for SES, need to check to make sure it's grabbing from the other (low/high) category
                if category == "SES" and not needs_proper_name:
                    Name1_info = relevant_vocab.loc[relevant_vocab["Name"] == name, "Info"].iloc[0]
                    new_options = relevant_vocab[relevant_vocab.Info != Name1_info] # TODO: why use "words" here and not "new_word_list"?
                    other_names_list = new_options.Name.unique().tolist()
                # for gender, keep track of gender of the name picked and select a name of a different gender for the
                # second name variable
                if category == "Gender_identity" and needs_proper_name:
                    Name1_info = first_names.loc[first_names["Name"] == name, "gender"].iloc[0]
                    new_options = first_names[first_names.gender != Name1_info]
                    other_names_list = new_options.Name.unique().tolist()
                    other_names_list = random.sample(other_names_list, 5)  # for downsampling
                # for race/ethnicity...
                if category == "Race_ethnicity" and needs_proper_name:
                    # keep track of gender and ethnicity of the name in question
                    the_word_gender = first_names.loc[first_names["Name"] == name, "gender"].iloc[0]
                    the_word_eth = first_names.loc[first_names["Name"] == name, "ethnicity"].iloc[0]
                    Name1_info = the_word_gender + "-" + the_word_eth
                    # select a last name that matches ethnicity, then put them together
                    last_names = names_vocab[
                        (names_vocab.First_last == "last")
                        & (names_vocab.ethnicity == the_word_eth)
                    ]
                    last_names_list = last_names.Name.unique().tolist()
                    this_last_name = random.choice(last_names_list)
                    name = name + " " + this_last_name
                    # create a list of names for the second name var w/ same gender
                    # but ethnicity that's not one of the bias targets for that template
                    other_first_names = first_names_full[
                        (~first_names_full.ethnicity.isin(bias_targets))
                        & (first_names_full.gender == the_word_gender)
                    ].reset_index()
                    other_first_names = other_first_names.sample(
                        n=5, replace=False
                    ).reset_index()  # for downsampling
                    other_last_names = names_vocab[
                        (names_vocab.First_last == "last")
                        & (~names_vocab.ethnicity.isin(bias_targets))
                    ].reset_index()
                    # initialize list and dict to keep track of the second name variables to create
                    other_names_list = []
                    Name2_info_dict = {}
                    for nam in range(len(other_first_names)):
                        frst = other_first_names.Name[nam]
                        eth = other_first_names.ethnicity[nam]
                        gen = other_first_names.gender[nam]
                        Name2_info = gen + "-" + eth
                        lst_list = (
                            other_last_names[other_last_names.ethnicity == eth]
                            .Name.unique()
                            .tolist()
                        )
                        lst = random.choice(lst_list)
                        other_names_list.append(frst + " " + lst)
                        Name2_info_dict[frst + " " + lst] = Name2_info

            # - NOTE: Now start the iteration where you loop over the other names, fill the templates and write to jsonl file - #
            # iterate over each word in the second word list
            # results in full pairings of every possible vocab pair within the subset
            for k in range(len(other_names_list)):
                this_word_2 = other_names_list[k]
                # TODO: Why does this happen here?
                this_frame_row = the_frames.iloc[[i]].reset_index()
                lex_div = this_frame_row.Lexical_diversity[0]

                # Only need to create these values when there's text in lexical diversity
                if lex_div:
                    wrdlist1, wrdlist2 = get_words_from_string(lex_div)
                    random_word_1 = random.choice(wrdlist1)
                    if len(wrdlist2) > 1:  # sometimes there's not a WORD2
                        random_word_2 = random.choice(wrdlist2)

                # NOTE: Fill the template row #
                # replace frame text info with value of {{NAME}} and {{WORD}}. Check the value for each column
                new_frame_row = do_slotting(
                    this_frame_row,
                    frame_cols,
                    name,
                    None,
                    this_word_2,
                    None,
                    lex_div,
                    random_word_1,
                    random_word_2,
                    lang=LANGUAGE,
                )
                # Apply extra NAME slots (e.g., Norwegian definite forms like {{NAME1b}}/{{NAME2b}})
                new_frame_row = _apply_extra_name_slots(new_frame_row, relevant_vocab, name, this_word_2)

                # NOTE: Retrieve data info #
                # need to record info about the names that were used for easier analysis later
                if (
                    Name1_info
                    and category == "Race_ethnicity"
                    and needs_proper_name
                ):
                    Name2_info = Name2_info_dict[this_word_2]
                elif category == "Gender_identity" and needs_proper_name:
                    try:
                        Name2_info = first_names.loc[
                            first_names["Name"] == this_word_2, "gender"
                        ].iloc[0]
                    except IndexError:
                        Name2_info = this_word_2
                    if this_frame_row.NAME1_info[0] != "":
                        # in some cases, there info both from the name selected and info tracked in an info column
                        # in the template. Need to save both of these pieces of info
                        if k == 0:
                            Name1_info = this_frame_row.NAME1_info[0] + "_" + Name1_info
                        Name2_info = this_frame_row.NAME2_info[0] + "_" + Name2_info
                elif category == "Nationality" or (
                    category == "SES" and this_subcat == "Occupation"
                ):
                    # need to get the relevant info about the name from the vocab file
                    Name1_info = vocab.loc[vocab["Name"] == name, "Info"].iloc[0]
                    Name2_info = vocab.loc[vocab["Name"] == this_word_2, "Info"].iloc[0]
                elif "NAME1_info" in frame_cols:
                    # for when the info about the name variables is stored in the templates
                    if this_frame_row.NAME1_info[0] != "":
                        Name1_info = this_frame_row.NAME1_info[0]
                        Name2_info = this_frame_row.NAME2_info[0]
                    else:
                        Name1_info = name
                        Name2_info = this_word_2
                else:
                    # if none of the above apply, just store the info as the actual string used in the name
                    Name1_info = name
                    Name2_info = this_word_2

                print("Passing unknown_options:", UNKNOWN_OPTIONS_NB[:3])

                # NOTE: write to jsonl file #
                # create four sets of data, each as a dictionary
                dat_formatted = create_templating_dicts(
                    category,
                    new_frame_row,
                    this_subcat,
                    UNKNOWN_OPTIONS_NB,
                    frame_cols,
                    bias_targets,
                    name,
                    this_word_2,
                    Name1_info,
                    Name2_info,
                    nn,
                )
                nn += 4
                
                # write to file
                for item in dat_formatted:
                    data_file.write(json.dumps(item, default=str, ensure_ascii=False))
                    data_file.write("\n")
                data_file.flush()

                # NOTE: Here the data is filled with the reversed arguments (if necessary), so that the target and non-target words are swapped in the sentences #
                if (
                    (category in NEED_STEREOTYPING_SUBSET)
                    or needs_proper_name
                    or (category == "SES" and this_subcat == "Occupation")
                ):
                    # flip input of this_word and this_word_2
                    new_frame_row = do_slotting(
                        this_frame_row,
                        frame_cols,
                        this_word_2,
                        None,
                        name,
                        None,
                        lex_div,
                        random_word_1,
                        random_word_2,
                        lang=LANGUAGE,
                    )
                    # Apply extra NAME slots (e.g., Norwegian definite forms like {{NAME1b}}/{{NAME2b}})
                    new_frame_row = _apply_extra_name_slots(new_frame_row, relevant_vocab, this_word_2, name)


                    # create four sets of data, each as a dictionary
                    dat_formatted = create_templating_dicts(
                        category,
                        new_frame_row,
                        this_subcat,
                        UNKNOWN_OPTIONS_NB,
                        frame_cols,
                        bias_targets,
                        this_word_2,
                        name,
                        Name2_info,
                        Name1_info,
                        nn,
                    )
                    nn += 4
                    for item in dat_formatted:
                        data_file.write(json.dumps(item, default=str, ensure_ascii=False))
                        data_file.write("\n")
                    data_file.flush()

        print("generated %s sentences total for %s in file %s" % (str(nn), category, data_file.name))

    data_file.close()