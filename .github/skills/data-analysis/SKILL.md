---
name: data-analysis
description: |
  End-to-end Python data analysis workflow. Load, explore, clean, transform,
  analyze, visualize, and report findings. Use when asked to analyze data,
  explore a dataset, or produce a data analysis report.
argument-hint: "[dataset path or description]"
---

# data-analysis — Data Analysis Workflow

## Step 1: Load Data
```python
import pandas as pd
df = pd.read_csv("data/dataset.csv")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"Dtypes:\n{df.dtypes}")
```

## Step 2: Explore
```python
print(df.describe())
print(df.isnull().sum())
print(df.nunique())
```

## Step 3: Clean
```python
df = df.dropna(subset=["required_column"])
df["date"] = pd.to_datetime(df["date"])
df = df.drop_duplicates()
```

## Step 4: Transform
```python
df["derived_feature"] = df["col_a"] / df["col_b"]
df["category"] = df["category"].str.lower().str.strip()
```

## Step 5: Analyze
```python
results = df.groupby("category").agg({"value": ["mean", "std", "count"]})
correlations = df[numeric_cols].corr()
```

## Step 6: Visualize
```python
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
# ... plotting code
fig.savefig("output/analysis_plot.png", dpi=150, bbox_inches="tight")
```

## Step 7: Report

Save findings to `output/analysis_YYYY-MM-DD.md` or present inline.

## Verification
- [ ] All figures generated and saved
- [ ] No empty DataFrames in results
- [ ] Output directory exists
- [ ] Results make domain sense
