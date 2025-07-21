import json

import pdfplumber


# Function to calculate averages and extract question texts
def calculate_averages(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    question_sums = {}
    question_counts = {}
    question_texts = {}

    for responder in data:
        for response in responder["Responses"]:
            question_id = response["Question_ID"]
            answer = response["Answer"]
            if question_id not in question_sums:
                question_sums[question_id] = 0
                question_counts[question_id] = 0
                question_texts[question_id] = response["Question_Text"]
            question_sums[question_id] += answer
            question_counts[question_id] += 1

    averages = {}
    for question_id in question_sums:
        averages[question_id] = (
            question_sums[question_id] / question_counts[question_id]
        )

    return {"averages": averages, "question_texts": question_texts}


# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += (
                page.extract_text() or ""
            )  # Handle cases where extract_text() returns None
    return text
