import os
import argparse
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
MAX_LINES = None  # Set to a number to limit the number of lines processed, or None to process all lines.
MODEL_FOLDERS = {
    "gpt" : "ChatGPT",
    "gemini" : "Gemini",
    "mistral" : "Mistral/Responses"
}

MODEL_PATH_STRINGS = {
    "gpt-4o" : "GPT4o",
    "gpt-5.4-mini" : "GPT5dot4mini",
    "gemini-2.5-flash" : "Gemini2dot5flash",
    "gemini-3-flash-preview" : "Gemini3flashPreview",
    # TODO: Add mistral
}

def process_responses(responses: dict[str, pd.DataFrame], category: str, models: list[str]):
    ...


def main(args):
    responses = load_responses(args.category, args.models)

    process_responses(responses, args.category, args.models)


def load_responses(category: str, models: list[str]):
    category_responses_dir = f"data/{category.lower().strip()}/2. Prompts and responses"
    
    responses = {}
    for model in models:
        model_lower = model.lower().strip()
        model_system = model_lower.split("-")[0] # TODO: might not work with mistral!

        for file in os.listdir(f"{category_responses_dir}/{MODEL_FOLDERS[model_system]}"):
            if MODEL_PATH_STRINGS[model_lower] in file:
                file_path = f"{category_responses_dir}/{MODEL_FOLDERS[model_system]}/{file}"
        responses[model_lower] = file_path

    return responses
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("category", type=str, help="The category to process")
    parser.add_argument("models", nargs="+", type=str, help="The models to process")
    parser.add_argument("output_excel_path", type=str, help="Path to save the output Excel file")
    parser.add_argument("--max-lines", type=int, default=MAX_LINES, help=f"Maximum number of lines to process per results file. If 'None', all lines will be processed. (default: {MAX_LINES})")
    #parser.add_argument("-a", "--append-from-end", action="store_true", help="Flag used if you wish to continue to read jsonl lines from the last read line (only possible if \'output_excel_path\' already exists)")
    args = parser.parse_args()

    main(args)