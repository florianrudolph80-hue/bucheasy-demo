import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="BuchEasy Demo", layout="wide")

st.title("📘 BuchEasy – Demo Version")

st.markdown("Diese Demo zeigt die Funktion **Einzahlung Bank**.")

st.divider()

# =====================================================
# SESSION STATE INITIALISIERUNG
# =====================================================

if "einzahlung_bank" not in st.session_state:
    st.session_state.einzahlung_bank = []

# =====================================================
# EINZAHLUNG BANK – EINGABE
# =====================================================

st.subheader("🏦 Einzahlung Bank erfassen")

with st.form("einzahlung_form"):
    col1, col2 = st.columns(2)

    with col1:
        datum = st.date_input("Datum", value=date.today())

    with col2:
        betrag = st.number_input(
            "Betrag (€)",
            min_value=0.0,
            step=0.01,
            format="%.2f"
        )

    beschreibung = st.text_input("Beschreibung")

    submit = st.form_submit_button("Einzahlung speichern")

    if submit:
        if betrag > 0:
            st.session_state.einzahlung_bank.append({
                "Datum": datum.strftime("%d.%m.%Y"),
                "Betrag (€)": betrag,
                "Beschreibung": beschreibung
            })
            st.success("Einzahlung Bank gespeichert.")
        else:
            st.error("Bitte einen Betrag größer 0 eingeben.")

st.divider()

# =====================================================
# TABELLE EINZAHLUNG BANK
# =====================================================

st.subheader("📋 Übersicht Einzahlung Bank")

if st.session_state.einzahlung_bank:

    df = pd.DataFrame(st.session_state.einzahlung_bank)

    # Anzeigeformat für Euro
    df_display = df.copy()
    df_display["Betrag (€)"] = df_display["Betrag (€)"].map(
        lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    st.dataframe(df_display, use_container_width=True)

    # Summe berechnen
    summe = df["Betrag (€)"].sum()

    st.markdown("### 💰 Gesamtsumme")
    st.success(
        f"{summe:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    )

else:
    st.info("Noch keine Einzahlung Bank erfasst.")

st.divider()

# =====================================================
# DEMO HINWEIS
# =====================================================

st.caption("Demo-Version – Daten werden nicht dauerhaft gespeichert.")
