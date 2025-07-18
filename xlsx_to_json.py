import argparse
import json
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser(
    description="Convert a digitalni upitnik XLSX into JSON"
)
parser.add_argument("xlsx_path", help="relative path to the .xlsx file")
args = parser.parse_args()

input_path = Path(args.xlsx_path)
df = pd.read_excel(input_path, header=0)

split_row = df[df["VU_ID"] == "ID pitanja"].index[0]

answers_frame = df.iloc[:split_row].dropna(subset=["VU_ID"]).copy()
answers_frame["VU_ID"] = answers_frame["VU_ID"].astype(int)
answers_frame["Respondent_ID"] = answers_frame["Respondent_ID"].astype(int)

questions_frame = df.iloc[split_row + 1 :, :2].copy()
questions_frame.columns = ["Question_ID", "Question_Text"]
question_mapping = questions_frame.set_index("Question_ID")["Question_Text"].to_dict()

output_records = []
for _, row in answers_frame.iterrows():
    record = {
        "Institution_ID": row["VU_ID"],
        "Responder_ID": row["Respondent_ID"],
        "Responses": [],
    }
    for question_id, question_text in question_mapping.items():
        if question_id in row:
            record["Responses"].append(
                {
                    "Question_ID": question_id,
                    "Question_Text": question_text,
                    "Answer": int(row[question_id]),
                }
            )
    output_records.append(record)

output_path = input_path.with_suffix(".json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output_records, f, ensure_ascii=False, indent=2)
