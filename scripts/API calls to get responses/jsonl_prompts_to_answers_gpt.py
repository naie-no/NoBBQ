"""
Reads a JSONL file containing prompts, sends them to the OpenAI API, and saves the responses in a Excel file.
The JSONL file used has been created by the "generate_from_template..." file.
"""
import os
import argparse
import jsonlines
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from utils import *

load_dotenv()

DEFAULT_MODEL = "gpt-5.4-mini"
SYSTEM_PROMPT = "Svar med maks tre setninger."
MAX_LINES = None  # Set to a number to limit the number of lines processed, or None to process all lines.

def process_prompts(jsonl_path: str, model: str, max_lines: int) -> pd.DataFrame:
    '''
    Retrieves prompts from a JSONL file, sends them to the OpenAI API, and collects the prompts and responses in a DataFrame.

    Args:
        jsonl_path (str): The path to the JSONL file containing the info to construct the prompts ('context' and 'question' fields).
        model (str): The GPT model to use for generating responses.
        max_lines (int): The maximum number of lines to process. If 'None', all lines will be processed.

    Returns:
        pd.DataFrame: A DataFrame containing the prompts and their corresponding responses.
    '''

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    df = pd.DataFrame(columns=["Prompt", "Answer"])
    
    # Reasoning is for gpt-5 and o-series models only (see docs)
    reasoning_setting = {"effort": "none"} if "gpt-5" in model or model.startswith("o") else None
    print("Reasoning:", reasoning_setting)

    counter = 0
    print(f"Starting to read file \'{jsonl_path}\'")
    with jsonlines.open(jsonl_path) as jsonl_reader:
        for line in jsonl_reader:
            try:
                if counter == max_lines:
                    break

                print(f"Read line {counter}")
                context = line["context"]
                question = line["question"]
                prompt = context + " " + question

                print(f"Retrieve response from OpenAI with {model}")
                # Docs: https://developers.openai.com/api/reference/resources/responses/methods/create
                response = client.responses.create(
                    model=model,
                    instructions=SYSTEM_PROMPT,
                    reasoning=reasoning_setting,
                    temperature=0.0,
                    input=prompt     
                )
                print("Adding response to dataframe")
                answer = response.output_text
                df.loc[len(df)] = [prompt, answer]

                counter += 1

                # reset prompt and response to avoid accidentally carrying over values in case of an error in the next iteration
                prompt = ""
                response = None
                
            except Exception as e:
                print(f"Error processing line {counter}: {e}")
                break

    # Close client to free resources
    client.close()
    return df

def main(args):
    paths_valid, verified_paths = verify_paths(args.jsonl_path, args.output_excel_path)
    if not paths_valid:
        print("One or more specified paths is incorrect. Please check the paths and try again.")
        return
    
    df = process_prompts(verified_paths["jsonl_path"], args.model, args.max_lines)
    write_df_to_excel(df, verified_paths["output_excel_path"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path", type=str, help="Path to the JSONL file containing prompts")
    parser.add_argument("output_excel_path", type=str, help="Path to save the output Excel file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-lines", type=int, default=MAX_LINES, help=f"Maximum number of lines to process. If 'None', all lines will be processed. (default: {MAX_LINES})")
    args = parser.parse_args()

    main(args)