import os
import time
import argparse
import jsonlines
import pandas as pd
from google import genai
from google.genai import types
from google.genai import errors
from dotenv import load_dotenv
from utils import *

load_dotenv()

DEFAULT_MODEL = "gemini-3-flash-preview"
SYSTEM_PROMPT = "Svar med maks tre setninger."

MAX_LINES = None  # Set to a number to limit the number of lines processed, or None to process all lines.

def process_prompts(jsonl_path: str, model: str, max_lines: int):
    '''
    Retrieves prompts from a JSONL file, sends them to the GEMINI API, and collects the prompts and responses in a DataFrame.

    Args:
        jsonl_path (str): The path to the JSONL file containing the info to construct the prompts ('context' and 'question' fields).
        model (str): The GEMINI model to use for generating responses.
        max_lines (int): The maximum number of lines to process. If 'None', all lines will be processed.

    Returns:
        pd.DataFrame: A DataFrame containing the prompts and their corresponding responses.
    '''

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    thinking_config = get_thinking_config(model)
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

                try:
                    print(f"Retrieve response from Gemini with {model}")
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig( # https://googleapis.github.io/python-genai/genai.html#genai.types.GenerateContentConfig
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.0,
                            thinking_config=thinking_config
                        )
                    )
                except errors.ClientError as e:
                    if e.code == 429:
                        print(f"Rate limit exceeded when processing line {counter}. Waiting for 60 seconds before retrying...")
                        time.sleep(60) # This will avoid the rate per minute limit
                        
                        # Retry the request after waiting
                        print(f"Retrying retrieving response from Gemini with {model}")
                        response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig( # https://googleapis.github.io/python-genai/genai.html#genai.types.GenerateContentConfig
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.0,
                            thinking_config=thinking_config
                        )
                    )
                        
                    else:
                        print(f"Client error when processing line {counter}: {e}")
                        raise Exception(f"Client error: {e}")

                print("Adding response to dataframe")    
                answer = response.text
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

def get_thinking_config(model: str):
    # setting thinking config based on model version, as per https://ai.google.dev/gemini-api/docs/thinking
    # docs on ThinkingConfig: https://googleapis.github.io/python-genai/genai.html#genai.types.ThinkingConfig
    if "2.5" in model:
        thinking_config = types.ThinkingConfig(
            thinking_budget=0
        )
    elif "3" in model:
        thinking_config = types.ThinkingConfig(
            thinking_level='MINIMAL' # https://googleapis.github.io/python-genai/genai.html#genai.types.ThinkingLevel
        )
    else:
        thinking_config = None

    print(f"\nThinking config: {thinking_config}\n")
    return thinking_config

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
