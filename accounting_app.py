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
#  CUSTOM CSS  —  deep navy / crimson / emerald
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Root palette ── */
:root {
  --navy:   #0D1B2A;
  --navy2:  #1A2E45;
  --navy3:  #243B55;
  --crimson:#C0392B;
  --crimson-light: #E74C3C;
  --emerald:#1A7A4A;
  --emerald-light: #27AE60;
  --gold:   #D4AF37;
  --silver: #BDC3C7;
  --cream:  #F5F0E8;
  --white:  #FFFFFF;
}

/* ── Global reset ── */
html, body, [data-testid="stAppViewContainer"] {
  background: var(--navy) !important;
  color: var(--cream) !important;
  font-family: 'DM Sans', sans-serif;
}

[data-testid="stSidebar"] { background: var(--navy2) !important; }
[data-testid="stHeader"]  { background: var(--navy)  !important; }

/* ── Hero banner ── */
.hero-banner {
  background: linear-gradient(135deg, var(--navy2) 0%, var(--navy3) 60%, #1e3a5f 100%);
  border-left: 4px solid var(--gold);
  border-radius: 2px;
  padding: 2rem 2.5rem;
  margin-bottom: 1.5rem;
  position: relative;
  overflow: hidden;
}
.hero-banner::after {
  content: '';
  position: absolute;
  top: -30px; right: -30px;
  width: 180px; height: 180px;
  border-radius: 50%;
  background: rgba(212,175,55,0.06);
}
.hero-title {
  font-family: 'Playfair Display', serif;
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--white);
  letter-spacing: 0.02em;
  margin: 0 0 .3rem;
}
.hero-sub {
  font-size: .9rem;
  color: var(--silver);
  letter-spacing: .12em;
  text-transform: uppercase;
}
.gold-line {
  width: 60px; height: 2px;
  background: var(--gold);
  margin: .8rem 0;
}

/* ── KPI cards ── */
.kpi-grid { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.kpi-card {
  flex: 1;
  min-width: 160px;
  background: var(--navy2);
  border: 1px solid rgba(255,255,255,.07);
  border-top: 3px solid var(--gold);
  border-radius: 4px;
  padding: 1.2rem 1.4rem;
}
.kpi-label { font-size: .72rem; color: var(--silver); text-transform: uppercase; letter-spacing: .1em; }
.kpi-value { font-family: 'Playfair Display', serif; font-size: 1.6rem; color: var(--white); margin: .25rem 0 0; }
.kpi-value.debt  { color: #e87272; }
.kpi-value.adv   { color: #5ecb8a; }
.kpi-value.ratio { color: var(--gold); }

/* ── Section titles ── */
.section-title {
  font-family: 'Playfair Display', serif;
  font-size: 1.15rem;
  color: var(--white);
  border-bottom: 1px solid rgba(212,175,55,.3);
  padding-bottom: .4rem;
  margin: 1.5rem 0 .8rem;
  letter-spacing: .03em;
}

/* ── Expanders ── */
[data-testid="stExpander"] summary {
  font-family: 'DM Sans', sans-serif;
  font-weight: 600;
  color: var(--cream);
  background: var(--navy2);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 3px;
}
[data-testid="stExpander"] { background: var(--navy2); border-radius: 3px; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--navy2);
  border: 1px dashed rgba(212,175,55,.4);
  border-radius: 4px;
  padding: .5rem;
}

/* ── Button ── */
[data-testid="baseButton-primary"],
.stButton > button {
  background: var(--gold) !important;
  color: var(--navy) !important;
  font-weight: 700 !important;
  font-family: 'DM Sans', sans-serif !important;
  border: none !important;
  border-radius: 2px !important;
  letter-spacing: .08em !important;
  text-transform: uppercase !important;
  padding: .6rem 1.8rem !important;
}
.stButton > button:hover { opacity: .88 !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid rgba(255,255,255,.07); border-radius: 3px; }

/* ── Spinner ── */
.stSpinner > div { color: var(--gold) !important; }

/* ── Download button ── */
.stDownloadButton > button {
  background: var(--emerald) !important;
  color: var(--white) !important;
  font-weight: 700 !important;
  border-radius: 2px !important;
  letter-spacing: .06em !important;
  text-transform: uppercase !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CORE LOGIC  (untouched)
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
    if debt_val <= 0:
        return "", ""
    target_name = str(row['სახელი გვარი']).strip()
    p_nomeri = str(row['პირადი ნომერი']).strip()
    matches = phone_df[phone_df['სახელი გვარი'].apply(lambda x: is_name_similar(x, target_name))]
    if matches.empty:
        return "ნომერი ვერ მოიძებნა", ""
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
    """Return clean string, hiding nan/None values."""
    s = str(val).strip()
    if s.lower() in ('nan', 'none', ''):
        return ''
    if max_len and len(s) > max_len:
        return s[:max_len - 1] + '…'
    return s

# ─────────────────────────────────────────────
#  PDF GENERATOR  —  redesigned
# ─────────────────────────────────────────────

# Palette (RGB tuples)
NAVY   = (13,  27,  42)
NAVY2  = (26,  46,  69)
NAVY3  = (36,  59,  85)
GOLD   = (212, 175,  55)
CREAM  = (245, 240, 232)
WHITE  = (255, 255, 255)
CRIMSON= (192,  57,  43)
CRIMSON_LIGHT = (231, 76, 60)
EMERALD= (26, 122,  74)
EMERALD_LIGHT = (39, 174, 96)
SILVER = (189, 195, 199)
LIGHT_GREY = (240, 243, 246)

def _set_font(pdf, size=10, bold=False):
    try:
        style = 'B' if bold else ''
        pdf.set_font('DejaVu', style, size)
    except:
        pdf.set_font('Arial', 'B' if bold else '', size)

def _fill(pdf, rgb):
    pdf.set_fill_color(*rgb)

def _text_color(pdf, rgb):
    pdf.set_text_color(*rgb)

def _draw_color(pdf, rgb):
    pdf.set_draw_color(*rgb)


class ProfessionalPDF(FPDF):
    def __init__(self, report_date, total_debts, total_advances):
        # fpdf2-ის სწორი ინიციალიზაცია
        super().__init__('P', 'mm', 'A4')
        self.report_date = report_date
        self.total_debts = total_debts
        self.total_adv = total_advances
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=22)
        
        try:
            # აუცილებლად გქონდეთ ეს ფაილი GitHub-ზე!
            self.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
            self._font = 'DejaVu'
        except:
            self._font = 'Arial'

    def draw_dashboard(self, summary_df, project_count):
        self.add_page()
        # აქ მოდის თქვენი დეშბორდის ხატვის კოდი...
        # (დარწმუნდით რომ ეს ფუნქცია კლასის შიგნითაა შეწეული)
        self.set_fill_color(13, 27, 42) # NAVY
        self.rect(0, 0, 210, 297, 'F')
        # ... დანარჩენი ვიზუალი ...

    def draw_project_page(self, proj_name, debtors_df, advances_df):
        self.add_page()
        # პროექტის გვერდის კოდი...

def generate_pdf(df):
    report_date = datetime.now().strftime('%d %B %Y | %H:%M')
    
    # მონაცემების მომზადება
    summary_data = []
    for proj in df['პროექტის დასახელება'].unique():
        sub = df[df['პროექტის დასახელება'] == proj]
        summary_data.append({
            'პროექტი': str(proj),
            'ვალი': sub['ვალები'].sum(),
            'ავანსი': sub['ავანსები'].sum(),
        })
    sum_df = pd.DataFrame(summary_data)

    # ობიექტის შექმნა
    pdf = ProfessionalPDF(report_date, sum_df['ვალი'].sum(), sum_df['ავანსი'].sum())
    
    # მეთოდის გამოძახება
    pdf.draw_dashboard(sum_df, len(sum_df))

    for proj in df['პროექტის დასახელება'].unique():
        proj_df = df[df['პროექტის დასახელება'] == proj]
        pdf.draw_project_page(str(proj), 
                              proj_df[proj_df['ვალები'] > 0], 
                              proj_df[proj_df['ავანსები'] > 0])

    # fpdf2-ში bytes() აღარ გჭირდებათ
    return pdf.output()

        # Thin top bar
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 12, 'F')

        self._sf(7)
        self.set_text_color(*GOLD)
        self.set_xy(15, 3)
        self.cell(90, 6, 'A/C FINANCIAL INTELLIGENCE REPORT', 0, 0, 'L')
        self.set_text_color(*SILVER)
        self.set_xy(105, 3)
        self.cell(90, 6, self.report_date, 0, 0, 'R')
        self.set_y(14)

    def footer(self):
        self.set_y(-18)
        # thin gold rule
        self.set_draw_color(*GOLD)
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        self._sf(7)
        self.set_text_color(*SILVER)
        self.cell(0, 5,
                  f'CONFIDENTIAL — Generated {self.report_date}  |  Page {self.page_no()}',
                  0, 0, 'C')

    # ── Dashboard (page 1) ────────────────────
    def draw_dashboard(self, summary_df, project_count):
        self.add_page()

        # Navy hero block
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 297, 'F')

        # Gold accent bar left
        self.set_fill_color(*GOLD)
        self.rect(0, 0, 5, 60, 'F')

        # Logo-type
        self._sf(28, bold=True)
        self.set_text_color(*WHITE)
        self.set_xy(12, 12)
        self.cell(0, 12, 'A/C', 0, 2, 'L')

        self._sf(9)
        self.set_text_color(*GOLD)
        self.set_x(12)
        self.cell(0, 6, 'FINANCIAL INTELLIGENCE REPORT', 0, 2, 'L')

        self._sf(7)
        self.set_text_color(*SILVER)
        self.set_x(12)
        self.cell(0, 5, f'GENERATED  {self.report_date}', 0, 2, 'L')

        # Horizontal gold rule
        self.set_draw_color(*GOLD)
        self.set_line_width(0.5)
        self.set_y(42)
        self.line(12, self.get_y(), 198, self.get_y())

        # ── KPI band ─────────────────────────
        y_kpi = 50
        ratio = (self.total_debts / self.total_adv) if self.total_adv else 0
        net   = self.total_debts - self.total_adv

        kpis = [
            ('TOTAL DEBTS',        f'{self.total_debts:,.2f} GEL', CRIMSON_LIGHT),
            ('TOTAL ADVANCES',     f'({self.total_adv:,.2f}) GEL', EMERALD_LIGHT),
            ('NET EXPOSURE',       f'{net:,.2f} GEL',              GOLD),
            ('DEBT/ADV RATIO',     f'{ratio:.2f}x',                (135,206,235)),
            ('PROJECTS',           str(project_count),             WHITE),
        ]

        card_w   = (210 - 30 - 4 * 4) / 5   # 5 cards, 15mm margins each side, 4 gaps
        card_h   = 28
        x_start  = 15

        for i, (label, value, color) in enumerate(kpis):
            x = x_start + i * (card_w + 4)
            # Card bg
            self.set_fill_color(*NAVY2)
            self.set_draw_color(*NAVY3)
            self.set_line_width(0.2)
            self.rect(x, y_kpi, card_w, card_h, 'FD')
            # Top accent
            self.set_fill_color(*color)
            self.rect(x, y_kpi, card_w, 1.5, 'F')
            # Label
            self._sf(6)
            self.set_text_color(*SILVER)
            self.set_xy(x + 2, y_kpi + 4)
            self.cell(card_w - 4, 4, label, 0, 2, 'C')
            # Value
            self._sf(9, bold=True)
            self.set_text_color(*color)
            self.set_xy(x + 2, y_kpi + 10)
            self.multi_cell(card_w - 4, 5, value, 0, 'C')

        # ── Summary table header ──────────────
        y_tbl = y_kpi + card_h + 10
        self._sf(8, bold=True)
        self.set_text_color(*GOLD)
        self.set_xy(15, y_tbl - 6)
        self.cell(0, 5, 'PROJECT SUMMARY', 0, 1, 'L')

        # Column header row
        col_w = [85, 42, 42, 12]   # name, debt, advance, bar
        self.set_fill_color(*NAVY3)
        self.set_draw_color(*NAVY2)
        self.set_line_width(0.15)
        self.set_xy(15, y_tbl)
        self._sf(7, bold=True)
        self.set_text_color(*GOLD)
        for header, w in zip(['PROJECT NAME', 'TOTAL DEBT (GEL)', 'ADVANCE (GEL)', ''], col_w):
            self.cell(w, 7, header, 1, 0, 'C', True)
        self.ln()

        # Rows
        max_debt = summary_df['ვალი'].max() or 1
        for idx, row in summary_df.iterrows():
            bg = NAVY2 if idx % 2 == 0 else (20, 34, 52)
            self.set_fill_color(*bg)
            self.set_xy(15, self.get_y())
            self._sf(7)
            self.set_text_color(*CREAM)

            proj_name = clean_str(row['პროექტი'], 45)
            debt_val  = row['ვალი']
            adv_val   = row['ავანსი']

            self.set_fill_color(*bg)
            self.cell(col_w[0], 6.5, proj_name,                            1, 0, 'L', True)
            self.set_text_color(*CRIMSON_LIGHT)
            self.cell(col_w[1], 6.5, f'{debt_val:,.2f}',                   1, 0, 'R', True)
            self.set_text_color(*EMERALD_LIGHT)
            self.cell(col_w[2], 6.5, f'({adv_val:,.2f})' if adv_val else '—', 1, 0, 'R', True)

            # Mini bar
            bar_pct = debt_val / max_debt
            bar_x   = self.get_x()
            bar_y   = self.get_y()
            self.set_fill_color(*bg)
            self.cell(col_w[3], 6.5, '', 1, 0, 'L', True)
            filled = col_w[3] * bar_pct * 0.85
            if filled > 0.5:
                self.set_fill_color(*CRIMSON)
                self.rect(bar_x + 0.5, bar_y + 1.5, filled, 3.5, 'F')

            self.set_text_color(*CREAM)
            self.ln()

        # Totals row
        self.set_fill_color(*NAVY3)
        self.set_text_color(*WHITE)
        self._sf(7, bold=True)
        self.cell(col_w[0], 7, 'TOTAL', 1, 0, 'L', True)
        self.set_text_color(*CRIMSON_LIGHT)
        self.cell(col_w[1], 7, f'{self.total_debts:,.2f}', 1, 0, 'R', True)
        self.set_text_color(*EMERALD_LIGHT)
        self.cell(col_w[2], 7, f'({self.total_adv:,.2f})', 1, 0, 'R', True)
        self.cell(col_w[3], 7, '', 1, 0, 'L', True)
        self.ln()

        # ── Disclaimer ───────────────────────
        self.set_y(-30)
        self.set_draw_color(*NAVY3)
        self.set_line_width(0.2)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        self._sf(6)
        self.set_text_color(*SILVER)
        self.multi_cell(0, 4,
            'This document is confidential and intended solely for authorised personnel. '
            'All figures are in Georgian Lari (GEL) unless otherwise stated.',
            0, 'C')

    # ── Project detail page ───────────────────
    def draw_project_page(self, proj_name, debtors_df, advances_df):
        self.add_page()

        # Project title block
        self.set_fill_color(*NAVY2)
        self.rect(15, self.get_y(), 180, 12, 'F')
        self.set_fill_color(*GOLD)
        self.rect(15, self.get_y(), 3, 12, 'F')

        self._sf(11, bold=True)
        self.set_text_color(*WHITE)
        self.set_xy(21, self.get_y() + 2)
        self.cell(170, 8, clean_str(proj_name, 70), 0, 1, 'L')
        self.ln(5)

        # Project KPIs
        p_debt = debtors_df['ვალები'].sum()  if not debtors_df.empty  else 0
        p_adv  = advances_df['ავანსები'].sum() if not advances_df.empty else 0
        self._sf(7)
        self.set_text_color(*SILVER)
        self.cell(60, 5, f'Debtors: {len(debtors_df)}', 0, 0, 'L')
        self.cell(60, 5, f'Advance holders: {len(advances_df)}', 0, 0, 'L')
        self.set_text_color(*CRIMSON_LIGHT)
        self.cell(30, 5, f'Debt: {p_debt:,.2f}', 0, 0, 'L')
        self.set_text_color(*EMERALD_LIGHT)
        self.cell(30, 5, f'Adv: ({p_adv:,.2f})', 0, 1, 'L')
        self.ln(3)

        # ── Debtors table ───────────────────
        if not debtors_df.empty:
            self._sf(8, bold=True)
            self.set_text_color(*CRIMSON_LIGHT)
            self.cell(0, 6, '▸  DEBTORS', 0, 1, 'L')

            col_w = [58, 30, 28, 32, 32]
            headers = ['FULL NAME', 'ID NUMBER', 'DEBT (GEL)', 'PHONE', 'NOTE']
            self.set_fill_color(*NAVY3)
            self._sf(7, bold=True)
            self.set_text_color(*GOLD)
            for h, w in zip(headers, col_w):
                self.cell(w, 7, h, 1, 0, 'C', True)
            self.ln()

            for i, (_, r) in enumerate(debtors_df.iterrows()):
                bg = NAVY2 if i % 2 == 0 else (20, 34, 52)
                self.set_fill_color(*bg)
                self._sf(7)
                self.set_text_color(*CREAM)
                self.cell(col_w[0], 6.5, clean_str(r['სახელი გვარი'], 32),    1, 0, 'L', True)
                self.cell(col_w[1], 6.5, clean_str(r['პირადი ნომერი'], 17),   1, 0, 'C', True)
                self.set_text_color(*CRIMSON_LIGHT)
                self.cell(col_w[2], 6.5, f"{r['ვალები']:,.2f}",               1, 0, 'R', True)
                self.set_text_color(*CREAM)
                self.cell(col_w[3], 6.5, clean_str(r.get('ტელეფონი',''), 16), 1, 0, 'C', True)
                self.cell(col_w[4], 6.5, clean_str(r.get('შენიშვნა',''), 18), 1, 1, 'L', True)

            # subtotal
            self.set_fill_color(*NAVY3)
            self._sf(7, bold=True)
            self.set_text_color(*WHITE)
            self.cell(col_w[0] + col_w[1], 6.5, 'SUBTOTAL', 1, 0, 'R', True)
            self.set_text_color(*CRIMSON_LIGHT)
            self.cell(col_w[2], 6.5, f"{p_debt:,.2f}", 1, 0, 'R', True)
            self.cell(col_w[3] + col_w[4], 6.5, '', 1, 1, 'L', True)
            self.ln(4)

        # ── Advances table ──────────────────
        if not advances_df.empty:
            self._sf(8, bold=True)
            self.set_text_color(*EMERALD_LIGHT)
            self.cell(0, 6, '▸  ADVANCE HOLDERS', 0, 1, 'L')

            col_w2 = [88, 50, 42]
            headers2 = ['FULL NAME', 'ID NUMBER', 'ADVANCE (GEL)']
            self.set_fill_color(*NAVY3)
            self._sf(7, bold=True)
            self.set_text_color(*GOLD)
            for h, w in zip(headers2, col_w2):
                self.cell(w, 7, h, 1, 0, 'C', True)
            self.ln()

            for i, (_, r) in enumerate(advances_df.iterrows()):
                bg = NAVY2 if i % 2 == 0 else (20, 34, 52)
                self.set_fill_color(*bg)
                self._sf(7)
                self.set_text_color(*CREAM)
                self.cell(col_w2[0], 6.5, clean_str(r['სახელი გვარი'], 50),  1, 0, 'L', True)
                self.cell(col_w2[1], 6.5, clean_str(r['პირადი ნომერი'], 28), 1, 0, 'C', True)
                self.set_text_color(*EMERALD_LIGHT)
                self.cell(col_w2[2], 6.5, f"({r['ავანსები']:,.2f})",         1, 1, 'R', True)

            self.set_fill_color(*NAVY3)
            self._sf(7, bold=True)
            self.set_text_color(*WHITE)
            self.cell(col_w2[0] + col_w2[1], 6.5, 'SUBTOTAL', 1, 0, 'R', True)
            self.set_text_color(*EMERALD_LIGHT)
            self.cell(col_w2[2], 6.5, f"({p_adv:,.2f})", 1, 1, 'R', True)

# 1. დარწმუნდით, რომ იმპორტი ასეთია:
from fpdf import FPDF

# 2. განაახლეთ ProfessionalPDF კლასის __init__ და generate_pdf ფუნქცია:

class ProfessionalPDF(FPDF):
    def __init__(self, report_date, total_debts, total_advances):
        # fpdf2-ში ვიყენებთ პირდაპირ ინიციალიზაციას
        super().__init__('P', 'mm', 'A4')
        self.report_date = report_date
        self.total_debts = total_debts
        self.total_adv = total_advances
        
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=22)
        
        # ქართული შრიფტის დამატება - ფაილი dejavu-sans.book.ttf უნდა გქონდეთ საქაღალდეში
        try:
            self.add_font('DejaVu', '', 'dejavu-sans.book.ttf')
            self.add_font('DejaVu', 'B', 'dejavu-sans.book.ttf') 
            self._font = 'DejaVu'
        except:
            # თუ ფონტი ვერ იპოვა, აპლიკაცია რომ არ გაითიშოს
            self._font = 'Arial'

    # ... (დანარჩენი მეთოდები draw_dashboard და ა.შ. რჩება იგივე)

def generate_pdf(df):
    report_date = datetime.now().strftime('%d %B %Y | %H:%M')

    summary_data = []
    for proj in df['პროექტის დასახელება'].unique():
        sub = df[df['პროექტის დასახელება'] == proj]
        summary_data.append({
            'პროექტი': str(proj), # ვამატებთ str() კონვერტაციას
            'ვალი': sub['ვალები'].sum(),
            'ავანსი': sub['ავანსები'].sum(),
        })
    sum_df = pd.DataFrame(summary_data)

    total_debts = sum_df['ვალი'].sum()
    total_advances = sum_df['ავანსი'].sum()
    project_count = len(sum_df)

    # ობიექტის შექმნა
    pdf = ProfessionalPDF(report_date, total_debts, total_advances)

    # Dashboard-ის დახატვა
    pdf.draw_dashboard(sum_df, project_count)

    # თითოეული პროექტის გვერდი
    for proj in df['პროექტის დასახელება'].unique():
        proj_df = df[df['პროექტის დასახელება'] == proj]
        debtors = proj_df[proj_df['ვალები'] > 0].copy()
        advances = proj_df[proj_df['ავანსები'] > 0].copy()
        pdf.draw_project_page(str(proj), debtors, advances)

    # ყველაზე მნიშვნელოვანი ცვლილება აქ არის:
    # fpdf2-ში output() პირდაპირ აბრუნებს bytearray-ს, bytes() აღარ გჭირდებათ
    return pdf.output()


# ─────────────────────────────────────────────
#  STREAMLIT UI
# ─────────────────────────────────────────────

# Hero banner
st.markdown("""
<div class="hero-banner">
  <div class="hero-title">A/C Financial Intelligence</div>
  <div class="gold-line"></div>
  <div class="hero-sub">Accounts Receivable & Advance Analytics Platform</div>
</div>
""", unsafe_allow_html=True)

# Upload section
col_l, col_r = st.columns(2)
with col_l:
    st.markdown('<p style="color:#D4AF37;font-size:.8rem;text-transform:uppercase;letter-spacing:.1em;">Receivables File</p>', unsafe_allow_html=True)
    f1 = st.file_uploader("prnValiSagad1.csv", type=['csv'], label_visibility='collapsed')
with col_r:
    st.markdown('<p style="color:#D4AF37;font-size:.8rem;text-transform:uppercase;letter-spacing:.1em;">Contact Directory</p>', unsafe_allow_html=True)
    f2 = st.file_uploader("valebi.csv", type=['csv'], label_visibility='collapsed')

if f1 and f2:
    df1 = pd.read_csv(f1)
    df2 = pd.read_csv(f2)

    for col in ['ვალები', 'ავანსები']:
        df1[col] = df1[col].apply(safe_float)

    with st.spinner('Enriching records with contact data…'):
        df1[['ტელეფონი', 'შენიშვნა']] = df1.apply(
            lambda row: pd.Series(match_phone(row, df2)), axis=1)

    # ── KPI Dashboard ────────────────────────
    summary = (df1.groupby('პროექტის დასახელება')
               .agg(ვალი=('ვალები', 'sum'), ავანსი=('ავანსები', 'sum'))
               .reset_index())

    total_d = summary['ვალი'].sum()
    total_a = summary['ავანსი'].sum()
    net_exp = total_d - total_a
    ratio   = round(total_d / total_a, 2) if total_a else 0
    proj_n  = len(summary)

    st.markdown('<div class="section-title">Executive Dashboard</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Debts",    f"{total_d:,.2f} ₾")
    k2.metric("Total Advances", f"({total_a:,.2f}) ₾")
    k3.metric("Net Exposure",   f"{net_exp:,.2f} ₾")
    k4.metric("Debt/Adv Ratio", f"{ratio}×")
    k5.metric("Projects",       proj_n)

    # ── Plotly Chart ─────────────────────────
    st.markdown('<div class="section-title">Debt vs. Advance by Project</div>', unsafe_allow_html=True)

    proj_labels = [clean_str(p, 30) for p in summary['პროექტის დასახელება']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Debt',
        x=proj_labels,
        y=summary['ვალი'],
        marker_color='#E74C3C',
        marker_line_color='#C0392B',
        marker_line_width=0.5,
    ))
    fig.add_trace(go.Bar(
        name='Advance',
        x=proj_labels,
        y=summary['ავანსი'],
        marker_color='#27AE60',
        marker_line_color='#1A7A4A',
        marker_line_width=0.5,
    ))
    fig.update_layout(
        barmode='group',
        plot_bgcolor='#1A2E45',
        paper_bgcolor='#0D1B2A',
        font=dict(family='DM Sans', color='#F5F0E8', size=11),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='right', x=1,
            font=dict(color='#F5F0E8'),
        ),
        xaxis=dict(
            gridcolor='#243B55', tickfont=dict(size=10),
            tickangle=-30,
        ),
        yaxis=dict(
            gridcolor='#243B55',
            tickformat=',.0f',
        ),
        margin=dict(l=10, r=10, t=40, b=60),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Project expanders ────────────────────
    st.markdown('<div class="section-title">Project-Level Detail</div>', unsafe_allow_html=True)

    display_cols = ['სახელი გვარი', 'პირადი ნომერი', 'ვალები', 'ავანსები', 'ტელეფონი', 'შენიშვნა']

    for p in df1['პროექტის დასახელება'].unique():
        p_df    = df1[df1['პროექტის დასახელება'] == p]
        p_debt  = p_df['ვალები'].sum()
        p_adv   = p_df['ავანსები'].sum()
        label   = f"📁  {clean_str(p, 50)}   |   Debt: {p_debt:,.0f} ₾   |   Adv: ({p_adv:,.0f}) ₾"
        with st.expander(label):
            display_df = p_df[display_cols].copy()
            # hide nan strings in note/phone columns
            for c in ['ტელეფონი', 'შენიშვნა']:
                display_df[c] = display_df[c].apply(lambda v: '' if str(v).lower() in ('nan','none') else v)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── PDF export ───────────────────────────
    st.markdown("---")
    col_btn, col_dl = st.columns([1, 3])
    with col_btn:
        generate = st.button("🚀  Generate PDF Report")

    if generate:
        with st.spinner("Compiling professional report…"):
            pdf_bytes = generate_pdf(df1)
        with col_dl:
            fname = f"AC_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            st.download_button(
                "📥  Download Report",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
            )
        st.success("✅ Report ready — click Download above.")
