# NoBBQ

**We are using the following research/repo as a basis for our Norwegian version of the same thing;**

- https://github.com/nyu-mll/BBQ/blob/main/README.md

**This project is initiated by:**

- Wessel Braakman
- Alejandra Palacio Perez
- Teresa Dalen Herland

**Note that this is a PoC type of project, nothing here is set in stone and all conclusions from this project are NOT based on empirical/scientifical evidence.
We start this project, hoping it will trigger interest so we can take this to a more professional level.**

## Our work

Progress can be tracked by either

- **Checking our repository regularly**
- **Reading our blogs on Medium:**
- Blog 1: https://medium.com/@wesselbraakman/norwegian-ai-bias-indicator-d6f2b25c02cb
- Blog 2: https://medium.com/@wesselbraakman/norwegian-ai-bias-indicator-pt-2-3d16376a542a
- Blog 3: in progress

## Usage

### Process

1. Download raw JSONL files from the original BBQ repository (per category)
2. Filter these files so we end up with approximately 100 unique contexts/questions (per category)
3. Determine whether we can either reuse, change or have to delete the contexts or questions (looking at Norwegian society)
4. Translate the contexts and questions to Norwegian
5. Create prompts (context + questions)
6. Send prompts to various LLM systems (e.g. ChatGPT, Perplexity, Gemini, ...)
7. Document responses
8. Review and score the responses (do they contain bias)
9. Report conclusions

### Instructions

The instructions for the process steps listed above are places in the respective directories. Please see [Templates](templates/README.md), [Scripts](scripts/README.md) and [Data](data/README.md) for more information.

To be able to run the files you need to make sure to have Python (e.g., version 3.13.12) and all the necessary packages installed. To install the necessary packages, run the following command from the root dir:

```
pip install -r requirements.txt
```

Feel free to contact us if you have any issues.

---

## License

© Norsk AI-Etikkforening (NAIE) 2025

- **Code** is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
- **Datasets, documentation, and research outputs** are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

You are free to use and adapt this work with proper attribution.  
Logo and name are trademarks of Norsk AI-Etikkforening and are not covered by these licenses.

---
