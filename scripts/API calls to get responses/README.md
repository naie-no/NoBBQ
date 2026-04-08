# Retrieving responses

The scripts in this folder are used to retrieve responses from the respective language models, using the datasets.

In the [data](../../data/README.md) dir, there is a folder per category. Within each category folder, you will find a `/1. Data prep/` folder which contains the jsonl file retrieved for the respective category by running the [template_to_jsonl](../../scripts/template_to_jsonl/README.md) script. These are the dataset files used when running the scripts that retrieve the responses.

## How to use the scripts

The scripts (one per language model) expect 2 mandatory input params and 2 optional input params:

- jsonl_path $\rightarrow$ Mandatory param (1st position). Path to the JSONL file containing prompts (jsonl file).
- output_excel_path $\rightarrow$ Mandatory param (2nd position). Path to save the output Excel file.
- --model $\rightarrow$ Optional param (flag). Which language model version to use. For Gemini this is set to `gemini-3-flash-preview` and for GPT this is set to `gpt-5.4-mini`.
- --max-lines $\rightarrow$ Optional param (flag). "Maximum number of lines to process. If set to `None`, all lines will be processed. Default value is `None`. This param is useful for testing purposes.

Example (from root) with no flags:

```
python "scripts/API calls to get responses/jsonl_prompts_to_answers_gpt.py" "data/nationality/1. Data prep/Nationality_nb.jsonl" "data/nationality/2. Prompts and responses/Nationality_Prompts_nb_100_GPT5dot4mini_temp0_noReasoning_max3sentences.xlsx"
```

Example (from root) with flags:

```
python "scripts/API calls to get responses/jsonl_prompts_to_answers_gpt.py" "data/nationality/1. Data prep/Nationality_nb.jsonl" "data/nationality/2. Prompts and responses/Nationality_Prompts_nb_100_GPT5pro_temp0_noReasoning_max3sentences.xlsx" --model gpt-5-pro --max-lines 2
```

**Please make sure to provide a descriptive name to the response file, as you see in the examples.**

_Note:_ The quotation marks ("") are necessary when providing a path which has whitespace in it

### Settings

#### Hardcoded

The language models are all run with temperature 0, no/minimal reasoning, and a system prompt defining that max 3 sentences should be used to respond to the prompt. This is to ensure a fair comparison and results that are not the product of a models internal reasoning. We to not wish to direct the model towards how to respond, only to respond briefly to save tokens.

#### Modifiable

It is possible to decide which model version should be used when running the script. **HOWEVER:** For now we ask you to get approval from Wessel Braakman before you use any other models than the default. This is because the cost is paid out of pocket and we need to have control of the budget.

---

## License

© Norsk AI-Etikkforening (NAIE) 2025

- **Code** is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
- **Datasets, documentation, and research outputs** are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

You are free to use and adapt this work with proper attribution.  
Logo and name are trademarks of Norsk AI-Etikkforening and are not covered by these licenses.

---
