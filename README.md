**We are using the following research/repo as a basis for our Norwegian version of the same thing;**
- https://github.com/nyu-mll/BBQ/blob/main/README.md


**This project is initiated by:**
- Wessel Braakman
- Alejandra Palacio Perez
- Teresa Dalen Herland

**Note that this is a PoC type of project, nothing here is set in stone and all conclusions from this project are NOT based on empirical/scientifical evidence.
We start this project, hoping it will trigger interest so we can take this to a more professional level.**

**Steps:**
1. Download raw JSONL files from the original BBQ repository (per category)
2. Filter these files so we end up with approximately 100 unique contexts/questions (per category)
3. Determine whether we can either reuse, change or have to delete the contexts or questions (looking at Norwegian society)
4. Translate the contexts and questions to Norwegian
5. Create prompts (context + questions)
6. Send prompts to various LLM systems (e.g. ChatGPT, Perplexity, Gemini, ...)
7. Document responses
8. Review and score the responses (do they contain bias)
9. Report conclusions

**Progress:**
Progress can be tracked by either
- **Checking our repository regularly**
- **Reading our blogs on Medium:**
- Blog 1: https://medium.com/@wesselbraakman/norwegian-ai-bias-indicator-d6f2b25c02cb
- Blog 2: https://medium.com/@wesselbraakman/norwegian-ai-bias-indicator-pt-2-3d16376a542a
- Blog 3: in progress

**How to use templates and scripts:**
We use the following script for Norsk Bokmål:
.\scripts\generate_from_template_all_categories_lang_utf8_nb.py

This script utilizes one or more ".\templates\<<CATEGORY_NAME>>_nb.csv" files to create context/question files in ".\data_nb\" folder. If you are testing just ONE of the categories, make sure to comment out the others in the script!

# all possible values of cat
cats = [
#    "Disability_status",
#    "Age",
#    "Physical_appearance",
#    "SES",
    "Gender_identity",
#    "Race_ethnicity",
#    "Religion",
#    "Nationality",
#    "Sexual_orientation",
]

To use this script, make sure your <<CATEGORY_NAME>>_nb.csv file is ready, comma-separated (not semicolon or something else), and utf-8 encoded. If this file does not adhere to these restrictions, the script will fail.

Run the script from the MAIN folder (in our case, the "NoBBQ" folder).

set BBQ_LANG=nb && python scripts\generate_from_template_all_categories_lang_utf8_nb.py

The output should look like this:
C:\Users\wesselb\dev\NoBBQ>set BBQ_LANG=nb && python scripts\generate_from_template_all_categories_lang_utf8_nb.py
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

If any issues with the script arise, feel free to contact us.

---

### License

© Norsk AI-Etikkforening (NAIE) 2025

- **Code** is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).  
- **Datasets, documentation, and research outputs** are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

You are free to use and adapt this work with proper attribution.  
Logo and name are trademarks of Norsk AI-Etikkforening and are not covered by these licenses.

---
