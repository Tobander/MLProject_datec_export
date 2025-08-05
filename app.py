import streamlit as st
import requests
import json
import csv
import io
import tempfile
from datetime import date
import os

# ---------------- API KONFIGURATION ----------------
VA_API_KEY = os.getenv('VA_API_KEY') 
HEADERS = {"Authorization": f"Basic {VA_API_KEY}"}
API_URL = "https://api.va.landing.ai/v1/tools/agentic-document-analysis"

# ---------------- JSON-SCHEMA DEFINIEREN ----------------
EXTRACTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Zoom Invoice Extraction Schema",
    "type": "object",
    "properties": {
        "invoiceInfo": {
            "type": "object",
            "properties": {
                "belegdatum": {"type": "string"},
                "belegnummer": {"type": "string"}
            },
            "required": ["belegdatum", "belegnummer"]
        },
        "chargeDetails": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "betrag": {"type": "number"},
                    "taxes": {"type": "number"}
                },
                "required": ["betrag", "taxes"]
            }
        }
    },
    "required": ["invoiceInfo", "chargeDetails"]
}

# ---------------- STREAMLIT APP ----------------
st.title("📄 DATEC Export")

# Dateiupload
uploaded_file = st.file_uploader("Lade eine Rechnung hoch (PDF)", type=["pdf"])

# Daten extrahieren & speichern
if uploaded_file and "extracted_data" not in st.session_state:
    with st.spinner("Extrahiere Daten mit Landing AI..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            temp_pdf_path = tmp_file.name

        files = [("pdf", (uploaded_file.name, open(temp_pdf_path, "rb"), "application/pdf"))]
        payload = {"fields_schema": json.dumps(EXTRACTION_SCHEMA)}
        response = requests.post(API_URL, headers=HEADERS, files=files, data=payload)

        if response.status_code != 200:
            st.error(f"Fehler bei der API-Anfrage: {response.text}")
            st.stop()

        st.session_state["extracted_data"] = response.json()["data"]["extracted_schema"]

# Hauptlogik
if "extracted_data" in st.session_state:
    extracted_data = st.session_state["extracted_data"]
    st.success("Daten erfolgreich extrahiert!")

    st.subheader("🧾 Allgemeine Rechnungsdaten")
    invoice_info = extracted_data.get("invoiceInfo", {})
    belegdatum = st.text_input("Belegdatum", value=invoice_info.get("belegdatum", ""))
    belegnummer = st.text_input("Belegnummer", value=invoice_info.get("belegnummer", ""))

    st.subheader("📅 Buchungsdatum")
    buchungsdatum = st.date_input("Buchungsdatum", value=date.today())

    st.subheader("💰 Rechnungspositionen bearbeiten")
    edited_rows = []

    for i, row in enumerate(extracted_data.get("chargeDetails", [])):
        st.markdown(f"### Position {i + 1}")

        col1, col2 = st.columns(2)
        with col1:
            betrag = st.number_input(f"Betrag {i + 1}", value=float(row.get("betrag", 0.0)), step=0.01, key=f"betrag_{i}")
        with col2:
            steuersatz = st.selectbox(f"Steuersatz {i + 1}", options=[0, 7, 19], index=[0, 7, 19].index(int(row.get("taxes", 0))), key=f"steuersatz_{i}")

        steuerkennzeichen = st.selectbox(f"Steuerkennzeichen {i + 1}", options=["V0", "V1", "V2"], key=f"steuerkennz_{i}")
        buchungstext = st.text_input(f"Buchungstext {i + 1}", value=f"Wareneingang {steuersatz}%" if steuersatz > 0 else "Wareneinkauf Netto", key=f"bt_{i}")
        konto = st.number_input(f"Konto {i + 1}", value=3400, step=1, key=f"konto_{i}")
        gegenkonto = st.number_input(f"Gegenkonto {i + 1}", value=1200, step=1, key=f"gkto_{i}")
        buchungsart = st.number_input(f"Buchungsart {i + 1}", value=1, step=1, key=f"btyp_{i}")
        waehrung = st.text_input(f"Währung {i + 1}", value="EUR", key=f"waehrung_{i}")

        edited_rows.append({
            "betrag": betrag,
            "steuersatz": steuersatz,
            "steuerkennzeichen": steuerkennzeichen,
            "buchungstext": buchungstext,
            "konto": konto,
            "gegenkonto": gegenkonto,
            "buchungsart": buchungsart,
            "waehrung": waehrung
        })

    # CSV erstellen
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Buchungsdatum", "Belegdatum", "Belegnummer", "Buchungstext",
        "Konto", "Gegenkonto", "Betrag", "Steuerkennzeichen", "Buchungsart", "Währung"
    ])

    for row in edited_rows:
        writer.writerow([
            buchungsdatum.strftime("%Y-%m-%d"),
            belegdatum,
            belegnummer,
            row["buchungstext"],
            row["konto"],
            row["gegenkonto"],
            row["betrag"],
            row["steuerkennzeichen"],
            row["buchungsart"],
            row["waehrung"]
        ])

    st.download_button(
        label="💾 CSV-Datei herunterladen",
        data=output.getvalue(),
        file_name=f"buchung_{belegnummer}.csv",
        mime="text/csv"
    )

    # Optional: Zurücksetzen-Button
    if st.button("🔁 Neue Datei hochladen / Zurücksetzen"):
        st.session_state.clear()
        st.experimental_rerun()