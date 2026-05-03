#!/usr/bin/env python3
"""
Compile APR survey results from a simplified Google Forms CSV.

Usage:
    python3 14-compile_results.py compiled-respnses.csv

Expected CSV layout:
    Timestamp, Name Surname,
    [initial judgment question for patch 1],
    [ChatGPT considers this patch ... agree/disagree question for patch 1],
    [Do you still agree or disagree? for patch 1],
    ... repeated for each patch

The script prints all result tables in Markdown.
Compatible with Python 3.7+.
"""

import sys
import re
from pathlib import Path

import pandas as pd


def pct(num, den):
    if den == 0:
        return "0.0%"
    return f"{100.0 * num / den:.1f}%"


def agreement_cell(matches, total):
    return f"{matches} / {total} = {pct(matches, total)}"


def normalize_answer(value):
    if pd.isna(value):
        return ""

    s = str(value).strip()
    s_clean = " ".join(s.split())
    key = s_clean.lower()

    mapping = {
        "correct": "Correct",
        "overfitting": "Overfitting",
        "not sure": "Not sure",
        "agree": "Agree",
        "disagree": "Disagree",
        "keep original answer": "Keep original answer",
        "change to correct": "Change to Correct",
        "change to overfitting": "Change to Overfitting",
        "change to not sure": "Change to Not sure",
    }
    return mapping.get(key, s_clean)


def extract_patch_name(question_col):
    """Extract patch name from the initial judgment question column."""
    m = re.search(
        r"bug in the (.*?) is a Correct fix",
        question_col,
        flags=re.IGNORECASE,
    )
    if not m:
        raise ValueError("Could not extract patch name from column:\n" + str(question_col))
    return m.group(1).strip()


def extract_chatgpt_judgment(assessment_col):
    """Extract ChatGPT label from the assessment column."""
    m = re.search(
        r"ChatGPT considers this patch to be (Correct|Overfitting)",
        assessment_col,
        flags=re.IGNORECASE,
    )
    if not m:
        raise ValueError("Could not extract ChatGPT judgment from column:\n" + str(assessment_col))
    return normalize_answer(m.group(1))


def final_judgment(initial, post_reasoning_response):
    """Convert post-reasoning response to final human judgment."""
    if post_reasoning_response == "Keep original answer":
        return initial
    if post_reasoning_response == "Change to Correct":
        return "Correct"
    if post_reasoning_response == "Change to Overfitting":
        return "Overfitting"
    if post_reasoning_response == "Change to Not sure":
        return "Not sure"

    # Useful fallback if the CSV directly stores final labels.
    if post_reasoning_response in ["Correct", "Overfitting", "Not sure"]:
        return post_reasoning_response

    return post_reasoning_response


def markdown_table(df):
    """Print a simple Markdown table without requiring tabulate."""
    if df.empty:
        return "_No rows._"

    cols = list(df.columns)
    rows = [[str(x) for x in row] for row in df.to_numpy().tolist()]

    widths = []
    for i, col in enumerate(cols):
        max_width = len(str(col))
        for row in rows:
            max_width = max(max_width, len(row[i]))
        widths.append(max_width)

    header = "| " + " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(cols)) + " |"
    sep = "| " + " | ".join("-" * widths[i] for i in range(len(cols))) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(cols))) + " |")

    return "\n".join([header, sep] + body)


def print_table(title, df):
    print("\n## " + title + "\n")
    print(markdown_table(df))


def find_question_blocks(columns):
    """
    Find repeated 3-column blocks:
        initial question, ChatGPT assessment, post-reasoning answer.
    """
    blocks = []
    i = 0
    while i < len(columns):
        col = columns[i]
        if col.startswith("Do you think the patch for the bug in the"):
            if i + 2 >= len(columns):
                raise ValueError("Question block is incomplete near column: " + col)

            initial_col = columns[i]
            assessment_col = columns[i + 1]
            post_col = columns[i + 2]

            # Basic safety checks.
            if not str(assessment_col).startswith("ChatGPT considers this patch"):
                raise ValueError(
                    "Expected ChatGPT assessment column after initial question, but found:\n"
                    + str(assessment_col)
                )
            if not str(post_col).startswith("Do you still agree or disagree?"):
                raise ValueError(
                    "Expected post-reasoning column after ChatGPT assessment, but found:\n"
                    + str(post_col)
                )

            blocks.append((initial_col, assessment_col, post_col))
            i += 3
        else:
            i += 1

    return blocks


def parse_survey_csv(csv_path):
    df = pd.read_csv(csv_path)
    columns = list(df.columns)
    blocks = find_question_blocks(columns)

    if not blocks:
        raise ValueError("No question blocks were found. Check the CSV column names.")

    records = []

    for initial_col, assessment_col, post_col in blocks:
        patch = extract_patch_name(initial_col)
        chatgpt_label = extract_chatgpt_judgment(assessment_col)

        for _, row in df.iterrows():
            participant = row.get("Name Surname", "")
            initial = normalize_answer(row[initial_col])
            response_to_chatgpt = normalize_answer(row[assessment_col])
            post_reasoning = normalize_answer(row[post_col])
            final = final_judgment(initial, post_reasoning)

            records.append({
                "participant": participant,
                "patch": patch,
                "chatgpt_judgment": chatgpt_label,
                "initial_judgment": initial,
                "response_to_chatgpt": response_to_chatgpt,
                "post_reasoning_response": post_reasoning,
                "final_judgment": final,
            })

    return pd.DataFrame(records)


def make_tables(data):
    tables = {}
    total = len(data)

    initial_matches = int((data["initial_judgment"] == data["chatgpt_judgment"]).sum())
    final_matches = int((data["final_judgment"] == data["chatgpt_judgment"]).sum())

    initial_definite = data[data["initial_judgment"] != "Not sure"]
    final_definite = data[data["final_judgment"] != "Not sure"]

    initial_def_matches = int(
        (initial_definite["initial_judgment"] == initial_definite["chatgpt_judgment"]).sum()
    )
    final_def_matches = int(
        (final_definite["final_judgment"] == final_definite["chatgpt_judgment"]).sum()
    )

    tables["Agreement between human and ChatGPT judgments"] = pd.DataFrame([
        {
            "Comparison": "Before ChatGPT reasoning",
            "Matching judgments": f"{initial_matches} / {total}",
            "Agreement": pct(initial_matches, total),
        },
        {
            "Comparison": "After ChatGPT reasoning",
            "Matching judgments": f"{final_matches} / {total}",
            "Agreement": pct(final_matches, total),
        },
        {
            "Comparison": "Before reasoning, excluding Not sure",
            "Matching judgments": f"{initial_def_matches} / {len(initial_definite)}",
            "Agreement": pct(initial_def_matches, len(initial_definite)),
        },
        {
            "Comparison": "After reasoning, excluding Not sure",
            "Matching judgments": f"{final_def_matches} / {len(final_definite)}",
            "Agreement": pct(final_def_matches, len(final_definite)),
        },
    ])

    rows = []
    for label in ["Correct", "Overfitting"]:
        subset = data[data["chatgpt_judgment"] == label]
        n = len(subset)
        init = int((subset["initial_judgment"] == subset["chatgpt_judgment"]).sum())
        fin = int((subset["final_judgment"] == subset["chatgpt_judgment"]).sum())
        rows.append({
            "ChatGPT judgment": label,
            "Initial agreement": agreement_cell(init, n),
            "Final agreement": agreement_cell(fin, n),
        })

    tables["Agreement with ChatGPT judgments by ChatGPT label"] = pd.DataFrame(rows)

    patch_rows = []
    for (patch, label), group in data.groupby(["patch", "chatgpt_judgment"], sort=False):
        n = len(group)
        init = int((group["initial_judgment"] == group["chatgpt_judgment"]).sum())
        fin = int((group["final_judgment"] == group["chatgpt_judgment"]).sum())
        patch_rows.append({
            "Patch / algorithm": patch,
            "ChatGPT judgment": label,
            "Initial matches": init,
            "Final matches": fin,
            "Total": n,
            "Initial agreement": agreement_cell(init, n),
            "Final agreement": agreement_cell(fin, n),
        })

    patch_df = pd.DataFrame(patch_rows)

    tables["Patches with the lowest initial human-ChatGPT agreement"] = (
        patch_df
        .sort_values(["Initial matches", "Patch / algorithm"], ascending=[True, True])
        .head(7)
        [["Patch / algorithm", "ChatGPT judgment", "Initial agreement"]]
        .reset_index(drop=True)
    )

    tables["Patches with the lowest final human-ChatGPT agreement"] = (
        patch_df
        .sort_values(["Final matches", "Patch / algorithm"], ascending=[True, True])
        .head(5)
        [["Patch / algorithm", "ChatGPT judgment", "Final agreement"]]
        .reset_index(drop=True)
    )

    changed = data[data["initial_judgment"] != data["final_judgment"]].copy()
    changed_n = len(changed)

    changed_toward = int((
        (changed["initial_judgment"] != changed["chatgpt_judgment"]) &
        (changed["final_judgment"] == changed["chatgpt_judgment"])
    ).sum())

    changed_away = int((
        (changed["initial_judgment"] == changed["chatgpt_judgment"]) &
        (changed["final_judgment"] != changed["chatgpt_judgment"])
    ).sum())

    other = changed_n - changed_toward - changed_away

    tables["Summary of participant answer revisions"] = pd.DataFrame([
        {
            "Revision type": "Human answer changed after reasoning",
            "Count": agreement_cell(changed_n, total),
        },
        {
            "Revision type": "Changed toward the ChatGPT judgment",
            "Count": agreement_cell(changed_toward, changed_n),
        },
        {
            "Revision type": "Changed away from the ChatGPT judgment",
            "Count": agreement_cell(changed_away, changed_n),
        },
        {
            "Revision type": "Other or mixed effect",
            "Count": agreement_cell(other, changed_n),
        },
    ])

    direction = (
        changed
        .groupby(["initial_judgment", "final_judgment"])
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
        .rename(columns={
            "initial_judgment": "Initial judgment",
            "final_judgment": "Final judgment",
        })
        .reset_index(drop=True)
    )
    tables["Direction of participant answer changes"] = direction

    rows = []
    for response in ["Agree", "Disagree", "Not sure"]:
        subset = data[data["response_to_chatgpt"] == response]
        n = len(subset)
        changed_count = int((subset["initial_judgment"] != subset["final_judgment"]).sum())
        rows.append({
            "Response to ChatGPT assessment": response,
            "Total cases": n,
            "Changed answer": changed_count,
            "Change rate": pct(changed_count, n),
        })

    tables["Revision rate by participant response to ChatGPT assessment"] = pd.DataFrame(rows)

    most_revised = (
        changed
        .groupby(["patch", "chatgpt_judgment"])
        .size()
        .reset_index(name="Revised answers")
        .sort_values(["Revised answers", "patch"], ascending=[False, True])
        .head(7)
        .rename(columns={
            "patch": "Patch / algorithm",
            "chatgpt_judgment": "ChatGPT judgment",
        })
        .reset_index(drop=True)
    )
    tables["Patches where ChatGPT reasoning caused the most revisions"] = most_revised

    return tables


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        raise FileNotFoundError("Could not find CSV file: " + str(csv_path))

    data = parse_survey_csv(csv_path)

    print(f"Parsed {len(data)} participant-patch judgments.")
    print(f"Participants: {data['participant'].nunique()}")
    print(f"Patches: {data['patch'].nunique()}")

    # Optional diagnostics: useful for checking whether parsing worked.
    print("\nDetected patches:")
    for patch in data["patch"].drop_duplicates().tolist():
        label = data.loc[data["patch"] == patch, "chatgpt_judgment"].iloc[0]
        print(f"- {patch}: ChatGPT = {label}")

    tables = make_tables(data)
    for title, table in tables.items():
        print_table(title, table)


if __name__ == "__main__":
    main()
