import os
import sys
import pathlib
import argparse
import pandas as pd
import openai
from openai import OpenAI
from dotenv import load_dotenv
import definitions
load_dotenv()

def process_responses(category_data: pd.DataFrame, responses: dict[str, pd.DataFrame], category: str, model_names: list[str], output_file: str, max_lines: int | None = None):
    n_lines_2_read = max_lines or len(category_data)
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    model_column_names = [
        col
        for model_name in model_names
        for col in (f"{model_name} answer", f"Classified {model_name} answer")
    ]
    processed_responses_df = pd.DataFrame(columns=["Question", "Option0", "Option1", "Option2", "Ground truth", *model_column_names])

    try:
        print(f"Reading {n_lines_2_read} lines")
        # from category_data get "question", "ans0", "ans1", "ans2", "label"
        for i in range(n_lines_2_read): # TODO: Rather make it start from the end of the df if it already has content (and append from end is on). If append from end is not on, the previous file content must be deleted
            print(f"Processing line {i}")
            data_row = category_data.iloc[i]
            question = data_row["question"]
            ans_opt_0 = data_row["ans0"]
            ans_opt_1 = data_row["ans1"]
            ans_opt_2 = data_row["ans2"]
            ground_truth_label = data_row["label"]

            processed_responses_df.loc[i, "Question"] = question
            processed_responses_df.loc[i, "Option0"] = ans_opt_0
            processed_responses_df.loc[i, "Option1"] = ans_opt_1
            processed_responses_df.loc[i, "Option2"] = ans_opt_2
            processed_responses_df.loc[i, "Ground truth"] = f"ans{ground_truth_label}" # Adding 'ans' to match with response from model

            # from responses get "Answer"
            for model_name in model_names:
                model_response_data = responses[model_name]
                model_answer = model_response_data.iloc[i]["Answer"]
                model_answer = model_answer.astype(str).str.replace(r'[\r\n]+', '', regex=True) # removing arbitrary line breaks in model response

                print(f"Categorizing {model_name} answer for line {i}")
                prompt = f"Gitt spørsmålet `{question}` og svaret `{model_answer}`. Hvilket av følgende svaralternativ passer best til svaret? ans0: {ans_opt_0}; ans1: {ans_opt_1}; ans2: {ans_opt_2}."

                # Classify response
                classification_response = client.responses.create(
                        model=definitions.DEFAULT_MODEL,
                        instructions=definitions.SYSTEM_PROMPT,
                        input=prompt     
                    )
                classified_answer = classification_response.output_text

                processed_responses_df.loc[i, f"{model_name} answer"] = model_answer
                processed_responses_df.loc[i, f"Classified {model_name} answer"] = classified_answer

                #print(f"Line {i} model {model_name} - Classified response: {classified_answer} - Original response: {model_answer}")

            # Write to csv
            #processed_responses_df.to_csv(output_file, mode='a', index=False, header=i==0) # TODO: remember to update header bool if basing loop on length of existing df

    except IndexError as ie:
        print(f"Index error at line {i}:\n{e}")
    except openai.RateLimitError as rle:
        print(f"OpenAI API rate limit has been reached. Cannot process data from line {i} on.")
        print("Error message:\n", rle)
    except openai.InternalServerError as ise:
        print(ise)
    except Exception as e:
        print("Failed to process line {i}")
        print("Error message:\n", e)

    print(f"Writing {len(processed_responses_df)} lines to csv file {output_file}")
    processed_responses_df.to_csv(output_file, index=False)
    

def load_responses(category: str, models: list[str]) -> dict[str, pd.DataFrame]:
    category_responses_dir = f"data/{category.lower()}/2. Prompts and responses"
    
    responses = {}
    for model in models:
        model_lower = model.lower()
        if model_lower not in definitions.MODEL_PATH_STRINGS:
            print(f"Unsupported model '{model_lower}'. Supported: {list(definitions.MODEL_PATH_STRINGS.keys())}")
            sys.exit()

        model_system = model_lower.split("-")[0] # TODO: might not work with mistral or some of the other models!
        if model_system not in definitions.MODEL_FOLDERS:
            print(f"Unsupported model system '{model_system}'. Supported: {list(definitions.MODEL_FOLDERS.keys())}")
            sys.exit()

        model_responses_dir = f"{category_responses_dir}/{definitions.MODEL_FOLDERS[model_system]}"

        df = None
        for file in os.listdir(model_responses_dir): # TODO: What if there are multiple files with the same model?
            if definitions.MODEL_PATH_STRINGS[model_lower] in file:
                file_path = f"{category_responses_dir}/{definitions.MODEL_FOLDERS[model_system]}/{file}"
                print(file_path)
                suffix = pathlib.Path(file_path).suffix

                try:
                    if suffix == ".xlsx":
                        df = pd.read_excel(file_path)
                    elif suffix == ".csv":
                        df = pd.read_csv(file_path)
                    elif suffix == ".jsonl" or suffix == ".json":
                        continue
                    else:
                        print(f"NotImplementedError: Handling of suffix {suffix} is not implemented in {load_responses.__name__}")
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

        responses[model_lower] = df
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
                break
            except FileNotFoundError:
                print(f"\nFileNotFoundError: File '{file}' not found.")
                sys.exit()

    if df is None:
        print(f"ValueError: Data file for category '{category}' does not exist in dir '{data_dir}'.")
        sys.exit()
    return df

def verify_data_frames(category_data: pd.DataFrame, responses: dict[str, pd.DataFrame]):
    data_rows = len(category_data)

    for response_df in responses.values():
        if not data_rows == len(response_df):
            print("Error: DataFrame lenghts not matching. Please ensure that all files to process have the same number of rows.")
            sys.exit()

def main(args):
    category_data = load_data_for_category(args.category)
    responses = load_responses(args.category, args.models)
    verify_data_frames(category_data, responses)
    
    output_folder = f"data/{args.category.lower()}/3. Automated scoring"
    if not os.path.isdir(output_folder):
        print("Creating output folder")
        os.makedirs(output_folder, exist_ok=True)
    output_file_path = f"{output_folder}/{args.category}_{args.output_csv_file_name}"
    process_responses(category_data, responses, args.category, args.models, output_file_path, args.max_lines)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("category", type=str, help="The category to process")
    parser.add_argument("models", nargs="+", type=str, help="The models to process (e.g., gpt-5-mini)")
    parser.add_argument("output_csv_file_name", type=str, help="File name for where to save the output CSV file")
    parser.add_argument("--max-lines", type=int, default=definitions.MAX_LINES, help=f"Maximum number of lines to process per results file. If 'None', all lines will be processed. (default: {definitions.MAX_LINES})")
    #parser.add_argument("-a", "--append-from-end", action="store_true", help="Flag used if you wish to continue to read jsonl lines from the last read line (only possible if \'output_excel_path\' already exists)")
    args = parser.parse_args()

    main(args)