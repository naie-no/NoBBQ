# Generating the dataset

The dataset is created as multiple jsonl files (one per category), based on the [templates](../../templates/). To create the dataset, the script needs to be run per category.

## How to use the script

Run the script from the root directory

We use the following script for Norsk Bokmål:

```
python scripts/template_to_jsonl/generate_from_template_all_categories_lang_utf8_nb.py
```

The script utilizes one or more `./templates/<<CATEGORY_NAME>>_nb.csv` file(s) to create context/question files in the `./data/<<CATEGORY_NAME>>/1. Data prep/` folder.
Make sure the template .csv files are ready, comma-separated or semicolon separated, and utf-8 encoded. If the .csv files do not adhere to these restrictions, the script will fail.

**All possible categories**

```py
cats = [
"Disability_status",
"Age",
"Physical_appearance",
"SES",
"Gender_identity",
"Race_ethnicity",
"Religion",
"Nationality",
"Sexual_orientation",
]
```

> _**NOTE**: Make sure to comment out the categories you don't wish to generate before running the script. This is in particular useful for testing._
> _**NOTE2**: For now only "Age", "Gender identity", "Religion", and "Nationality" are included in the Norsk Bokmål (NB) dataset_

**When running the script, you should see the following output in the terminal (example Gender_identity):**

```
C:\Users\wesselb\dev\NoBBQ>set python scripts/template_to_jsonl/generate_from_template_all_categories_lang_utf8_nb.py
generated 8 sentences total for Gender_identity
generated 16 sentences total for Gender_identity
generated 24 sentences total for Gender_identity
generated 32 sentences total for Gender_identity
generated 40 sentences total for Gender_identity
generated 48 sentences total for Gender_identity
generated 52 sentences total for Gender_identity
generated 56 sentences total for Gender_identity
generated 64 sentences total for Gender_identity
generated 72 sentences total for Gender_identity
```

If any issues with the script arise, feel free to contact us.

---

## License

© Norsk AI-Etikkforening (NAIE) 2025

- **Code** is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
- **Datasets, documentation, and research outputs** are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

You are free to use and adapt this work with proper attribution.  
Logo and name are trademarks of Norsk AI-Etikkforening and are not covered by these licenses.

---
