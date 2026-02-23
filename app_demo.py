# -*- coding: utf-8 -*-
import io
from datetime import datetime, date, timedelta
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="BuchEasy – DATEV Import", page_icon="🧾")

# =============================
# KONFIG
# =============================
KONTO_RECHTS = "1000"
GEGEN_UMSATZ = "8400"
GEGEN_KARTE = "1360"
GEGEN_BANK = "1360"
WKZ = "EUR"

# =============================
# DEMO SETTINGS
# =============================
DEMO_MODE = True
DEMO_DAYS = 7

# =============================
# Helper
# =============================
def money_de(x):
    return f"{float(x):.2f}".replace(".", ",")

def iso_week_key(d):
    iso = d.isocalendar()
    return (iso.year, iso.week)

def belegdatum_ttmm(d):
    return f"{d.day:02d}{d.month:02d}"

# =============================
# Excel robust einlesen
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
        raise ValueError("Keine Kopfzeile mit 'Datum' gefunden.")

    df = pd.read_excel(io.BytesIO(file_bytes), header=header_idx, engine="openpyxl")

    def find_col(keys):
        for col in df.columns:
            for k in keys:
                if k in str(col).lower():
                    return col
        return None

    datum_col = find_col(["datum"])
    umsatz_col = find_col(["brutto", "umsatz", "total", "betrag"])
    zahlart_col = find_col(["zahlart", "payment", "art"])

    if not datum_col or not umsatz_col:
        raise ValueError("Spalten nicht erkannt.")

    df = df.rename(columns={datum_col: "Datum", umsatz_col: "Umsatz"})
    if zahlart_col:
        df = df.rename(columns={zahlart_col: "Zahlart"})
    else:
        df["Zahlart"] = ""

    df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce").dt.date
    df = df[df["Datum"].notna()].copy()
    df["Umsatz"] = pd.to_numeric(df["Umsatz"], errors="coerce").fillna(0.0)

    def is_card(x):
        x = str(x).lower()
        return any(k in x for k in ["karte", "ec", "visa", "master", "shore"])

    df["ist_karte"] = df["Zahlart"].apply(is_card)

    g_all = df.groupby("Datum")["Umsatz"].sum()
    g_card = df[df["ist_karte"]].groupby("Datum")["Umsatz"].sum()

    days = []
    for d, total in g_all.items():
        days.append((d, float(total), float(g_card.get(d, 0.0))))
    days.sort(key=lambda x: x[0])

    if not days:
        raise ValueError("Keine Buchungsdaten gefunden.")

    return days

# =============================
# DATEV Export
# =============================
def build_datev_csv(days, einzahl_rows):

    rows = []

    for d, u, k in days:
        if u > 0:
            rows.append([money_de(u), "S", KONTO_RECHTS, GEGEN_UMSATZ, belegdatum_ttmm(d)])
        if k > 0:
            rows.append([money_de(k), "H", KONTO_RECHTS, GEGEN_KARTE, belegdatum_ttmm(d)])

    for item in einzahl_rows:
        d_b = item["datum"]
        if isinstance(d_b, datetime):
            d_b = d_b.date()
        rows.append([money_de(item["betrag"]), "S", KONTO_RECHTS, GEGEN_BANK, belegdatum_ttmm(d_b)])

    out = io.StringIO()
    out.write("Umsatz;S/H;Konto;Gegenkonto;Belegdatum\n")
    for r in rows:
        out.write(";".join(r) + "\n")

    return out.getvalue().encode("utf-8")

# =============================
# PDF
# =============================
def build_pdf(von, bis, days, einzahl_rows, startbestand=0.0):

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    x_left = 18 * mm
    y = height - 18 * mm

    def euro_de(amount):
        return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    def page_break():
        nonlocal y
        if y < 20 * mm:
            c.showPage()
            y = height - 18 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_left, y, f"Kassenbuch {von.month:02d}.{von.year}")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(x_left, y,
                 f"Zeitraum: {von.strftime('%d.%m.%Y')} – {bis.strftime('%d.%m.%Y')}")
    y -= 12 * mm

    current_cash = startbestand

    for d, u, k in days:

        if u > 0:
            c.drawString(x_left, y, f"{d.strftime('%d.%m.')} Umsatz")
            c.drawRightString(width - 18 * mm, y, euro_de(u))
            y -= 6 * mm
            current_cash += u
            page_break()

        if k > 0:
            c.drawString(x_left, y, f"{d.strftime('%d.%m.')} EC")
            c.drawRightString(width - 18 * mm, y, euro_de(k))
            y -= 6 * mm
            current_cash -= k
            page_break()

    for item in einzahl_rows:
        d_b = item["datum"]
        if isinstance(d_b, datetime):
            d_b = d_b.date()
        betrag = float(item["betrag"])
        if betrag > 0:
            c.drawString(x_left, y,
                         f"Einzahlung Bank {d_b.strftime('%d.%m.')}")
            c.drawRightString(width - 18 * mm, y, euro_de(betrag))
            y -= 6 * mm
            current_cash -= betrag
            page_break()

    c.save()
    return buf.getvalue()

# =============================
# UI
# =============================
st.title("📘 BuchEasy – DATEV Import in Sekunden")

if DEMO_MODE:
    st.warning("⚠️ Demo-Version: Es werden nur die ersten 7 Tage berücksichtigt.")

st.divider()

st.header("📥 Shore Export importieren")
uploaded = st.file_uploader("Excel hochladen (.xlsx)", type=["xlsx"])

st.header("🏦 Einzahlung Bank")

if "einzahlungen" not in st.session_state:
    st.session_state["einzahlungen"] = []

col1, col2 = st.columns(2)
with col1:
    d_in = st.date_input("Datum", date.today())
with col2:
    b_in = st.number_input("Betrag (€)", min_value=0.0, step=10.0)

if st.button("Einzahlung Bank hinzufügen"):
    if b_in > 0:
        st.session_state["einzahlungen"].append(
            {"datum": d_in, "betrag": b_in}
        )

if st.session_state["einzahlungen"]:
    st.dataframe(pd.DataFrame(st.session_state["einzahlungen"]), use_container_width=True)

st.divider()

if uploaded:
    try:
        days = read_excel_days(uploaded.getvalue())

        # =============================
        # DEMO LIMIT
        # =============================
        if DEMO_MODE:
            first_date = days[0][0]
            demo_end = first_date + timedelta(days=DEMO_DAYS - 1)
            days = [d for d in days if d[0] <= demo_end]

        von = days[0][0]
        bis = days[-1][0]

        st.success(f"Zeitraum: {von.strftime('%d.%m.%Y')} – {bis.strftime('%d.%m.%Y')}")

        st.header("📄 Downloads")

        pdf_bytes = build_pdf(
            von,
            bis,
            days,
            st.session_state["einzahlungen"],
            startbestand=0.0
        )

        csv_bytes = build_datev_csv(
            days,
            st.session_state["einzahlungen"]
        )

        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                "📥 Kassenbuch PDF herunterladen",
                data=pdf_bytes,
                file_name=f"Kassenbuch_{von.year}-{von.month:02d}.pdf"
            )

        with col2:
            st.download_button(
                "📤 DATEV CSV herunterladen",
                data=csv_bytes,
                file_name=f"DATEV_{von.year}_{von.month:02d}.csv"
            )

    except Exception as e:
        st.error(str(e))
