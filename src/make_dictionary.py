import pandas as pd # type: ignore
df = pd.read_csv("outputs/survey_clean.csv")
dd = pd.DataFrame({
    "column": df.columns,
    "type": df.dtypes.astype(str).values,
    "missing_%": (df.isna().mean() * 100).round(1).values,
    "unique_values": df.nunique().values,
    "description": "",
})
dd.to_csv("data_dictionary.csv", index=False)
print(dd)