# This is a temp file to make sure that the results file for mistral responses is correct for the scoring step
import os
import pathlib
import argparse
import jsonlines
import pandas as pd

def main(args):
    file_path = f"data/{args.category}/2. Prompts and responses/Mistral/PrelimResponses/{args.responses_file}"

    df = pd.DataFrame(columns=["Id", "Answer"])

    # OBS: assuming JSONL file type
    with jsonlines.open(file_path) as jsonl_reader:
        for i, line in enumerate(jsonl_reader):
            print("Processing line ", i)
            id = line["custom_id"]
            response = line["response"]["body"]["choices"][0]["message"]["content"]
            df.loc[len(df)] = [id, response]

    print(f"Sorting {len(df)} based on Id column")
    df["Id"] = df["Id"].astype(int)
    df = df.sort_values(by="Id")

    output_file = pathlib.Path(args.responses_file).stem + ".xlsx"
    #output_file = pathlib.Path(args.responses_file).stem + ".csv"
    responses_output_folder = f"data/{args.category}/2. Prompts and responses/Mistral/Responses"
    if not os.path.isdir(responses_output_folder):
        print("Creating output folder")
        os.makedirs(responses_output_folder, exist_ok=True)
    
    responses_file_path = f"{responses_output_folder}/{output_file}"

    print("Saving to ", responses_file_path)
    #df.to_csv(responses_file_path, index=False)
    df.to_excel(responses_file_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("category", type=str, help="The category to process")
    parser.add_argument("responses_file", type=str, help="The responses file to process")

    args = parser.parse_args()
    main(args)