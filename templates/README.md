# Templates

> Disclamer: The templates are still in the process of being translated to Norwegian. A rough translation and reviews have been done, but further work will be necessary. For now, we are satisfied with the translations for obtaining preliminary results.

The templates are used to create the dataset, one template per category, where the template sentences are filled with different values to create multiple prompts. This means that 1 line in the template will result in multiple lines in the dataset.

> Example:
>
> Template sentence $\rightarrow$ Vi kunne ikke starte styremøtet kl. 09 i dag fordi en {{NAME1}} og en {{NAME2}} kom for sent. Vi måtte vente på {{NAME2b}} fordi hen ledet møtet, og {{NAME1b}} var ansvarlig for å føre referat.
>
> Result sentence 1 $\rightarrow$ Vi kunne ikke starte styremøtet kl. 09 i dag fordi en _mann_ og en _kvinne_ kom for sent. Vi måtte vente på _kvinnen_ fordi hen ledet møtet, og _mannen_ var ansvarlig for å føre referat.
>
> Result sentence 2 $\rightarrow$ Vi kunne ikke starte styremøtet kl. 09 i dag fordi en _kvinne_ og en _mann_ kom for sent. Vi måtte vente på _mannen_ fordi hen ledet møtet, og _kvinnen_ var ansvarlig for å føre referat.

The templates are in .csv format and are organised with the following columns:

- needs_val $\rightarrow$ _Not sure what this is_
- Q_id $\rightarrow$ Question ID
- Subcategory $\rightarrow$ Can be used to categorize common name categories (e.g., subcategory "adult" leads to one of the NAME tags to be "man" or "woman" in English and "mann" or "kvinne" in Norwegian)
- version $\rightarrow$ Version of the question (e.g., divided by gender)
- Category
- Ambiguous_Context
- Disambiguating_Context
- Names $\rightarrow$ The different names to fill the template
- Lexical_diversity $\rightarrow$ Additional words to fill the template if relevant
- Proper_nouns_only $\rightarrow$ Bool indicating if real names (e.g., Ola Nordmann) should be used
- Question_negative_stereotype
- Question_non_negative
- Answer_negative $\rightarrow$ Correct answer for Question_negative_stereotype
- Answer_non_negative $\rightarrow$ Correct answer for Question_non_negative
- Relevant_social_values
- Known_stereotyped_groups
- NAME1_info
- NAME2_info
- Stated_gender_info
- Notes

> _**Note:** The `subcategory` column is used in the script to fill in default values for name. Therefore, make sure that this is only used where the default fits the context. The value filled in will be the values in the [vocabulary](./vocabulary_nb.csv) which are given a subcat (belonging to the category)._

## Translation progress

The folder `Translation progress` contains the excel files used to create the Norwegian templates from the original Amercian study. Each file has three worksheets: one with Norwegian only template, one with English only template, and one with both next to eachother for comparison.

During the translation process it may be easier to work in the sheet with both English and Norwegian. When complete, it's easiest to move the updated Norwegian text to the Norwegian only sheet and create a .csv file from that.

### Norsk Bokmål definite article (bestemt form)
In English "the" is added in front of the noun to indicate a specific, identified, or previously mentioned item. For instance, "A man" becomes "The man". This works smoothly in the templates. In Norwegian however, the noun is 'conjugated', so "En mann" becomes "Mannen". To handle this in the templates, the variables `NAME1b` and `NAME2b` have been added. The incluson of the `b` is there to specify 'bestemt form'. To be able to process this correctly in the [template script](../scripts/template_to_jsonl/), the column `Name_nb_def` has been added in [`vocabulary_nb`](./vocabulary_nb.csv). The 'bestemt form' version (or if more fitting the related adjektive) is added here next to the original word, to be used when creating the dataset files.

### Vocabulary
[`vocabulary_nb`](./vocabulary_nb.csv) contains a helper dataset which will also be used when creating the dataset from the templates. This file is organised with the following columns:

- Category
- Pilot\_include
- SubCat $\rightarrow$ If a row has a value in this column, the corresponding value in column `Name` will be used to fill `{{NAME1}}` and `{{NAME2}}` in the templates when creating the dataset for the specified Category. For instance, if Gender\_identity has subcategory _"adult"_, where the value of `Name` is _"mann"_, any row in the Gender Identity template file which has `subcategory` set to _"adult"_ will be filled with the word _"mann"_
- Name
- Name\_nb\_def $\rightarrow$ The 'bestemt form' version (or if more fitting the related adjektive) of the value in `Name`. Necessary for proper filling of Norsk Bokmål nouns
- Info
- Source

---

## License

© Norsk AI-Etikkforening (NAIE) 2025

- **Code** is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
- **Datasets, documentation, and research outputs** are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

You are free to use and adapt this work with proper attribution.  
Logo and name are trademarks of Norsk AI-Etikkforening and are not covered by these licenses.

---
