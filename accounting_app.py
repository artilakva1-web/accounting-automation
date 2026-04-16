import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import re
import difflib

st.set_page_config(page_title="Accounting By A/C", layout="wide")

def is_name_similar(name1, name2):
    n1, n2 = str(name1).strip().lower(), str(name2).strip().lower()
    return difflib.SequenceMatcher(None, n1, n2).ratio() > 0.85

def match_phone(row, phone_df):
    try:
        debt_val = float(row.get('ვალები', 0))
    except:
        debt_val = 0
    
    # ავანსებზე ნომერი არ გვინდა
    if debt_val <= 0:
        return "", ""
        
    p_nomeri = str(row['პირადი ნომერი']).strip()
    target_name = str(row['სახელი გვარი']).strip()
    
    potential_matches = phone_df[phone_df['სახელი გვარი'].apply(lambda x: is_name_similar(x, target_name))]
    
    for length in [11, 7, 4]:
        if len(p_nomeri) >= length:
            suffix = p_nomeri[-length:]
            match = potential_matches[potential_matches['პირადი ნომერი'].astype(str).str.endswith(suffix)]
            if not match.empty:
                return match.iloc[0]['ტელეფონი'], match.iloc[0].get('შენიშვნა', '')
    return "ნომერი არ მოიძებნა", ""

def create_pdf_bytes(final_df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    try:
        pdf.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
        pdf.set_font('DejaVu', size=10)
    except:
        pdf.set_font('Arial', size=10)

    for proj_name in final_df['პროექტის დასახელება'].unique():
        pdf.add_page()
        pdf.set_font('DejaVu', size=14)
        pdf.cell(0, 10, f"პროექტი: {proj_name}", ln=True)
        pdf.ln(2)
        
        # ცხრილის თავფურცელი
        pdf.set_font('DejaVu', size=9)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(50, 8, "სახელი გვარი", 1, 0, 'C', True)
        pdf.cell(30, 8, "პირადი №", 1, 0, 'C', True)
        pdf.cell(30, 8, "თანხა (₾)", 1, 0, 'C', True)
        pdf.cell(30, 8, "ტელეფონი", 1, 0, 'C', True)
        pdf.cell(50, 8, "შენიშვნა", 1, 1, 'C', True)
        
        proj_rows = final_df[final_df['პროექტის დასახელება'] == proj_name]
        for _, r in proj_rows.iterrows():
            # ფერების ლოგიკა: ვალი წითლად, ავანსი მწვანედ
            is_debt = "(" not in str(r['ვალი/ავანსი(თანხა ₾)'])
            pdf.set_text_color(200, 0, 0) if is_debt else pdf.set_text_color(0, 120, 0)
            
            pdf.cell(50, 7, str(r['სახელი გვარი'])[:25], 1)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(30, 7, str(r['პირადი ნომერი']), 1)
            pdf.cell(30, 7, str(r['ვალი/ავანსი(თანხა ₾)']), 1, 0, 'R')
            pdf.cell(30, 7, str(r['ტელეფონის ნომერი']), 1)
            pdf.cell(50, 7, str(r['შენიშვნა'])[:30], 1, 1)
            
    return pdf.output()

# --- UI ---
st.title("📊 Accounting Tool - By A/C")

f1 = st.file_uploader("ატვირთეთ prnValiSagad1.csv", type=['csv'])
f2 = st.file_uploader("ატვირთეთ valebi.csv", type=['csv'])

if f1 and f2:
    df1 = pd.read_csv(f1)
    df2 = pd.read_csv(f2)
    
    # 1. მონაცემების გასუფთავება
    for col in ['ვალები', 'ავანსები']:
        df1[col] = df1[col].astype(str).str.replace(r'[\(\)]', '', regex=True)
        df1[col] = pd.to_numeric(df1[col], errors='coerce').fillna(0)
    
    # 2. იდენტიფიცირება
    with st.spinner('მუშავდება...'):
        df1[['ტელეფონი', 'შენიშვნა_valebi']] = df1.apply(lambda row: pd.Series(match_phone(row, df2)), axis=1)
    
    # 3. მხოლოდ საჭირო სტრუქტურის აწყობა (5 სვეტი)
    output_df = pd.DataFrame()
    output_df['სახელი გვარი'] = df1['სახელი გვარი']
    output_df['პირადი ნომერი'] = df1['პირადი ნომერი']
    output_df['ვალი/ავანსი(თანხა ₾)'] = df1.apply(lambda r: f"{r['ვალები']:.2f}" if r['ვალები'] > 0 else f"({r['ავანსები']:.2f})", axis=1)
    output_df['ტელეფონის ნომერი'] = df1['ტელეფონი']
    output_df['შენიშვნა'] = df1['შენიშვნა_valebi']
    output_df['პროექტის დასახელება'] = df1['პროექტის დასახელება'] # ამას ვიყენებთ დასაყოფად

    # 4. Preview (ვაჩვენებთ მხოლოდ თქვენს მიერ მოთხოვნილ 5 სვეტს)
    st.subheader("📋 წინასწარი ნახვა (მხოლოდ არჩეული სვეტები)")
    display_cols = ['სახელი გვარი', 'პირადი ნომერი', 'ვალი/ავანსი(თანხა ₾)', 'ტელეფონის ნომერი', 'შენიშვნა']
    
    # ვაჩვენებთ პროექტების მიხედვით დაყოფილ ცხრილებს ეკრანზეც
    for p in output_df['პროექტის დასახელება'].unique():
        with st.expander(f"📁 პროექტი: {p}", expanded=True):
            st.table(output_df[output_df['პროექტის დასახელება'] == p][display_cols])

    # 5. PDF გენერირება
    if st.button("🚀 PDF დოკუმენტის მომზადება"):
        try:
            pdf_data = create_pdf_bytes(output_df)
            st.download_button(
                label="📥 ჩამოტვირთეთ გამზადებული PDF",
                data=bytes(pdf_data),
                file_name="Accounting_Report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"შეცდომა PDF-ის შექმნისას: {e}")
