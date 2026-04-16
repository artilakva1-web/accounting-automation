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
    # უსაფრთხოების შემოწმება: ვაქცევთ რიცხვად, თუ ვერ ხდება - ვთვლით რომ 0-ია
    try:
        debt_val = float(row.get('ვალები', 0))
    except:
        debt_val = 0
        
    # თუ ვალი არ აქვს (ავანსია), ნომერი არ გვჭირდება
    if debt_val <= 0:
        return "", ""
        
    p_nomeri = str(row['პირადი ნომერი']).strip()
    target_name = str(row['სახელი გვარი']).strip()
    
    potential_matches = phone_df[phone_df['სახელი გვარი'].apply(lambda x: is_name_similar(x, target_name))]
    
    if potential_matches.empty:
        return "ნომერი არ მოიძებნა", ""

    # იერარქია: 11 -> 7 -> 4
    for length in [11, 7, 4]:
        if len(p_nomeri) >= length:
            suffix = p_nomeri[-length:]
            match = potential_matches[potential_matches['პირადი ნომერი'].astype(str).str.endswith(suffix)]
            if not match.empty:
                return match.iloc[0]['ტელეფონი'], match.iloc[0].get('შენიშვნა', '')
                
    return "ნომერი არ მოიძებნა", ""

def generate_pdf(df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    try:
        pdf.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
        pdf.set_font('DejaVu', size=10)
    except:
        pdf.set_font('Arial', size=10)

    projects = df['პროექტის დასახელება'].unique()
    
    for proj_name in projects:
        pdf.add_page()
        # პროექტის სათაური
        pdf.set_font('DejaVu', size=14)
        pdf.cell(0, 10, f"პროექტი: {proj_name}", ln=True, align='L')
        pdf.ln(2)
        
        # ცხრილის თავფურცელი (თქვენი სტრუქტურა)
        pdf.set_font('DejaVu', size=9)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(50, 8, "სახელი გვარი", 1, 0, 'C', True)
        pdf.cell(30, 8, "პირადი №", 1, 0, 'C', True)
        pdf.cell(30, 8, "თანხა (₾)", 1, 0, 'C', True)
        pdf.cell(30, 8, "ტელეფონი", 1, 0, 'C', True)
        pdf.cell(50, 8, "შენიშვნა", 1, 1, 'C', True)
        
        proj_df = df[df['პროექტის დასახელება'] == proj_name]
        
        for _, r in proj_df.iterrows():
            # განვსაზღვროთ რა დაიწეროს თანხაში
            debt = float(r['ვალები'])
            adv = float(r['ავანსები'])
            display_money = f"{debt:.2f}" if debt > 0 else f"({adv:.2f})"
            
            # ფერის შერჩევა: მევალე წითლად, ავანსი მწვანედ
            if debt > 0:
                pdf.set_text_color(200, 0, 0)
            else:
                pdf.set_text_color(0, 120, 0)
            
            pdf.cell(50, 7, str(r['სახელი გვარი'])[:25], 1)
            pdf.set_text_color(0, 0, 0) # დანარჩენი ტექსტი შავად
            pdf.cell(30, 7, str(r['პირადი ნომერი']), 1)
            pdf.cell(30, 7, display_money, 1, 0, 'R')
            pdf.cell(30, 7, str(r['ტელეფონი']), 1)
            pdf.cell(50, 7, str(r['შენიშვნა'])[:30], 1, 1)
            
    return pdf.output()

# --- Streamlit UI ---
st.title("📊 Accounting By A/C")

f1 = st.file_uploader("ატვირთეთ prnValiSagad1.csv", type=['csv'])
f2 = st.file_uploader("ატვირთეთ valebi.csv", type=['csv'])

if f1 and f2:
    df1 = pd.read_csv(f1)
    df2 = pd.read_csv(f2)
    
    # მონაცემების გასუფთავება (ვალები და ავანსები)
    for col in ['ვალები', 'ავანსები']:
        if col in df1.columns:
            df1[col] = df1[col].astype(str).str.replace(r'[\(\)]', '', regex=True)
            df1[col] = pd.to_numeric(df1[col], errors='coerce').fillna(0)
    
    # დამუშავება
    with st.spinner('მიმდინარეობს იდენტიფიცირება...'):
        df1[['ტელეფონი', 'შენიშვნა']] = df1.apply(lambda row: pd.Series(match_phone(row, df2)), axis=1)
    
    st.subheader("📋 წინასწარი ნახვა")
    st.dataframe(df1)

    if st.button("🖨️ PDF-ის შექმნა"):
        pdf_bytes = generate_pdf(df1)
        st.download_button("📥 ჩამოტვირთვა", data=pdf_bytes, file_name="Report.pdf", mime="application/pdf")
