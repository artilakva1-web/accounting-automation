import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import re
import difflib

st.set_page_config(page_title="Accounting Automation By A/C", layout="wide")

def is_name_similar(name1, name2):
    n1, n2 = str(name1).strip().lower(), str(name2).strip().lower()
    return difflib.SequenceMatcher(None, n1, n2).ratio() > 0.90 # 90% მსგავსება

def match_phone(row, phone_df):
    try:
        debt_val = float(row.get('ვალები', 0))
    except:
        debt_val = 0
    
    # ავანსებზე ნომერი არ გვინდა
    if debt_val <= 0:
        return "", ""
        
    target_name = str(row['სახელი გვარი']).strip()
    p_nomeri = str(row['პირადი ნომერი']).strip()
    
    # 1. ვეძებთ ყველა მსგავს სახელს
    matches = phone_df[phone_df['სახელი გვარი'].apply(lambda x: is_name_similar(x, target_name))]
    
    if matches.empty:
        return "ნომერი ვერ მოიძებნა", ""
    
    # 2. თუ მხოლოდ ერთი ასეთი სახელი იპოვა - პირდაპირ ვაბამთ
    if len(matches) == 1:
        return matches.iloc[0]['ტელეფონი'], matches.iloc[0].get('შენიშვნა', '')
    
    # 3. თუ რამდენიმე იპოვა - მაშინ ვიწყებთ პირადი ნომრით ფილტრაციას (11->7->4)
    for length in [11, 7, 4]:
        if len(p_nomeri) >= length:
            suffix = p_nomeri[-length:]
            sub_match = matches[matches['პირადი ნომერი'].astype(str).str.endswith(suffix)]
            if not sub_match.empty:
                return sub_match.iloc[0]['ტელეფონი'], sub_match.iloc[0].get('შენიშვნა', '')
                
    return "დუბლიკატია / ID არ ემთხვევა", ""

def generate_pdf(df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    try:
        pdf.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
        pdf.set_font('DejaVu', size=10)
    except:
        pdf.set_font('Arial', size=10)

    # გვერდი 1: მთავარი შეჯამება
    pdf.add_page()
    pdf.set_font('DejaVu', size=16)
    pdf.cell(0, 15, "მთავარი შეჯამება - By A/C", ln=True, align='C')
    pdf.set_font('DejaVu', size=11)
    
    # შეჯამების ცხრილი
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(80, 10, "პროექტის დასახელება", 1, 0, 'C', True)
    pdf.cell(55, 10, "ჯამური ვალები", 1, 0, 'C', True)
    pdf.cell(55, 10, "ჯამური ავანსები", 1, 1, 'C', True)
    
    for proj in df['პროექტის დასახელება'].unique():
        sub = df[df['პროექტის დასახელება'] == proj]
        d_sum = sub['ვალები'].sum()
        a_sum = sub['ავანსები'].sum()
        
        pdf.cell(80, 10, str(proj), 1)
        pdf.set_text_color(200, 0, 0) # წითელი ვალებისთვის
        pdf.cell(55, 10, f"{d_sum:,.2f} ₾", 1, 0, 'R')
        pdf.set_text_color(0, 120, 0) # მწვანე ავანსებისთვის
        pdf.cell(55, 10, f"({a_sum:,.2f}) ₾", 1, 1, 'R')
        pdf.set_text_color(0, 0, 0)

    # დეტალური გვერდები
    for proj in df['პროექტის დასახელება'].unique():
        pdf.add_page()
        pdf.set_font('DejaVu', size=14)
        pdf.cell(0, 10, f"პროექტი: {proj}", ln=True)
        
        proj_df = df[df['პროექტის დასახელება'] == proj]
        
        # --- მევალეების სექცია ---
        debtors = proj_df[proj_df['ვალები'] > 0]
        if not debtors.empty:
            pdf.set_font('DejaVu', size=11)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 10, "მევალეები", ln=True)
            pdf.set_font('DejaVu', size=9)
            pdf.set_text_color(0, 0, 0)
            
            # Header
            pdf.set_fill_color(255, 240, 240)
            pdf.cell(50, 8, "სახელი გვარი", 1, 0, 'C', True)
            pdf.cell(30, 8, "პირადი №", 1, 0, 'C', True)
            pdf.cell(30, 8, "ვალი (₾)", 1, 0, 'C', True)
            pdf.cell(30, 8, "ტელეფონი", 1, 0, 'C', True)
            pdf.cell(50, 8, "შენიშვნა", 1, 1, 'C', True)
            
            for _, r in debtors.iterrows():
                pdf.cell(50, 7, str(r['სახელი გვარი'])[:25], 1)
                pdf.cell(30, 7, str(r['პირადი ნომერი']), 1)
                pdf.cell(30, 7, f"{r['ვალები']:.2f}", 1, 0, 'R')
                pdf.cell(30, 7, str(r['ტელეფონი']), 1)
                pdf.cell(50, 7, str(r['შენიშვნა'])[:30], 1, 1)
            
            pdf.set_font('DejaVu', size=10, style='B')
            pdf.cell(0, 8, f"მევალეების ჯამი: {debtors['ვალები'].sum():,.2f} ₾", ln=True)

        # --- ავანსების სექცია ---
        advances = proj_df[proj_df['ავანსები'] > 0]
        if not advances.empty:
            pdf.ln(5)
            pdf.set_font('DejaVu', size=11)
            pdf.set_text_color(0, 120, 0)
            pdf.cell(0, 10, "ავანსები", ln=True)
            pdf.set_font('DejaVu', size=9)
            pdf.set_text_color(0, 0, 0)
            
            # Header
            pdf.set_fill_color(240, 255, 240)
            pdf.cell(70, 8, "სახელი გვარი", 1, 0, 'C', True)
            pdf.cell(50, 8, "პირადი №", 1, 0, 'C', True)
            pdf.cell(40, 8, "ავანსი (₾)", 1, 1, 'C', True)
            
            for _, r in advances.iterrows():
                pdf.cell(70, 7, str(r['სახელი გვარი'])[:35], 1)
                pdf.cell(50, 7, str(r['პირადი ნომერი']), 1)
                pdf.cell(40, 7, f"({r['ავანსები']:.2f})", 1, 1, 'R')
            
            pdf.set_font('DejaVu', size=10, style='B')
            pdf.cell(0, 8, f"ავანსების ჯამი: ({advances['ავანსები'].sum():,.2f}) ₾", ln=True)

    return pdf.output()

# --- STREAMLIT UI ---
st.title("📊 Accounting Management By A/C")

f1 = st.file_uploader("ატვირთეთ prnValiSagad1.csv", type=['csv'])
f2 = st.file_uploader("ატვირთეთ valebi.csv", type=['csv'])

if f1 and f2:
    df1 = pd.read_csv(f1)
    df2 = pd.read_csv(f2)
    
    # წმენდა
    for col in ['ვალები', 'ავანსები']:
        df1[col] = df1[col].astype(str).str.replace(r'[\(\)]', '', regex=True)
        df1[col] = pd.to_numeric(df1[col], errors='coerce').fillna(0)
    
    with st.spinner('მიმდინარეობს მონაცემების დამუშავება...'):
        df1[['ტელეფონი', 'შენიშვნა']] = df1.apply(lambda row: pd.Series(match_phone(row, df2)), axis=1)
    
    # Preview-სთვის მხოლოდ საჭირო სვეტები
    st.subheader("📋 პროექტების ჩამონათვალი")
    for p in df1['პროექტის დასახელება'].unique():
        with st.expander(f"📁 პროექტი: {p}"):
            p_df = df1[df1['პროექტის დასახელება'] == p]
            # ვაჩვენებთ მხოლოდ თქვენს მიერ მოთხოვნილ სვეტებს
            st.dataframe(p_df[['სახელი გვარი', 'პირადი ნომერი', 'ვალები', 'ავანსები', 'ტელეფონი', 'შენიშვნა']])

    if st.button("🚀 PDF რეპორტის გენერირება"):
        # generate_pdf ახლა აბრუნებს bytes-ს სწორად
        pdf_out = generate_pdf(df1)
        st.download_button("📥 გადმოწერეთ PDF", data=bytes(pdf_out), file_name="Report_AC.pdf", mime="application/pdf")
