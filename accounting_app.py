import streamlit as st
import pandas as pd
import difflib
from datetime import datetime
import plotly.graph_objects as go
from fpdf import FPDF
import math

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="A/C Financial Intelligence",
    page_icon="📊",
    layout="wide",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600&display=swap');
:root {
  --navy:   #0D1B2A;
  --navy2:  #1A2E45;
  --navy3:  #243B55;
  --crimson:#C0392B;
  --emerald:#1A7A4A;
  --gold:   #D4AF37;
  --white:  #FFFFFF;
  --cream:  #F5F0E8;
  --silver: #BDC3C7;
}
html, body, [data-testid="stAppViewContainer"] {
  background: var(--navy) !important;
  color: var(--cream) !important;
  font-family: 'DM Sans', sans-serif;
}
[data-testid="stSidebar"] { background: var(--navy2) !important; }
.hero-banner {
  background: linear-gradient(135deg, var(--navy2) 0%, var(--navy3) 60%, #1e3a5f 100%);
  border-left: 4px solid var(--gold);
  padding: 2rem 2.5rem;
  margin-bottom: 1.5rem;
}
.hero-title { font-family: 'Playfair Display', serif; font-size: 2.2rem; font-weight: 700; color: var(--white); margin: 0; }
.section-title { font-family: 'Playfair Display', serif; font-size: 1.15rem; color: var(--white); border-bottom: 1px solid rgba(212,175,55,.3); padding-bottom: .4rem; margin: 1.5rem 0 .8rem; }
.stButton > button { background: var(--gold) !important; color: var(--navy) !important; font-weight: 700 !important; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CORE LOGIC
# ─────────────────────────────────────────────
def safe_float(value):
    try:
        cleaned = str(value).replace('(', '').replace(')', '').replace(',', '').strip()
        return float(cleaned)
    except:
        return 0.0

def is_name_similar(name1, name2):
    n1, n2 = str(name1).strip().lower(), str(name2).strip().lower()
    return difflib.SequenceMatcher(None, n1, n2).ratio() > 0.90

def match_phone(row, phone_df):
    debt_val = safe_float(row.get('ვალები', 0))
    if debt_val <= 0: return "", ""
    target_name = str(row['სახელი გვარი']).strip()
    p_nomeri = str(row['პირადი ნომერი']).strip()
    matches = phone_df[phone_df['სახელი გვარი'].apply(lambda x: is_name_similar(x, target_name))]
    if matches.empty: return "ნომერი ვერ მოიძებნა", ""
    if len(matches) == 1:
        sh_val = str(matches.iloc[0].get('შენიშვნა', ''))
        return matches.iloc[0]['ტელეფონი'], "" if sh_val.lower() == 'nan' else sh_val
    for length in [11, 7, 4]:
        if len(p_nomeri) >= length:
            suffix = p_nomeri[-length:]
            sub_match = matches[matches['პირადი ნომერი'].astype(str).str.endswith(suffix)]
            if not sub_match.empty:
                sh_val = str(sub_match.iloc[0].get('შენიშვნა', ''))
                return sub_match.iloc[0]['ტელეფონი'], "" if sh_val.lower() == 'nan' else sh_val
    return "დუბლიკატია", ""

def clean_str(val, max_len=None):
    s = str(val).strip()
    if s.lower() in ('nan', 'none', ''): return ''
    if max_len and len(s) > max_len: return s[:max_len - 1] + '…'
    return s

# ─────────────────────────────────────────────
#  PROFESSIONAL PDF CLASS (UTF-8 SUPPORT)
# ─────────────────────────────────────────────
NAVY = (13, 27, 42); GOLD = (212, 175, 55); WHITE = (255, 255, 255); SILVER = (189, 195, 199)

class ProfessionalPDF(FPDF):
    def __init__(self, report_date, total_debts, total_advances):
        super().__init__('P', 'mm', 'A4')
        self.report_date = report_date
        self.total_debts = total_debts
        self.total_adv = total_advances
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=22)
        
        # ქართული შრიფტის რეგისტრაცია
        try:
            self.add_font('DejaVu', '', 'dejavu-sans.book.ttf', uni=True)
            self.add_font('DejaVu', 'B', 'dejavu-sans.book.ttf', uni=True)
            self._font = 'DejaVu'
        except:
            st.error("ფონტი 'dejavu-sans.book.ttf' ვერ მოიძებნა. ატვირთეთ ფაილი GitHub-ზე.")
            self._font = 'Arial'

    def _sf(self, size=10, bold=False):
        style = 'B' if bold else ''
        self.set_font(self._font, style, size)

    def header(self):
        if self.page_no() > 1:
            self.set_fill_color(*NAVY)
            self.rect(0, 0, 210, 12, 'F')
            self._sf(7); self.set_text_color(*GOLD)
            self.set_xy(15, 3); self.cell(90, 6, 'A/C FINANCIAL INTELLIGENCE', 0, 0, 'L')
            self.set_text_color(*SILVER); self.set_xy(105, 3); self.cell(90, 6, self.report_date, 0, 0, 'R')

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(*GOLD); self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2); self._sf(7); self.set_text_color(*SILVER)
        self.cell(0, 5, f'CONFIDENTIAL — Page {self.page_no()}', 0, 0, 'C')

    def draw_dashboard(self, summary_df):
        self.add_page()
        self.set_fill_color(*NAVY); self.rect(0, 0, 210, 297, 'F')
        self.set_fill_color(*GOLD); self.rect(0, 0, 5, 60, 'F')
        
        self.set_xy(12, 12); self._sf(26, True); self.set_text_color(*WHITE); self.cell(0, 12, 'A/C', 0, 2, 'L')
        self._sf(9); self.set_text_color(*GOLD); self.cell(0, 6, 'FINANCIAL INTELLIGENCE REPORT', 0, 2, 'L')
        self._sf(7); self.set_text_color(*SILVER); self.cell(0, 5, f'GENERATED: {self.report_date}', 0, 2, 'L')

        # KPI Cards
        y_kpi = 55
        self.set_fill_color(26, 46, 69) # NAVY2
        self.rect(15, y_kpi, 85, 25, 'F'); self.rect(110, y_kpi, 85, 25, 'F')
        
        self.set_xy(15, y_kpi + 5); self._sf(8); self.set_text_color(*SILVER); self.cell(85, 5, 'TOTAL DEBTS', 0, 2, 'C')
        self._sf(12, True); self.set_text_color(231, 76, 60); self.cell(85, 8, f"{self.total_debts:,.2f} GEL", 0, 0, 'C')
        
        self.set_xy(110, y_kpi + 5); self._sf(8); self.set_text_color(*SILVER); self.cell(85, 5, 'TOTAL ADVANCES', 0, 2, 'C')
        self._sf(12, True); self.set_text_color(39, 174, 96); self.cell(85, 8, f"({self.total_adv:,.2f}) GEL", 0, 0, 'C')

    def draw_project_page(self, proj_name, debtors_df, advances_df):
        self.add_page()
        self.set_fill_color(26, 46, 69); self.rect(15, 15, 180, 12, 'F')
        self.set_fill_color(*GOLD); self.rect(15, 15, 3, 12, 'F')
        self.set_xy(20, 17); self._sf(10, True); self.set_text_color(*WHITE)
        self.cell(170, 8, clean_str(proj_name, 70), 0, 1, 'L')
        
        y = 35
        if not debtors_df.empty:
            self.set_xy(15, y); self._sf(9, True); self.set_text_color(231, 76, 60); self.cell(0, 8, "▸ DEBTORS", 0, 1)
            self._sf(7); self.set_text_color(50, 50, 50)
            col_w = [80, 40, 30, 30]
            # Headers
            self.set_fill_color(230, 230, 230)
            for h, w in zip(['NAME', 'ID', 'DEBT', 'PHONE'], col_w): self.cell(w, 7, h, 1, 0, 'C', True)
            self.ln()
            # Rows
            for _, r in debtors_df.iterrows():
                self.cell(col_w[0], 6, clean_str(r['სახელი გვარი'], 40), 1)
                self.cell(col_w[1], 6, clean_str(r['პირადი ნომერი'], 20), 1, 0, 'C')
                self.cell(col_w[2], 6, f"{r['ვალები']:,.2f}", 1, 0, 'R')
                self.cell(col_w[3], 6, clean_str(r.get('ტელეფონი', ''), 15), 1, 1, 'C')

def generate_pdf(df):
    report_date = datetime.now().strftime('%d %B %Y | %H:%M')
    summary = df.groupby('პროექტის დასახელება').agg(ვალი=('ვალები','sum'), ავანსი=('ავანსები','sum')).reset_index()
    
    pdf = ProfessionalPDF(report_date, summary['ვალი'].sum(), summary['ავანსი'].sum())
    pdf.draw_dashboard(summary)
    
    for proj in df['პროექტის დასახელება'].unique():
        p_df = df[df['პროექტის დასახელება'] == proj]
        pdf.draw_project_page(proj, p_df[p_df['ვალები']>0], p_df[p_df['ავანსები']>0])
    
    # fpdf2-ში bytes() კონვერტაცია უზრუნველყოფს Streamlit-თან თავსებადობას
    return bytes(pdf.output())

# ─────────────────────────────────────────────
#  STREAMLIT UI
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <div class="hero-title">A/C Financial Intelligence</div>
  <div style="width:60px;height:2px;background:var(--gold);margin:0.8rem 0;"></div>
  <p style="color:var(--silver);font-size:0.9rem;text-transform:uppercase;letter-spacing:0.12em;margin:0;">Accounts Receivable & Advance Analytics</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1: f1 = st.file_uploader("Receivables CSV (prnValiSagad1)", type=['csv'])
with col2: f2 = st.file_uploader("Contacts CSV (valebi)", type=['csv'])

if f1 and f2:
    df1 = pd.read_csv(f1); df2 = pd.read_csv(f2)
    for col in ['ვალები', 'ავანსები']: df1[col] = df1[col].apply(safe_float)
    
    with st.spinner('Enriching contact data...'):
        df1[['ტელეფონი', 'შენიშვნა']] = df1.apply(lambda row: pd.Series(match_phone(row, df2)), axis=1)

    # UI Metrics
    total_d = df1['ვალები'].sum(); total_a = df1['ავანსები'].sum()
    st.markdown('<div class="section-title">Executive Overview</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Debts", f"{total_d:,.2f} ₾")
    m2.metric("Total Advances", f"({total_a:,.2f}) ₾", delta_color="inverse")
    m3.metric("Net Position", f"{total_d - total_a:,.2f} ₾")

    # Expanders
    st.markdown('<div class="section-title">Project Details</div>', unsafe_allow_html=True)
    for p in df1['პროექტის დასახელება'].unique():
        p_df = df1[df1['პროექტის დასახელება'] == p]
        with st.expander(f"📁 {p} (Debt: {p_df['ვალები'].sum():,.0f} ₾)"):
            st.dataframe(p_df[['სახელი გვარი', 'პირადი ნომერი', 'ვალები', 'ავანსები', 'ტელეფონი', 'შენიშვნა']], use_container_width=True, hide_index=True)

    # PDF Button
    st.markdown("---")
    if st.button("🚀 Generate & Download PDF Report"):
        with st.spinner("Compiling professional report..."):
            pdf_bytes = generate_pdf(df1)
            st.download_button(
                label="📥 Click here to Download",
                data=pdf_bytes,
                file_name=f"AC_Financial_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
