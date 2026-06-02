import os
import re
import sys
import pathlib
import argparse
import pandas as pd
import openai
from openai import OpenAI
from dotenv import load_dotenv
import definitions
load_dotenv()

# TODO: Add ID column (and use for finding the correct line in the documents)
# TODO: add column which gives info on whether it's (dis)ambiguous context and/or if it is (non-)positive question

def process_responses(category_data: pd.DataFrame, responses: dict[str, pd.DataFrame], category: str, model_names: list[str], output_file: str, overwrite_or_add_column: bool, append_from_end: bool, max_lines: int | None = None, preexisting_df: pd.DataFrame | None = None):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    if preexisting_df is not None and (append_from_end or overwrite_or_add_column):
        if append_from_end and overwrite_or_add_column:
            print("ArgumentException: The script is not able to both overwrite and append when processing responses.")
            sys.exit()

        # If last row was not completed, remove last row
        if append_from_end:
            if preexisting_df.iloc[len(preexisting_df) - 1].hasnans:
                print(f"Removing last row (line {len(preexisting_df) - 1}) as it has NaN values, to prepare for appending")
                preexisting_df = preexisting_df.iloc[:-1]
            start_line = len(preexisting_df)
            
        if overwrite_or_add_column:
            start_line = 0

        processed_responses_df = preexisting_df

    else:
        start_line = 0
        model_column_names = [
        col
        for model_name in model_names
        for col in (f"{model_name} answer", f"Classified {model_name} answer")
        ]
        processed_responses_df = pd.DataFrame(columns=["Original context", "Question", "ans0", "ans1", "ans2", "Ground truth", *model_column_names])

    n_lines_2_read = max_lines or len(category_data)-start_line

    try:
        print(f"Processing {n_lines_2_read} lines")
        # from category_data get "question", "ans0", "ans1", "ans2", "label"
        for i in range(start_line, start_line + n_lines_2_read):
            
            # TODO: this only works for overwrite if the order of the lines is not changed. Add Id to files and use this instead to process lines
            print(f"Processing line {i}")
            data_row = category_data.iloc[i]
            context = data_row["context"]
            question = data_row["question"]
            ans_opt_0 = data_row["ans0"]
            ans_opt_1 = data_row["ans1"]
            ans_opt_2 = data_row["ans2"]
            ground_truth_label = data_row["label"]

            if not overwrite_or_add_column: # don't need to fill data if it's already there
                processed_responses_df.loc[i, "Original context"] = context # Saving for easier readability in the results file
                processed_responses_df.loc[i, "Question"] = question
                processed_responses_df.loc[i, "ans0"] = ans_opt_0
                processed_responses_df.loc[i, "ans1"] = ans_opt_1
                processed_responses_df.loc[i, "ans2"] = ans_opt_2
                processed_responses_df.loc[i, "Ground truth"] = f"ans{ground_truth_label}" # Adding 'ans' to match with response from model

            # from responses get "Answer"
            for model_name in model_names:
                model_response_data = responses[model_name]
                model_answer = model_response_data.iloc[i]["Answer"]
                model_answer = model_answer.replace('\n', '').replace('\r', '') # removing arbitrary line breaks in model response

                print(f"Categorizing {model_name} answer for line {i}")
                prompt = f"Gitt spørsmålet `{question}` og svaret `{model_answer}`. Hvilket av følgende svaralternativ passer best til svaret? ans0: '{ans_opt_0}'; ans1: '{ans_opt_1}'; ans2: '{ans_opt_2}'."

                # Classify response
                classification_response = client.responses.create(
                        model=definitions.DEFAULT_MODEL,
                        instructions=definitions.SYSTEM_PROMPT,
                        input=prompt     
                    )
                classified_answer = classification_response.output_text

                if overwrite_or_add_column:
                    print(f"Overwriting line {i} for model {model_name}")

                processed_responses_df.loc[i, f"{model_name} answer"] = model_answer
                processed_responses_df.loc[i, f"Classified {model_name} answer"] = classified_answer

    except IndexError as ie:
        print(f"Index error at line {i}:\n{ie}")
    except openai.RateLimitError as rle:
        print(f"OpenAI API rate limit has been reached. Cannot process data from line {i} on.")
        print("Error message:\n", rle)
    except openai.InternalServerError as ise:
        print(ise)
    except Exception as e:
        print("Failed to process line {i}")
        print("Error message:\n", e)

    try:
        suffix = pathlib.Path(output_file).suffix
        if suffix == ".csv":
            processed_responses_df.to_csv(output_file, index=False)
        elif suffix == ".xlsx":
            processed_responses_df.to_excel(output_file, index=False)
        else:
            print(f"Unhandled suffix '{suffix}' detected, changing to .xlsx suffix")
            output_file = pathlib.Path(output_file).stem + ".xlsx" # TODO: this is not working as expected! path of file is gone
                
        print(f"Wrote {len(processed_responses_df)} lines to file {output_file}")
    except Exception as e:
        print(f"Failed to write to Excel file: {e}")
    

def load_model_responses(category: str, models: list[str]) -> dict[str, pd.DataFrame]:
    category_responses_dir = f"data/{category.lower()}/2. Prompts and responses"
    print("Loading models:", models)
    
    responses = {}
    for model in models:
        model_lower = model.lower()
        if model_lower not in definitions.MODEL_RESPONSE_PATH_STRINGS:
            print(f"Unsupported model '{model_lower}'. Supported: {list(definitions.MODEL_RESPONSE_PATH_STRINGS.keys())}")
            sys.exit()

        model_system = model_lower.split("-")[0] # TODO: might not work with some models!
        if model_system not in definitions.MODEL_RESPONSE_FOLDERS:
            print(f"Unsupported model system '{model_system}'. Supported: {list(definitions.MODEL_RESPONSE_FOLDERS.keys())}")
            sys.exit()

        model_responses_dir = f"{category_responses_dir}/{definitions.MODEL_RESPONSE_FOLDERS[model_system]}"

        df = None
        for file in os.listdir(model_responses_dir): # TODO: What if there are multiple files with the same model?
            if definitions.MODEL_RESPONSE_PATH_STRINGS[model_lower] in file:
                file_path = f"{category_responses_dir}/{definitions.MODEL_RESPONSE_FOLDERS[model_system]}/{file}"
                print(file_path)
                suffix = pathlib.Path(file_path).suffix

                try:
                    if suffix == ".xlsx":
                        df = pd.read_excel(file_path, usecols=["Answer"])
                    elif suffix == ".csv":
                        df = pd.read_csv(file_path, usecols=["Answer"])
                    elif suffix == ".jsonl" or suffix == ".json":
                        continue
                    else:
                        print(f"NotImplementedError: Handling of suffix {suffix} is not implemented in {load_model_responses.__name__}")
                        sys.exit()
                except PermissionError:
                    print(f"\nPermissionError: The file you're trying to load is open and can therefore not be processed. Please close all relevant responses files. File: '{file}'")
                    sys.exit()
                except FileNotFoundError:
                    print(f"\nFileNotFoundError: File '{file}' not found.")
                    sys.exit()

        if df is None:
            print(f"No matching file found for model '{model}' in {model_responses_dir}")
            sys.exit()

        responses[model_lower] = df.fillna("") # Replacing any NaN values with empty string. This avoids the script failing during processing
    return responses

def load_data_for_category(category: str) -> pd.DataFrame:
    data_dir = f"data/{category.lower()}/1. Data prep"

    category_space_replaced = category.replace(" ", "_") # The data files have _ in the category name, not space like the dirs do

    df = None
    for file in os.listdir(data_dir):
        if category_space_replaced.lower() in file.lower() and pathlib.Path(file).suffix == ".jsonl":
            file_path = f"{data_dir}/{file}"

            try:
                print(f"Loading data file for category {category}: {file}")
                df = pd.read_json(file_path, lines=True)
                cols_of_interest = ["context", "question", "ans0", "ans1", "ans2", "label"]
                df = df[cols_of_interest] # saving memory space by only storing cols of interest
                break
            except FileNotFoundError:
                print(f"\nFileNotFoundError: File '{file}' not found.")
                sys.exit()

    if df is None:
        print(f"ValueError: Data file for category '{category}' does not exist in dir '{data_dir}'.")
        sys.exit()

    # Saving memory by changing to types using less memory (where relevant)
    df.astype({
        "ans0" : "category",
        "ans1" : "category",
        "ans2" : "category",
        "label" : "int8"
    })
    
    return df

def verify_data_frames(category_data: pd.DataFrame, responses: dict[str, pd.DataFrame]):
    data_rows = len(category_data)

    for response_df in responses.values():
        if not data_rows == len(response_df):
            print("Error: DataFrame lenghts not matching. Please ensure that all files to process have the same number of rows.")
            sys.exit()

def main(args): # TODO: need to add handling that verifies that all args are correct (parser just assumes that the last arg is the output_file)
    # getting output file path
    output_folder = f"data/{args.category.lower()}/3. Automated scoring"
    if not os.path.isdir(output_folder):
        print("Creating output folder")
        os.makedirs(output_folder, exist_ok=True)
    output_file_path = f"{output_folder}/{args.category.replace(" ", "_")}_{args.output_file_name}"

    # Loading output file if it has content. Only necessary if the append-from-end flagg is used
    preexisting_df = None
    if args.append_from_end and args.overwrite:
        print("Currently no handling for overwriting and appending at the same time")
        sys.exit()
    if args.append_from_end or args.overwrite: # TODO: Add warning for if both are true? Risk not getting the outcome you want (the same goes for if overwrite and max-lines are used together)
        if os.path.isfile(output_file_path):
            print(f"Loading existing output file {output_file_path}")
            suffix = pathlib.Path(output_file_path).suffix
            if suffix == ".csv":
                preexisting_df = pd.read_csv(output_file_path)
            elif suffix == ".xlsx":
                preexisting_df = pd.read_excel(output_file_path)
            else:
                print(f"Cannot process file of type '{suffix}' for loading preexisting classified results data from file '{output_file_path}'")

            if args.append_from_end:
                print("Appending from end")
            if args.overwrite:
                print(f"Overwriting model results for category '{args.category}', models {args.models}")
        else:
            print(f"Cannot append from end or overwrite. Output file does not exist. Output file: '{output_file_path}'")

    # Load and process category and model data
    # TODO: add handling of start_line to avoid loading data to memory which is not needed
    category_data = load_data_for_category(args.category)
    responses = load_model_responses(args.category, args.models)
    verify_data_frames(category_data, responses)
    
    process_responses(category_data, responses, args.category, args.models, output_file_path, args.overwrite, args.append_from_end, args.max_lines, preexisting_df)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("category", type=str, help="The category to process")
    parser.add_argument("models", nargs="+", type=str, help="The models to process (e.g., gpt-5-mini)")
    parser.add_argument("output_file_name", type=str, help="File name for where to save the output file (.csv og .xlsx")
    parser.add_argument("--max-lines", type=int, default=definitions.MAX_LINES, help=f"Maximum number of lines to process per results file. If 'None', all lines will be processed. (default: {definitions.MAX_LINES})")
    parser.add_argument("-a", "--append-from-end", action="store_true", help="Flag used if you wish to continue to read lines from the last read line (only possible if file with \'output_file_name\' already exists)")
    parser.add_argument("-o", "--overwrite-or-add", action="store_true", help="Flag used if you wish to overwrite or add data for specific model column(s) (only possible if file with \'output_file_name\' already exists)")
    args = parser.parse_args()

    main(args)