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
  padding: 2rem;
  margin-bottom: 1.5rem;
}
.hero-title { font-family: 'Playfair Display', serif; font-size: 2.2rem; color: var(--white); }
.section-title { font-family: 'Playfair Display', serif; font-size: 1.2rem; color: var(--white); border-bottom: 1px solid rgba(212,175,55,.3); padding-bottom: .4rem; margin: 1.5rem 0; }
.stButton > button { background: var(--gold) !important; color: var(--navy) !important; font-weight: 700 !important; }
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
#  PDF GENERATOR
# ─────────────────────────────────────────────
NAVY = (13, 27, 42); NAVY2 = (26, 46, 69); NAVY3 = (36, 59, 85)
GOLD = (212, 175, 55); CREAM = (245, 240, 232); WHITE = (255, 255, 255)
CRIMSON = (192, 57, 43); CRIMSON_LIGHT = (231, 76, 60)
EMERALD = (26, 122, 74); EMERALD_LIGHT = (39, 174, 96); SILVER = (189, 195, 199)

class ProfessionalPDF(FPDF):
    def __init__(self, report_date, total_debts, total_advances):
        super().__init__('P', 'mm', 'A4')
        self.report_date = report_date
        self.total_debts = total_debts
        self.total_adv = total_advances
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=22)
        try:
            self.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
            self.add_font('DejaVu', 'B', 'dejavu-sans.book.ttf')
            self._font = 'DejaVu'
        except:
            self._font = 'Arial'

    def _sf(self, size=10, bold=False):
        style = 'B' if bold else ''
        self.set_font(self._font, style, size)

    def header(self):
        if self.page_no() > 1:
            self.set_fill_color(*NAVY)
            self.rect(0, 0, 210, 12, 'F')
            self._sf(7)
            self.set_text_color(*GOLD)
            self.set_xy(15, 3)
            self.cell(90, 6, 'A/C FINANCIAL INTELLIGENCE REPORT', 0, 0, 'L')
            self.set_text_color(*SILVER)
            self.set_xy(105, 3)
            self.cell(90, 6, self.report_date, 0, 0, 'R')

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(*GOLD)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        self._sf(7)
        self.set_text_color(*SILVER)
        self.cell(0, 5, f'CONFIDENTIAL — Page {self.page_no()}', 0, 0, 'C')

    def draw_dashboard(self, summary_df, project_count):
        self.add_page()
        self.set_fill_color(*NAVY); self.rect(0, 0, 210, 297, 'F')
        self.set_fill_color(*GOLD); self.rect(0, 0, 5, 60, 'F')
        
        self._sf(28, bold=True); self.set_text_color(*WHITE)
        self.set_xy(12, 12); self.cell(0, 12, 'A/C', 0, 2, 'L')
        self._sf(9); self.set_text_color(*GOLD); self.cell(0, 6, 'FINANCIAL INTELLIGENCE REPORT', 0, 2, 'L')
        
        y_kpi = 50
        card_w = 35; x_start = 15
        metrics = [('DEBTS', self.total_debts, CRIMSON_LIGHT), ('ADVANCES', self.total_adv, EMERALD_LIGHT)]
        for i, (lab, val, col) in enumerate(metrics):
            x = x_start + i * (card_w + 5)
            self.set_fill_color(*NAVY2); self.rect(x, y_kpi, card_w, 25, 'FD')
            self.set_fill_color(*col); self.rect(x, y_kpi, card_w, 1.5, 'F')
            self._sf(6); self.set_text_color(*SILVER); self.set_xy(x+2, y_kpi+4); self.cell(card_w-4, 4, lab, 0, 2, 'C')
            self._sf(9, bold=True); self.set_text_color(*WHITE); self.cell(card_w-4, 6, f"{val:,.0f}", 0, 2, 'C')

    def draw_project_page(self, proj_name, debtors_df, advances_df):
        self.add_page()
        self.set_fill_color(*NAVY2); self.rect(15, 15, 180, 12, 'F')
        self._sf(11, bold=True); self.set_text_color(*WHITE)
        self.set_xy(20, 17); self.cell(170, 8, clean_str(proj_name, 60), 0, 1, 'L')
        
        y = 35
        if not debtors_df.empty:
            self.set_xy(15, y); self._sf(9, True); self.set_text_color(*CRIMSON_LIGHT); self.cell(0, 8, "DEBTORS", 0, 1)
            self._sf(7); self.set_text_color(*WHITE)
            for _, r in debtors_df.head(20).iterrows():
                self.cell(100, 6, clean_str(r['სახელი გვარი'], 40), 1)
                self.cell(40, 6, f"{r['ვალები']:,.2f}", 1, 1, 'R')

def generate_pdf(df):
    report_date = datetime.now().strftime('%d %B %Y | %H:%M')
    summary = df.groupby('პროექტის დასახელება').agg(ვალი=('ვალები','sum'), ავანსი=('ავანსები','sum')).reset_index()
    
    pdf = ProfessionalPDF(report_date, summary['ვალი'].sum(), summary['ავანსი'].sum())
    pdf.draw_dashboard(summary, len(summary))
    
    for proj in df['პროექტის დასახელება'].unique():
        p_df = df[df['პროექტის დასახელება'] == proj]
        pdf.draw_project_page(proj, p_df[p_df['ვალები']>0], p_df[p_df['ავანსები']>0])
    
    return pdf.output()

# ─────────────────────────────────────────────
#  STREAMLIT UI
# ─────────────────────────────────────────────
st.markdown('<div class="hero-banner"><div class="hero-title">A/C Financial Intelligence</div></div>', unsafe_allow_html=True)

f1 = st.file_uploader("Receivables CSV", type=['csv'])
f2 = st.file_uploader("Contacts CSV", type=['csv'])

if f1 and f2:
    df1 = pd.read_csv(f1); df2 = pd.read_csv(f2)
    for col in ['ვალები', 'ავანსები']: df1[col] = df1[col].apply(safe_float)
    
    df1[['ტელეფონი', 'შენიშვნა']] = df1.apply(lambda row: pd.Series(match_phone(row, df2)), axis=1)
    
    st.markdown('<div class="section-title">Analysis Ready</div>', unsafe_allow_html=True)
    if st.button("🚀 Generate PDF Report"):
        with st.spinner("Creating PDF..."):
            pdf_data = generate_pdf(df1)
            st.download_button("📥 Download PDF", data=pdf_data, file_name="AC_Report.pdf", mime="application/pdf")
