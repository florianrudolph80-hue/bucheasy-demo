# -*- coding: utf-8 -*-
import io
from datetime import datetime
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# =============================
# DEMO SETTINGS
# =============================
DEMO_MAX_DATEV_ROWS = 10

st.set_page_config(page_title="BuchEasy – Demo", page_icon="🧾")
st.warning("⚠ Demo-Version – Export ist auf 1 Woche begrenzt.")

# =============================
# Helper
# =============================
def iso_week_key(d):
    iso = d.isocalendar()
    return (iso.year, iso.week)

def money_de(x):
    return f"{float(x):.2f}".replace(".", ",")

# =============================
# Excel einlesen
# =============================
def read_excel_days(file_bytes):

    df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None, engine="openpyxl")
    header_idx = None

    for i in range(min(len(df_raw), 60)):
        row = [str(x).lower() for x in df_raw.iloc[i].tolist()]
        if any("datum" in v for v in row):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Keine Kopfzeile gefunden.")

    df = pd.read_excel(io.BytesIO(file_bytes), header=header_idx, engine="openpyxl")
    df.columns = [str(c) for c in df.columns]

    def find_col(keys):
        for col in df.columns:
            for k in keys:
                if k in col.lower():
                    return col
        return None

    datum_col = find_col(["datum"])
    umsatz_col = find_col(["brutto", "umsatz", "betrag"])

    if not datum_col or not umsatz_col:
        raise ValueError("Spalten nicht erkannt.")

    df = df.rename(columns={datum_col: "Datum", umsatz_col: "Umsatz"})
    df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce").dt.date
    df = df[df["Datum"].notna()].copy()
    df["Umsatz"] = pd.to_numeric(df["Umsatz"], errors="coerce").fillna(0.0)

    days = []
    grouped = df.groupby("Datum")["Umsatz"].sum()

    for d, total in grouped.items():
        days.append((d, float(total)))

    days.sort(key=lambda x: x[0])

    if not days:
        raise ValueError("Keine Buchungen gefunden.")

    # DEMO LIMIT → nur erste Woche
    first_week = iso_week_key(days[0][0])
    days = [d for d in days if iso_week_key(d[0]) == first_week]

    return days

# =============================
# DATEV DEMO CSV
# =============================
def build_demo_csv(days):

    rows = []
    for d, u in days:
        rows.append([money_de(u), d.strftime("%d%m")])

    rows = rows[:DEMO_MAX_DATEV_ROWS]

    out = io.StringIO()
    out.write("Umsatz;Belegdatum\n")
    for r in rows:
        out.write(";".join(r) + "\n")

    return out.getvalue().encode("utf-8")

# =============================
# DEMO PDF
# =============================
def build_demo_pdf(days, kassen_start, bank_einzahlung):

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 20 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, "Kassenbuch – DEMO")
    y -= 12 * mm

    c.setFont("Helvetica", 10)

    saldo = kassen_start

    c.drawString(20 * mm, y, "Kassenanfangsbestand")
    c.drawRightString(160 * mm, y, f"{saldo:,.2f} €")
    y -= 8 * mm

    for d, u in days:
        saldo += u
        c.drawString(20 * mm, y, f"{d.strftime('%d.%m.%Y')} Umsatz")
        c.drawRightString(160 * mm, y, f"+ {u:,.2f} €")
        y -= 6 * mm

    if bank_einzahlung > 0:
        y -= 6 * mm
        saldo -= bank_einzahlung
        c.drawString(20 * mm, y, "Bankeinzahlung")
        c.drawRightString(160 * mm, y, f"- {bank_einzahlung:,.2f} €")
        y -= 8 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Kassenbestand Ende")
    c.drawRightString(160 * mm, y, f"{saldo:,.2f} €")

    y -= 15 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Demo-Version – Vollversion unter bucheasy.de")

    c.save()
    return buf.getvalue()

# =============================
# UI
# =============================
st.title("DATEV-Import in Sekunden – Demo")

uploaded = st.file_uploader("Excel hochladen (.xlsx)", type=["xlsx"])

st.subheader("Optionale Angaben")

kassen_start = st.number_input(
    "Kassenanfangsbestand (€)",
    min_value=0.0,
    step=10.0,
    value=0.0
)

bank_einzahlung = st.number_input(
    "Manuelle Bankeinzahlung (€)",
    min_value=0.0,
    step=10.0,
    value=0.0
)

if uploaded:
    try:
        days = read_excel_days(uploaded.getvalue())

        pdf_bytes = build_demo_pdf(days, kassen_start, bank_einzahlung)
        csv_bytes = build_demo_csv(days)

        st.success("Demo-Export erstellt (1 Woche begrenzt)")

        st.download_button(
            "📥 Demo PDF",
            data=pdf_bytes,
            file_name="Demo_Kassenbuch.pdf"
        )

        st.download_button(
            "📥 Demo DATEV CSV",
            data=csv_bytes,
            file_name="Demo_DATEV.csv"
        )

    except Exception as e:
        st.error(str(e))
