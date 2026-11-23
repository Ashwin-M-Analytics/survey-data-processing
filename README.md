# Survey Data Processing Pipeline

Automated cleaning, QC, cross tabulations, significance testing and weighting on the
Stack Overflow Developer Survey (49,191 responses). One command turns the raw CSV
into a documented Excel report.

## Get the data
1. Download the full CSV from https://survey.stackoverflow.co (scroll to the bottom,
   "Download Full Data Set (CSV)"). This project uses the 2025 survey, so confirm the year.
2. Unzip it and place `survey_results_public.csv` in the `data/` folder.

The raw file is not included in this repo because of its size (~150 MB).

## Run
```
pip install pandas numpy scipy openpyxl
python3 src/process_survey.py        # writes outputs/survey_report.xlsx
python3 src/make_dictionary.py       # writes data_dictionary.csv
```

## What the pipeline does
Raw CSV -> cleaned and flagged -> cross tabulations -> significance tests
-> raking weights -> 5-sheet Excel report (Change_Log, Tests, Age_x_AI_unweighted,
Age_x_AI_weighted, Weighting_Check).

## Key findings
- **Age x AI usage:** significant (chi-square p < 0.001) but a negligible-to-small
  effect (Cramer's V = 0.086). Daily AI use peaks at 25-34 (51.1%) and falls to
  22.3% at 65+. Percentages are based on respondents who answered (15,471 did not).
- **Job satisfaction, remote vs in-person:** medians 8 vs 7 (n = 7,908 vs 3,496);
  a small effect favouring remote (rank-biserial r = -0.10).
- **Weighting:** the headline barely moved (daily AI use 48.4% unweighted vs 47.8%
  weighted), so results are robust to weighting. Effective n = 23,345 of 26,497.

## Data quality approach
- No duplicate ResponseIDs.
- Logic checks against age: work experience implying work before age 14 (119 rows)
  and years of coding implying coding before age 5 (77 rows). Flagged, not deleted.
- 770 salary values outside $1K-$1M set to missing in `comp_clean`; originals kept.
- 378 "Prefer not to say" ages set to missing.
- High missingness (28-51%) on several questions, likely survey skip logic. Not imputed.
- Full rule list: see `CHANGES.md`.

## Limitations
- Weighting targets are illustrative, not official population figures. Real projects
  would use the client's specification or census data.
- Self-selected online survey, so results do not represent all developers.
- Job satisfaction test compares Remote and In-person only; hybrid groups excluded.

## Files
`src/process_survey.py` | `src/make_dictionary.py` | `notebooks/` | `data_dictionary.csv` | `CHANGES.md`

## Data source and licence
Stack Overflow Developer Survey, licensed under ODbL. Credit: Stack Overflow.
