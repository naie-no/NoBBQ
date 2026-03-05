import json

input_file = "./data_nb/Age.jsonl"
output_file = "./data_nb/Age.json"

data = []

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        data.append(json.loads(line))

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)