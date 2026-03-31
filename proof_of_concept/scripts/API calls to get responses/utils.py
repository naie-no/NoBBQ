import os
import pathlib
import pandas as pd

def verify_paths(jsonl_file_path: str, output_excel_path: str) -> bool:
    '''
    Verifies that the specified JSONL file path and output Excel file path are valid.
    
    Checks that the JSONL file exists, the directory for the output Excel file exists, and that the output file has an .xlsx extension.
    '''
    exists = True
    if not os.path.isfile(jsonl_file_path):
        print(f"JSONL file '{jsonl_file_path}' does not exist.")
        exists = False
    
    if not os.path.isdir(os.path.dirname(output_excel_path)):
        print(f"Directory for output Excel file '{os.path.dirname(output_excel_path)}' does not exist.")
        exists = False

    if not pathlib.Path(output_excel_path).suffix == ".xlsx":
        print(f"Output file '{output_excel_path}' does not have an .xlsx extension.")
        exists = False
    
    return exists

def write_df_to_excel(df : pd.DataFrame, output_excel_path : str):
    try:
        print(f"Writing dataframe with {len(df)} rows to Excel")
        df.to_excel(output_excel_path, index=False)
        print(f"Completed writing to Excel at {output_excel_path}")
    except Exception as e:
        print(f"Failed to write to Excel file: {e}")