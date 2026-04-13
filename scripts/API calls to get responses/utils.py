import os
import pathlib
import pandas as pd

def verify_paths(jsonl_file_path: str, output_excel_path: str) -> bool:
    '''
    Verifies that the specified JSONL file path and output Excel file path are valid.
    
    Checks that the JSONL file and the directory for the output Excel file exist, and that the output file has an .xlsx extension.
    Added corrections if .jsonl or .xlsx enxtensions are missing.

    Input
    -----
    jsonl_file_path: str
        The file path to the input data
    output_excel_path: str
        The file path to write the output

    Returns
    -------
    A dict containing the jsonl and xlsx paths, who may have been corrected if extension(s) were missing
    '''

    exists = True

    # Check input path
    if not os.path.isfile(jsonl_file_path):
        if os.path.isfile(jsonl_file_path + ".jsonl"):
            jsonl_file_path += ".jsonl"
            print(f"\nMissing file extension for intput JSON file. Adding \'.jsonl\' extension. Current file path: {jsonl_file_path}\n")
        else:
            print(f"\nJSONL file '{jsonl_file_path}' does not exist.\n")
            exists = False
    
    # Check output path (including dir)
    if not os.path.isdir(os.path.dirname(output_excel_path)):
        print(f"\nDirectory for output Excel file '{os.path.dirname(output_excel_path)}' does not exist.\n")
        exists = False

    suffix = pathlib.Path(output_excel_path).suffix
    if not suffix:
        output_excel_path += ".xlsx"
        print(f"\nMissing file extension for output Excel file. Adding \'.xlsx\' extension. Current file path: {output_excel_path}\n")
    elif suffix != ".xlsx":
        print(f"\nOutput file '{output_excel_path}' should have an \'.xlsx\' extension, not \'{suffix}\'.\n")
        exists = False
    
    return exists, {"jsonl_path": jsonl_file_path, "output_excel_path": output_excel_path}

def write_df_to_excel(df : pd.DataFrame, output_excel_path : str):
    try:
        print(f"Writing dataframe with {len(df)} rows to Excel")
        df.to_excel(output_excel_path, index=False)
        print(f"Completed writing to Excel at {output_excel_path}")
    except Exception as e:
        print(f"Failed to write to Excel file: {e}")