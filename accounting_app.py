import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import re
import difflib

st.set_page_config(page_title="Accounting By A/C", layout="wide")

def is_name_similar(name1, name2):
    name1, name2 = str(name1).strip().lower(), str(name2).strip().lower()
    return difflib.SequenceMatcher(None, name1, name2).ratio() > 0.85

def match_phone(row, phone_df):
    # მხოლოდ მევალეებისთვის ვეძებთ ნომერს
    if row['ვალები'] <= 0:
        return "", ""
        
    p_nomeri = str(row['პირადი ნომერი']).strip()
    target_name = str(row['სახელი გვარი']).strip()
    
    potential_matches = phone_df[phone_df['სახელი გვარი'].apply(lambda x: is_name_similar(x, target_name))]
    
    if potential_matches.empty:
        return "სახელი ვერ მოიძებნა", ""

    # იერარქია: 11 -> 7 -> 4
    for length in [11, 7, 4]:
        if len(p_nomeri) >= length:
            suffix = p_nomeri[-length:]
            match = potential_matches[potential_matches['პირადი ნომერი'].astype(str).str.endswith(suffix)]
            if not match.empty:
                return match.iloc[0]['ტელეფონი'], match.iloc[0].get('შენიშვნა', '')
                
    return "ნომერი არ მოიძებნა", ""

def generate_pdf(df, summary_data):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # ფონტის დამატება
    try:
        pdf.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
        pdf.set_font('DejaVu', size=11)
    except:
        pdf.set_font('Arial', size=11)

    # გვერდი 1: შეჯამება
    pdf.add_page()
    pdf.set_font('DejaVu', size=16)
    pdf.cell(0, 10, "ბუღალტრული ანგარიში - By A/C", ln=True, align='C')
    pdf.set_font('DejaVu', size=11)
    pdf.cell(0, 10, f"თარიღი: {pd.Timestamp.now().strftime('%Y-%m-%d')}", ln=True, align='C')
    pdf.ln(10)

    # შეჯამების ცხრილი
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(80, 10, "პროექტის დასახელება", 1, 0, 'C', True)
    pdf.cell(55, 10, "ვალები (ჯამი)", 1, 0, 'C', True)
    pdf.cell(55, 10, "ავანსები (ჯამი)", 1, 1, 'C', True)
    
    for proj, stats in summary_data.items():
        pdf.cell(80, 8, str(proj), 1)
        pdf.cell(55, 8, f"{stats['debts']:,.2d}", 1)
        pdf.cell(55, 8, f"{stats['adv']:,.2d}", 1, 1)

    # დეტალური გვერდები პროექტების მიხედვით
    projects = df['პროექტის დასახელება'].unique()
    for proj_name in projects:
        pdf.add_page()
        proj_df = df[df['პროექტის დასახელება'] == proj_name]
        
        pdf.set_font('DejaVu', size=14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f"პროექტი: {proj_name}", ln=True)
        pdf.ln(3)

        # 1. მევალეები (წითელი ცხრილი)
        debtors = proj_df[proj_df['ვალები'] > 0]
        if not debtors.empty:
            pdf.set_font('DejaVu', size=11)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 10, "მევალეების სია:", ln=True)
            
            # ცხრილის თავფურცელი
            pdf.set_font('DejaVu', size=9)
            pdf.set_fill_color(255, 230, 230)
            pdf.cell(50, 8, "სახელი გვარი", 1, 0, 'C', True)
            pdf.cell(35, 8, "პირადი №", 1, 0, 'C', True)
            pdf.cell(30, 8, "ტელეფონი", 1, 0, 'C', True)
            pdf.cell(25, 8, "ვალი", 1, 0, 'C', True)
            pdf.cell(50, 8, "შენიშვნა", 1, 1, 'C', True)
            
            pdf.set_text_color(0, 0, 0)
            for _, r in debtors.iterrows():
                pdf.cell(50, 7, str(r['სახელი გვარი'])[:25], 1)
                pdf.cell(35, 7, str(r['პირადი ნომერი']), 1)
                pdf.cell(30, 7, str(r['ტელეფონი']), 1)
                pdf.cell(25, 7, f"{r['ვალები']}", 1)
                pdf.cell(50, 7, str(r['შენიშვნა'])[:30], 1, 1)
            
            pdf.set_font('DejaVu', size=10)
            pdf.cell(0, 8, f"პროექტის ჯამური ვალი: {debtors['ვალები'].sum():,.2d}", ln=True)

        # 2. ავანსები (მწვანე ცხრილი)
        advances = proj_df[proj_df['ავანსები'] > 0]
        if not advances.empty:
            pdf.ln(5)
            pdf.set_text_color(0, 120, 0)
            pdf.cell(0, 10, "ავანსების სია:", ln=True)
            
            pdf.set_font('DejaVu', size=9)
            pdf.set_fill_color(230, 255, 230)
            pdf.cell(70, 8, "სახელი გვარი", 1, 0, 'C', True)
            pdf.cell(50, 8, "პირადი №", 1, 0, 'C', True)
            pdf.cell(40, 8, "ავანსი", 1, 1, 'C', True)
            
            pdf.set_text_color(0, 0, 0)
            for _, r in advances.iterrows():
                pdf.cell(70, 7, str(r['სახელი გვარი'])[:35], 1)
                pdf.cell(50, 7, str(r['პირადი ნომერი']), 1)
                pdf.cell(40, 7, f"{r['ავანსები']}", 1, 1)

    return pdf.output()

# --- Streamlit UI ---
st.title("📊 Accounting Management By A/C")

f1 = st.file_uploader("ატვირთეთ prnValiSagad1.csv", type=['csv'])
f2 = st.file_uploader("ატვირთეთ valebi.csv", type=['csv'])

if f1 and f2:
    df1 = pd.read_csv(f1)
    df2 = pd.read_csv(f2)
    
    # ავანსების გასუფთავება
    if 'ავანსები' in df1.columns:
        df1['ავანსები'] = df1['ავანსები'].astype(str).str.replace(r'[\(\)]', '', regex=True)
        df1['ავანსები'] = pd.to_numeric(df1['ავანსები'], errors='coerce').fillna(0)
    
    # მონაცემების დამუშავება
    with st.spinner('მონაცემები ჯამდება და ხდება იდენტიფიცირება...'):
        df1[['ტელეფონი', 'შენიშვნა']] = df1.apply(lambda row: pd.Series(match_phone(row, df2)), axis=1)
    
    # პროექტების სტატისტიკა შეჯამებისთვის
    summary_data = {}
    for p in df1['პროექტის დასახელება'].unique():
        p_sub = df1[df1['პროექტის დასახელება'] == p]
        summary_data[p] = {'debts': p_sub['ვალები'].sum(), 'adv': p_sub['ავანსები'].sum()}

    st.subheader("📋 წინასწარი გადახედვა (Preview)")
    st.dataframe(df1)

    if st.button("🖨️ PDF დოკუმენტის გენერირება"):
        pdf_bytes = generate_pdf(df1, summary_data)
        st.download_button("📥 ჩამოტვირთეთ ფაილი", data=pdf_bytes, file_name="Accounting_Report_AC.pdf", mime="application/pdf")
