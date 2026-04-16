import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import re
import difflib # სახელების მსგავსების შესამოწმებლად

# გვერდის კონფიგურაცია
st.set_page_config(page_title="Accounting Automation By A/C", layout="wide")

def is_name_similar(name1, name2):
    """ამოწმებს სახელების მსგავსებას (ნებადართულია 1-2 სიმბოლოს სხვაობა)"""
    name1 = str(name1).strip().lower()
    name2 = str(name2).strip().lower()
    # SequenceMatcher ითვლის მსგავსების კოეფიციენტს (0-დან 1-მდე)
    ratio = difflib.SequenceMatcher(None, name1, name2).ratio()
    return ratio > 0.85 # 0.85 ნიშნავს დაახლოებით 1-2 სიმბოლოს სხვაობას

def match_phone(row, phone_df):
    """იერარქიული ძებნა: სახელი (მსგავსი) + ID (11 -> 7 -> 4)"""
    p_nomeri = str(row['პირადი ნომერი']).strip()
    target_name = str(row['სახელი გვარი']).strip()
    
    # ვფილტრავთ იმ ხალხს, ვისი სახელიც ჰგავს სამიზნე სახელს
    potential_matches = phone_df[phone_df['სახელი გვარი'].apply(lambda x: is_name_similar(x, target_name))]
    
    if potential_matches.empty:
        return "სახელი ვერ მოიძებნა", ""

    # ახლა ვამოწმებთ პირად ნომრებს პოტენციურ დამთხვევებში
    # 1. 11 ნიშნა (ზუსტი)
    match = potential_matches[potential_matches['პირადი ნომერი'].astype(str).str.strip() == p_nomeri]
    if not match.empty:
        return match.iloc[0]['ტელეფონი'], match.iloc[0].get('შენიშვნა', '')

    # 2. ბოლო 7 ნიშნა
    if len(p_nomeri) >= 7:
        last_7 = p_nomeri[-7:]
        match = potential_matches[potential_matches['პირადი ნომერი'].astype(str).str.endswith(last_7)]
        if not match.empty:
            return match.iloc[0]['ტელეფონი'], match.iloc[0].get('შენიშვნა', '')

    # 3. ბოლო 4 ნიშნა
    if len(p_nomeri) >= 4:
        last_4 = p_nomeri[-4:]
        match = potential_matches[potential_matches['პირადი ნომერი'].astype(str).str.endswith(last_4)]
        if not match.empty:
            return match.iloc[0]['ტელეფონი'], match.iloc[0].get('შენიშვნა', '')

    return "ნომერი არ მოიძებნა", ""

def generate_pdf(df, totals):
    pdf = FPDF()
    pdf.add_page()
    
    # ფონტის რეგისტრაცია
    try:
        pdf.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
        pdf.set_font('DejaVu', size=12)
    except:
        st.error("ფონტი 'dejavu-sans.book.ttf' ვერ მოიძებნა!")
        pdf.set_font('Arial', size=12)

    # საწყისი გვერდი: შეჯამება
    pdf.cell(200, 10, txt="ბუღალტრული ანგარიში - By A/C", ln=True, align='C')
    pdf.ln(10)
    
    # შეჯამების ცხრილი
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(80, 10, "პროექტი", 1, 0, 'C', True)
    pdf.cell(55, 10, "ვალები (ჯამი)", 1, 0, 'C', True)
    pdf.cell(55, 10, "ავანსები (ჯამი)", 1, 1, 'C', True)
    
    for proj, data in totals.items():
        pdf.cell(80, 10, str(proj), 1)
        pdf.cell(55, 10, f"{data['debts']:.2f}", 1)
        pdf.cell(55, 10, f"{data['adv']:.2f}", 1, 1)

    # პროექტების მიხედვით დაყოფა
    for project in df['პროექტის დასახელება'].unique():
        pdf.add_page()
        pdf.set_font('DejaVu', size=14)
        pdf.cell(200, 10, txt=f"პროექტი: {project}", ln=True)
        pdf.set_font('DejaVu', size=10)
        
        proj_df = df[df['პროექტის დასახელება'] == project]
        
        # მევალეები
        debtors = proj_df[proj_df['ვალები'] > 0]
        if not debtors.empty:
            pdf.ln(5)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(200, 8, txt="მევალეების სია:", ln=True)
            for _, r in debtors.iterrows():
                line = f"{r['სახელი გვარი']} | ID: {r['პირადი ნომერი']} | ტელ: {r['ტელეფონი']} | ვალი: {r['ვალები']} | შენიშვნა: {r['შენიშვნა']}"
                pdf.multi_cell(0, 7, txt=line)
            pdf.cell(0, 8, txt=f"ჯამური ვალი: {debtors['ვალები'].sum():.2f}", ln=True)

        # ავანსები
        advances = proj_df[proj_df['ავანსები'] > 0]
        if not advances.empty:
            pdf.ln(5)
            pdf.set_text_color(0, 120, 0)
            pdf.cell(200, 8, txt="ავანსების სია:", ln=True)
            for _, r in advances.iterrows():
                line = f"{r['სახელი გვარი']} | ID: {r['პირადი ნომერი']} | ავანსი: {r['ავანსები']}"
                pdf.cell(0, 7, txt=line, ln=True)

    return pdf.output()

# --- Streamlit UI ---
st.title("📂 Accounting & Data Matching Tool")

f_debt = st.file_uploader("ატვირთეთ prnValiSagad1.csv", type=['csv'])
f_phone = st.file_uploader("ატვირთეთ valebi.csv", type=['csv'])

if f_debt and f_phone:
    df1 = pd.read_csv(f_debt)
    df2 = pd.read_csv(f_phone)
    
    # ავანსების დამუშავება
    # ავანსების დამუშავების უფრო უსაფრთხო გზა
    if 'ავანსები' in df1.columns:
        # ჯერ ვასუფთავებთ ფრჩხილებისგან, მერე ვცვლით ცარიელებს 0-ით
        df1['ავანსები'] = df1['ავანსები'].astype(str).str.replace(r'[\(\)]', '', regex=True)
        df1['ავანსები'] = pd.to_numeric(df1['ავანსები'], errors='coerce').fillna(0)
    
    # იერარქიული დამუშავება
    with st.spinner('მიმდინარეობს ძებნა (სახელების მსგავსება + ID)...'):
        df1[['ტელეფონი', 'შენიშვნა']] = df1.apply(lambda row: pd.Series(match_phone(row, df2)), axis=1)
    
    st.subheader("🔍 შედეგების წინასწარი ნახვა")
    st.dataframe(df1, use_container_width=True)
    
    # ჯამების მომზადება
    summary = {}
    for p in df1['პროექტის დასახელება'].unique():
        sub = df1[df1['პროექტის დასახელება'] == p]
        summary[p] = {'debts': sub['ვალები'].sum(), 'adv': sub['ავანსები'].sum()}

    if st.button("📄 PDF რეპორტის გენერირება"):
        pdf_bytes = generate_pdf(df1, summary)
        st.download_button("📥 ჩამოტვირთვა", data=pdf_bytes, file_name="Report_AC.pdf", mime="application/pdf")
