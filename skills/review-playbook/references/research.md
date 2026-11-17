# Research and data analysis checklist

## Sources

- Claims about the current state of the world come from a source checked now, not from memory.
- Sources are primary where possible, recent enough for the question, and cited. Conflicts between sources are stated.
- What a source says is kept separate from what was concluded from it.

## Data

- The data was inspected before analysis: row counts, missing values, duplicates, units, date range and outliers.
- Filters and joins did not silently drop or duplicate rows. Counts were compared before and after.
- Numbers were computed with code, not estimated.
- Sanity check: the order of magnitude is right, percentages sum correctly, and there are no impossible values.

## Conclusions

- Correlation is not presented as cause. Small samples are flagged.
- Charts have labelled axes, units and an honest scale.
- Limits are stated: sample size, missing data, and what the analysis cannot show.
- The analysis can be repeated: the data source, filters and code or formulas are recorded.
