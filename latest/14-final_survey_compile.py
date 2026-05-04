import sys
from pathlib import Path

import pandas as pd


CSV_PATH = Path(sys.argv[1])
if not CSV_PATH.exists():
    raise FileNotFoundError("Could not find CSV file: " + str(CSV_PATH))

df = pd.read_csv(CSV_PATH)
n = len(df)

COL_USE_PROGRAMMING = (
    "Do you currently use LLM tools such as ChatGPT, Copilot, Gemini, Claude, etc. "
    "for programming?"
)

COL_DEBUG_FREQ = "How often do you use LLMs specifically for debugging?"

COL_TRUST = (
    "Did the LLM feedback make you more or less likely to trust LLM debugging help?"
)

COL_AWARENESS = (
    "Before reading this, were you aware that LLM usage can involve significant "
    "energy and infrastructure costs?"
)

COL_USE_BEFORE = (
    "On a scale from 0 to 10, how likely are you to use LLMs for debugging in the future?"
)

COL_USE_AFTER = (
    "On a scale from 0 to 10, how likely are you to use LLMs for debugging in the future?.1"
)

COL_VERIFY_BEFORE = (
    "On a scale from 0 to 10, how carefully do you usually verify "
    "LLM-generated debugging suggestions?"
)

COL_VERIFY_AFTER = (
    "On a scale from 0 to 10, how carefully do you plan to verify "
    "LLM-generated debugging suggestions in the future?"
)

COL_VIEW_AFTER = "Which best describes your view after reading this information?"


def count_percent(mask):
    """Return count and percentage string."""
    count = int(mask.sum())
    percent = count / n * 100
    return count, f"{count}/{n} = {percent:.1f}\\%"


def mean_score(col):
    """Return mean score rounded to 1 decimal."""
    return df[col].mean().round(1)


rows = []

count, result = count_percent(df[COL_USE_PROGRAMMING].str.strip().eq("Yes"))
rows.append({
    "Factor": "Currently use LLMs for programming",
    "Result": result,
    "Interpretation": "Participants had high prior exposure to LLM tools."
})

debug_often = df[COL_DEBUG_FREQ].str.strip().isin(["Often", "Very often"])
count, result = count_percent(debug_often)
rows.append({
    "Factor": "Use LLMs for debugging often/very often",
    "Result": result,
    "Interpretation": "Debugging with LLMs was already common among participants."
})

trust_increased = df[COL_TRUST].str.strip().isin(
    ["Slightly more likely", "Much more likely"]
)
count, result = count_percent(trust_increased)
rows.append({
    "Factor": "LLM feedback increased trust",
    "Result": result,
    "Interpretation": "LLM explanations generally made participants more trusting."
})

trust_decreased = df[COL_TRUST].str.strip().isin(
    ["Slightly less likely", "Much less likely"]
)
count, result = count_percent(trust_decreased)
rows.append({
    "Factor": "LLM feedback decreased trust",
    "Result": result,
    "Interpretation": "A minority became more skeptical after the disagreement experience."
})

aware = df[COL_AWARENESS].str.strip().eq("Yes")
count, result = count_percent(aware)
rows.append({
    "Factor": "Aware of LLM energy/infrastructure costs",
    "Result": result,
    "Interpretation": "Ethical concerns were not new to most participants."
})

use_before = mean_score(COL_USE_BEFORE)
use_after = mean_score(COL_USE_AFTER)
rows.append({
    "Factor": "Future LLM debugging use, before vs. after ethical prompt",
    "Result": f"{use_before:.1f} $\\rightarrow$ {use_after:.1f} / 10",
    "Interpretation": "Ethical information did not reduce intended use."
})

verify_before = mean_score(COL_VERIFY_BEFORE)
verify_after = mean_score(COL_VERIFY_AFTER)
rows.append({
    "Factor": "Verification carefulness, before vs. after ethical prompt",
    "Result": f"{verify_before:.1f} $\\rightarrow$ {verify_after:.1f} / 10",
    "Interpretation": "Ethical/contextual information slightly increased caution."
})

same_more_careful = df[COL_VIEW_AFTER].str.strip().eq(
    "I would use LLMs about the same amount, but more carefully"
)
count, result = count_percent(same_more_careful)
rows.append({
    "Factor": "Would use LLMs same amount but more carefully",
    "Result": result,
    "Interpretation": "Ethical considerations shifted behavior toward verification."
})

summary = pd.DataFrame(rows)

print(summary.to_markdown(index=False))