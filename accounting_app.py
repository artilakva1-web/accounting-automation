import streamlit as st
import pandas as pd
from fpdf import FPDF
import difflib

st.set_page_config(page_title="Accounting By A/C", layout="wide")

def clean_and_sum(series):
    """ზუსტი დაჯამება: აშორებს ყველაფერს ციფრებისა და წერტილის გარდა"""
    cleaned = series.astype(str).str.replace(r'[^0-9.]', '', regex=True)
    return pd.to_numeric(cleaned, errors='coerce').fillna(0).sum()

def is_name_similar(name1, name2):
    n1, n2 = str(name1).strip().lower(), str(name2).strip().lower()
    return difflib.SequenceMatcher(None, n1, n2).ratio() > 0.90

def match_phone(row, phone_df):
    try:
        debt_val = float(str(row.get('ვალები', 0)).replace('(', '').replace(')', '').replace(',', ''))
    except: debt_val = 0
    
    if debt_val <= 0: return "", ""
    target_name = str(row['სახელი გვარი']).strip()
    p_nomeri = str(row['პირადი ნომერი']).strip()
    matches = phone_df[phone_df['სახელი გვარი'].apply(lambda x: is_name_similar(x, target_name))]
    
    if matches.empty: return "ნომერი ვერ მოიძებნა", ""
    if len(matches) == 1: return matches.iloc[0]['ტელეფონი'], str(matches.iloc[0].get('შენიშვნა', '')).replace('nan', '')
    
    for length in [11, 7, 4]:
        if len(p_nomeri) >= length:
            suffix = p_nomeri[-length:]
            sub_match = matches[matches['პირადი ნომერი'].astype(str).str.endswith(suffix)]
            if not sub_match.empty:
                return sub_match.iloc[0]['ტელეფონი'], str(sub_match.iloc[0].get('შენიშვნა', '')).replace('nan', '')
    return "დუბლიკატია", ""

def generate_pdf(df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    try:
        pdf.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
        pdf.set_font('DejaVu', size=10)
    except: pdf.set_font('Arial', size=10)

    # 1. საწყისი გვერდი: საერთო შეჯამება
    pdf.add_page()
    pdf.set_font('DejaVu', size=16)
    pdf.cell(0, 15, "ბუღალტრული შეჯამება - By A/C", ln=True, align='C')
    pdf.ln(5)
    
    # აქ ვიყენებთ ახალ დაჯამების მეთოდს
    total_debts = clean_and_sum(df['ვალები'])
    total_advances = clean_and_sum(df['ავანსები'])
    
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font('DejaVu', size=12)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, f"საერთო ვალები ჯამში:  {total_debts:,.2f} ₾", 0, 1, 'L', True)
    pdf.set_text_color(0, 120, 0)
    pdf.cell(0, 10, f"საერთო ავანსები ჯამში:  ({total_advances:,.2f}) ₾", 0, 1, 'L', True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # პროექტების შეჯამება
    pdf.set_font('DejaVu', size=10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(80, 10, "პროექტის დასახელება", 1, 0, 'C', True)
    pdf.cell(55, 10, "ვალი", 1, 0, 'C', True)
    pdf.cell(55, 10, "ავანსი", 1, 1, 'C', True)
    
    for proj in df['პროექტის დასახელება'].unique():
        sub = df[df['პროექტის დასახელება'] == proj]
        pdf.cell(80, 10, str(proj)[:40], 1)
        pdf.cell(55, 10, f"{clean_and_sum(sub['ვალები']):,.2f}", 1, 0, 'R')
        pdf.cell(55, 10, f"({clean_and_sum(sub['ავანსები']):,.2f})", 1, 1, 'R')

    # 2. დეტალური გვერდები
    for proj in df['პროექტის დასახელება'].unique():
        pdf.add_page()
        pdf.set_font('DejaVu', size=14)
        pdf.cell(0, 10, f"პროექტი: {proj}", ln=True)
        proj_df = df[df['პროექტის დასახელება'] == proj]
        
        # მევალეები
        debtors = proj_df[proj_df['ვალები'] > 0]
        if not debtors.empty:
            pdf.ln(2)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 10, "მევალეების სია", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('DejaVu', size=8)
            pdf.set_fill_color(255, 245, 245)
            pdf.cell(55, 8, "სახელი გვარი", 1, 0, 'C', True)
            pdf.cell(30, 8, "პირადი №", 1, 0, 'C', True)
            pdf.cell(25, 8, "ვალი", 1, 0, 'C', True)
            pdf.cell(30, 8, "ტელეფონი", 1, 0, 'C', True)
            pdf.cell(50, 8, "შენიშვნა", 1, 1, 'C', True)
            for _, r in debtors.iterrows():
                pdf.cell(55, 7, str(r['სახელი გვარი'])[:30], 1)
                pdf.cell(30, 7, str(r['პირადი ნომერი']), 1)
                pdf.cell(25, 7, f"{r['ვალები']:.2f}", 1, 0, 'R')
                pdf.cell(30, 7, str(r['ტელეფონი']), 1)
                pdf.cell(50, 7, str(r['შენიშვნა']).replace('nan', '')[:25], 1, 1)
            pdf.cell(0, 8, f"პროექტის ჯამური ვალი: {clean_and_sum(debtors['ვალები']):,.2f} ₾", ln=True)

        # ავანსები
        advances = proj_df[proj_df['ავანსები'] > 0]
        if not advances.empty:
            pdf.ln(5)
            pdf.set_text_color(0, 120, 0)
            pdf.cell(0, 10, "ავანსების სია", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('DejaVu', size=8)
            pdf.set_fill_color(245, 255, 245)
            pdf.cell(80, 8, "სახელი გვარი", 1, 0, 'C', True)
            pdf.cell(50, 8, "პირადი №", 1, 0, 'C', True)
            pdf.cell(60, 8, "ავანსი", 1, 1, 'C', True)
            for _, r in advances.iterrows():
                pdf.cell(80, 7, str(r['სახელი გვარი'])[:45], 1)
                pdf.cell(50, 7, str(r['პირადი ნომერი']), 1)
                pdf.cell(60, 7, f"({r['ავანსები']:.2f})", 1, 1, 'R')
            pdf.cell(0, 8, f"პროექტის ჯამური ავანსი: ({clean_and_sum(advances['ავანსები']):,.2f}) ₾", ln=True)
    return pdf.output()

# --- STREAMLIT UI ---
st.title("📊 Accounting Tool By A/C")
f1 = st.file_uploader("ატვირთეთ prnValiSagad1.csv", type=['csv'])
f2 = st.file_uploader("ატვირთეთ valebi.csv", type=['csv'])

if f1 and f2:
    df1 = pd.read_csv(f1)
    df2 = pd.read_csv(f2)
    
    # გასუფთავება
    for col in ['ვალები', 'ავანსები']:
        df1[col] = df1[col].astype(str).str.replace(r'[^0-9.]', '', regex=True)
        df1[col] = pd.to_numeric(df1[col], errors='coerce').fillna(0)
    
    with st.spinner('მუშავდება...'):
        df1[['ტელეფონი', 'შენიშვნა']] = df1.apply(lambda row: pd.Series(match_phone(row, df2)), axis=1)
        df1['შენიშვნა'] = df1['შენიშვნა'].fillna('').replace('nan', '')

    # --- პრევიუ ---
    st.subheader("📋 პრევიუ")
    for p in df1['პროექტის დასახელება'].unique():
        with st.expander(f"📁 {p}"):
            st.dataframe(df1[df1['პროექტის დასახელება'] == p][['სახელი გვარი', 'პირადი ნომერი', 'ვალები', 'ავანსები', 'ტელეფონი', 'შენიშვნა']])

    if st.button("🚀 PDF-ის გენერირება"):
        pdf_bytes = generate_pdf(df1)
        st.download_button("📥 გადმოწერეთ PDF", data=bytes(pdf_bytes), file_name="Report_AC.pdf", mime="application/pdf")
