"""Survey pipeline: raw CSV -> cleaned, flagged, tested, weighted -> Excel report."""
import numpy as np, pandas as pd # type: ignore
from scipy.stats import chi2_contingency, mannwhitneyu # type: ignore

RAW, OUT = "data/survey_results_public.csv", "outputs/survey_report.xlsx"
COLS = ["ResponseId","Age","EdLevel","Employment","RemoteWork","DevType","OrgSize",
        "YearsCode","WorkExp","Country","AISelect","AIAcc","JobSat","ConvertedCompYearly"]
TARGETS = {  # illustrative, replace with client/census targets in real projects
 "Age":  {"18-24 years old":.20,"25-34 years old":.30,"35-44 years old":.25,
          "45-54 years old":.15,"55-64 years old":.07,"65 years or older":.03},
 "Work": {"Remote":.30,"Hybrid/Flexible":.45,"In-person":.25}}

def clean(df, log):
    df = df.copy()
    n = (df["Age"] == "Prefer not to say").sum()
    df["Age"] = df["Age"].replace("Prefer not to say", np.nan)
    log.append(("Age 'Prefer not to say'", "set to missing", n))

    max_age = {"18-24 years old":24,"25-34 years old":34,"35-44 years old":44,
               "45-54 years old":54,"55-64 years old":64,"65 years or older":100}
    top = df["Age"].map(max_age)
    df["flag_workexp_age"] = df["WorkExp"] > (top - 14)   # worked before age 14
    df["flag_yearscode_age"] = df["YearsCode"] > (top - 5) # coded before age 5
    log.append(("WorkExp implies working before age 14", "flagged, kept", int(df["flag_workexp_age"].sum())))
    log.append(("YearsCode implies coding before age 5", "flagged, kept", int(df["flag_yearscode_age"].sum())))

    young = df["Age"].isin(["18-24 years old"])
    df["flag_age_exp"] = young & (df["WorkExp"] > 10)
    log.append(("Age 18-24 with 10+ yrs exp", "flagged, kept", df["flag_age_exp"].sum()))

    c = df["ConvertedCompYearly"]
    df["flag_comp_outlier"] = (c < 1000) | (c > 1_000_000)
    df["comp_clean"] = c.where(~df["flag_comp_outlier"])
    log.append(("Salary outside $1K-$1M", "set to missing in comp_clean", df["flag_comp_outlier"].sum()))

    df["Country"] = df["Country"].str.strip()
    df["Work"] = df["RemoteWork"].map(lambda x: np.nan if pd.isna(x) else
        "Remote" if x == "Remote" else "In-person" if x == "In-person" else "Hybrid/Flexible")
    return df

def rake(d, targets, iters=100, tol=1e-6):
    w = np.ones(len(d))
    for _ in range(iters):
        old = w.copy()
        for var, tgt in targets.items():
            share = pd.Series(w, index=d.index).groupby(d[var]).sum() / w.sum()
            w = w * d[var].map({k: tgt[k] / share[k] for k in tgt}).values
        if np.abs(w - old).max() < tol: break
    return np.minimum(w, 5 * w.mean())  # trim extreme weights

def main():
    log = []
    df = pd.read_csv(RAW, usecols=COLS)
    log.append(("Rows loaded", "none", len(df)))
    log.append(("Duplicate ResponseId", "none found" if not df["ResponseId"].duplicated().any() else "check", int(df["ResponseId"].duplicated().sum())))
    df = clean(df, log)

    # Test 1: Age x AI usage
    d = df.dropna(subset=["Age", "AISelect"])
    ct = pd.crosstab(d["Age"], d["AISelect"])
    pct = pd.crosstab(d["Age"], d["AISelect"], normalize="index").mul(100).round(1)
    chi2, p, _, _ = chi2_contingency(ct)
    v = np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1)))

    # Test 2: JobSat Remote vs In-person
    d2 = df.dropna(subset=["RemoteWork", "JobSat"])
    a = d2.loc[d2["RemoteWork"] == "Remote", "JobSat"]
    b = d2.loc[d2["RemoteWork"] == "In-person", "JobSat"]
    u, p2 = mannwhitneyu(a, b)
    r = 1 - 2 * u / (len(a) * len(b))

    tests = pd.DataFrame([
        ["Age x AI usage", "Chi-square", f"{chi2:.1f}", f"{p:.3g}", f"Cramer's V = {v:.3f}", len(d)],
        ["JobSat Remote vs In-person", "Mann-Whitney U", f"{u:.0f}", f"{p2:.3g}", f"rank-biserial r = {r:.3f}", len(a) + len(b)],
    ], columns=["Question", "Test", "Statistic", "p-value", "Effect size", "n"])

    # Weighting
    w = df.dropna(subset=["Age", "Work", "AISelect"]).copy()
    w["w"] = rake(w, TARGETS)
    n_eff = w["w"].sum() ** 2 / (w["w"] ** 2).sum()
    wpct = pd.crosstab(w["Age"], w["AISelect"], values=w["w"], aggfunc="sum", normalize="index").mul(100).round(1)
    daily = w["AISelect"].eq("Yes, I use AI tools daily")
    wcheck = pd.DataFrame({
        "metric": ["n", "effective n", "daily AI % unweighted", "daily AI % weighted"],
        "value": [len(w), round(n_eff), round(daily.mean() * 100, 1),
                  round((daily * w["w"]).sum() / w["w"].sum() * 100, 1)]})

    with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
        pd.DataFrame(log, columns=["Issue", "Rule", "Rows"]).to_excel(xw, sheet_name="Change_Log", index=False)
        tests.to_excel(xw, sheet_name="Tests", index=False)
        pct.to_excel(xw, sheet_name="Age_x_AI_unweighted")
        wpct.to_excel(xw, sheet_name="Age_x_AI_weighted")
        wcheck.to_excel(xw, sheet_name="Weighting_Check", index=False)
    df.to_csv("outputs/survey_clean.csv", index=False)
    print("Done ->", OUT)

if __name__ == "__main__":
    main()