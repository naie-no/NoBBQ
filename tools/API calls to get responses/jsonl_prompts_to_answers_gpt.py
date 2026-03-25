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
load_dotenv()

DEFAULT_MODEL = "gpt-5.4-mini"
SYSTEM_PROMPT = "Svar med maks tre setninger."
MAX_LINES = None  # Set to a number to limit the number of lines processed, or None to process all lines.

def process_prompts(jsonl_path: str, output_excel_path: str, model: str, max_lines: int):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    df = pd.DataFrame(columns=["Prompt", "Answer"])

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
                response = client.responses.create(
                    model=model,
                    instructions=SYSTEM_PROMPT,
                    reasoning={"effort": "none"},
                    temperature=0.0,
                    input=prompt
                )
                print("Adding response to dataframe")
                answer = response.output_text
                df.loc[len(df)] = [prompt, answer]

                counter += 1
            except Exception as e:
                print(f"Error processing line {counter}: {e}")
                break

    # Save prompt and answer to a new Excel file
    try:
        print(f"Writing dataframe with {len(df)} rows to Excel")
        df.to_excel(output_excel_path, index=False)
        print(f"Completed writing to Excel at {output_excel_path}")
    except Exception as e:
        print(f"Error writing to Excel file: {e}")

    # Close client to free resources
    client.close()

def main(args):
    process_prompts(args.jsonl_path, args.output_excel_path, args.model, args.max_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path", type=str, help="Path to the JSONL file containing prompts")
    parser.add_argument("output_excel_path", type=str, help="Path to save the output Excel file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-lines", type=int, default=MAX_LINES, help=f"Maximum number of lines to process. If 'None', all lines will be processed. (default: {MAX_LINES})")
    args = parser.parse_args()

    main(args)