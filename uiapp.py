import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# Title
st.title("🧾 Bank Statement PDF to Excel Converter")

# Radio for selecting bank
bank = st.radio("Select Bank", ["HDFC", "Any Other Bank (ICICI , Axis ,..)"])

# File uploader
uploaded_file = st.file_uploader("Upload PDF Bank Statement", type=["pdf"])

# Expected column headers
columns = ["Date", "Narration", "Chq./Ref.No.", "Value Date", "Withdrawal Amt", "Deposit Amt", "Closing Balance"]

# Process HDFC
def process_hdfc(pdf_bytes):
    date_pattern = re.compile(r"^\d{2}/\d{2}/\d{2}")
    transactions = []
    current_row = {}
    previous_closing = None

    def parse_amount(value):
        try:
            return float(value.replace(',', ''))
        except:
            return None

    def finalize_row(row_dict):
        nonlocal previous_closing
        w_amt = parse_amount(row_dict.get("Withdrawal Amt", "0.00"))
        d_amt = parse_amount(row_dict.get("Deposit Amt", "0.00"))
        c_bal = parse_amount(row_dict.get("Closing Balance", "0.00"))

        if w_amt is None and d_amt is not None and previous_closing is not None:
            if c_bal > previous_closing:
                d_amt = c_bal - previous_closing
                w_amt = 0.00
            else:
                w_amt = previous_closing - c_bal
                d_amt = 0.00
        elif d_amt is None and w_amt is not None and previous_closing is not None:
            if c_bal > previous_closing:
                d_amt = c_bal - previous_closing
                w_amt = 0.00
            else:
                w_amt = previous_closing - c_bal
                d_amt = 0.00

        row = [
            row_dict.get("Date", ""),
            row_dict.get("Narration", ""),
            row_dict.get("Chq/Ref", ""),
            row_dict.get("Value Date", ""),
            f"{w_amt:,.2f}" if w_amt is not None else "0.00",
            f"{d_amt:,.2f}" if d_amt is not None else "0.00",
            row_dict.get("Closing Balance", "")
        ]
        previous_closing = c_bal
        transactions.append(row)

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().split("\n")

            for line in lines:
                tokens = line.strip().split()
                if not tokens:
                    continue

                if date_pattern.match(tokens[0]):
                    if current_row:
                        finalize_row(current_row)
                    current_row = {"Date": tokens[0]}
                    try:
                        current_row["Closing Balance"] = tokens[-1]
                        current_row["Deposit Amt"] = tokens[-2] if re.match(r"^\d{1,3}(,\d{3})*(\.\d{2})?$", tokens[-2]) else None
                        current_row["Withdrawal Amt"] = tokens[-3] if re.match(r"^\d{1,3}(,\d{3})*(\.\d{2})?$", tokens[-3]) else None
                        current_row["Value Date"] = tokens[3]
                        current_row["Chq/Ref"] = tokens[2]
                        narration_tokens = tokens[1]
                        current_row["Narration"] = narration_tokens
                    except Exception as e:
                        print("Error parsing line:", line, "Error:", e)
                else:
                    if current_row:
                        current_row["Narration"] += " " + line.strip()

        if current_row:
            finalize_row(current_row)

    return pd.DataFrame(transactions, columns=columns)

# Process ICICI (dummy logic)
def process_icici(pdf_bytes):
    extracted_data = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                cleaned_table = []
                for row in table:
                    if any(cell.strip() for cell in row if cell):  # Ignore empty rows
                        cleaned_table.append([cell.replace("\n", " ").strip() if cell else "" for cell in row])
                if cleaned_table:
                    extracted_data.extend(cleaned_table)

    if not extracted_data:
        st.warning("No tables found in the PDF.")
        return pd.DataFrame()

    headers = extracted_data[0]
    rows = extracted_data[1:]

    
    return pd.DataFrame(rows, columns=headers)

# Main logic
if uploaded_file:
    pdf_bytes = uploaded_file.read()
    if bank == "HDFC":
        df = process_hdfc(pdf_bytes)
    elif bank == "Any Other Bank (ICICI , Axis ,..)":
        df = process_icici(pdf_bytes)

    # Display and download
    st.success(f"{bank} PDF processed successfully!")
    st.dataframe(df)

    towrite = io.BytesIO()
    df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=towrite,
        file_name=f"{bank}_statement.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
