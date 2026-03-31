import pandas as pd
import json

# Path to the JSONL file
jsonl_file = "Religion_Original.jsonl"  # Replace with your file path
output_excel = "Religion_Original_Excel.xlsx"  # Output Excel file name

# Read JSONL file
data_list = []
with open(jsonl_file, 'r', encoding='utf-8') as file:
    for line in file:
        data_list.append(json.loads(line))

# Convert to DataFrame
df = pd.DataFrame(data_list)

# Save to Excel
df.to_excel(output_excel, index=False)
print(f"File converted successfully to {output_excel}")
