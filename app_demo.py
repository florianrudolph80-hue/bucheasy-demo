import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="BuchEasy Demo", layout="wide")

st.title("📘 BuchEasy – Demo (7 Tage Version)")

st.warning("⚠️ Demo-Version: Es werden nur die ersten 7 Tage der Shore-Datei angezeigt.")

# =====================================================
# SESSION STATE
# =====================================================

if "shore_data" not in st.session_state:
    st.session_state.shore_data = None

if "start_date_demo" not in st.session_state:
    st.session_state.start_date_demo = None

if "einzahlungen" not in st.session_state:
    st.session_state.einzahlungen = []

# =====================================================
# SHORE IMPORT
# =====================================================

st.header("📥 Shore Export importieren")

uploaded_file = st.file_uploader("Shore CSV hochladen", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8")

    # Datumsspalte anpassen (ggf. an deine Shore Struktur anpassen)
    df["Datum"] = pd.to_datetime(df["Datum"], dayfirst=True)

    # Startdatum für Demo setzen
    first_date = df["Datum"].min()
    st.session_state.start_date_demo = first_date

    # Nur 7 Tage anzeigen
    end_date = first_date + timedelta(days=6)
    df_demo = df[(df["Datum"] >= first_date) & (df["Datum"] <= end_date)]

    st.session_state.shore_data = df_demo

    st.success("Shore Datei importiert (7 Tage gefiltert)")

# =====================================================
# ANFANGSBESTAND
# =====================================================

st.header("💰 Anfangsbestand Kasse")

anfangsbestand = st.number_input("Anfangsbestand (€)", min_value=0.0, step=0.01)

# =====================================================
# EINZAHLUNG BANK
# =====================================================

st.header("🏦 Einzahlung Bank")

with st.form("einzahlung_form"):
    datum = st.date_input("Datum")
    betrag = st.number_input("Betrag (€)", min_value=0.0, step=0.01)
    speichern = st.form_submit_button("Speichern")

    if speichern and betrag > 0:
        st.session_state.einzahlungen.append({
            "Datum": datum,
            "Betrag": betrag
        })
        st.success("Einzahlung gespeichert")

if st.session_state.einzahlungen:
    df_einzahlung = pd.DataFrame(st.session_state.einzahlungen)
    st.dataframe(df_einzahlung, use_container_width=True)

# =====================================================
# KASSENBUCH BERECHNUNG
# =====================================================

if st.session_state.shore_data is not None:

    st.header("📋 Kassenbuch")

    df = st.session_state.shore_data.copy()

    # Nur Barumsätze (anpassen falls Shore Spalte anders heißt)
    df_bar = df[df["Zahlungsart"] == "Bar"]

    tagesumsatz = df_bar.groupby("Datum")["Betrag"].sum().reset_index()
    tagesumsatz = tagesumsatz.sort_values("Datum")

    # Einzahlungen gruppieren
    if st.session_state.einzahlungen:
        df_einz = pd.DataFrame(st.session_state.einzahlungen)
        df_einz_grouped = df_einz.groupby("Datum")["Betrag"].sum().reset_index()
    else:
        df_einz_grouped = pd.DataFrame(columns=["Datum", "Betrag"])

    # Kassenbuch erstellen
    kassenbuch = []
    bestand = anfangsbestand

    for _, row in tagesumsatz.iterrows():
        datum = row["Datum"]
        einnahme = row["Betrag"]

        einzahlung = 0
        if not df_einz_grouped.empty:
            match = df_einz_grouped[df_einz_grouped["Datum"] == datum]
            if not match.empty:
                einzahlung = match["Betrag"].values[0]

        bestand = bestand + einnahme - einzahlung

        kassenbuch.append({
            "Datum": datum.strftime("%d.%m.%Y"),
            "Barumsatz": einnahme,
            "Einzahlung Bank": einzahlung,
            "Kassenbestand": bestand
        })

    df_kassenbuch = pd.DataFrame(kassenbuch)

    df_display = df_kassenbuch.copy()
    for col in ["Barumsatz", "Einzahlung Bank", "Kassenbestand"]:
        df_display[col] = df_display[col].map(
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    st.dataframe(df_display, use_container_width=True)

    # =====================================================
    # EXCEL DOWNLOAD
    # =====================================================

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_kassenbuch.to_excel(writer, index=False, sheet_name="Kassenbuch")

    st.download_button(
        "📥 Kassenbuch als Excel herunterladen",
        data=excel_buffer.getvalue(),
        file_name="Kassenbuch_Demo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # =====================================================
    # DATEV CSV EXPORT
    # =====================================================

    datev_export = []

    for _, row in df_kassenbuch.iterrows():
        if row["Einzahlung Bank"] > 0:
            datev_export.append({
                "Datum": row["Datum"],
                "Soll": "1200",
                "Haben": "1000",
                "Betrag": row["Einzahlung Bank"],
                "Text": "Einzahlung Bank"
            })

    df_datev = pd.DataFrame(datev_export)

    csv = df_datev.to_csv(index=False, sep=";")

    st.download_button(
        "📤 DATEV CSV herunterladen",
        data=csv,
        file_name="DATEV_Export_Demo.csv",
        mime="text/csv"
    )
