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

# ---------------- NEUES JSON-SCHEMA DEFINIEREN ----------------
EXTRACTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Extracted Invoice Information",
    "type": "object",
    "properties": {
        "document_info": {
            "type": "object",
            "properties": {
                "belegdatum": {"type": "string"},
                "belegnummer": {"type": "string"}
            },
            "required": ["belegdatum", "belegnummer"]
        },
        "summary": {
            "type": "object",
            "properties": {
                "tax_rate": {"type": "string"},
                "tax_amount": {"type": "number"},
                "net_total": {"type": "number"},
                "gross_total": {"type": "number"}
            },
            "required": ["tax_rate", "tax_amount", "net_total", "gross_total"]
        }
    },
    "required": ["document_info", "summary"]
}

# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title="BDP", page_icon="📄")
st.title("📄 DATAC Invoice Extraction")

# FILE UPLOAD
uploaded_file = st.file_uploader("Lade eine Rechnung hoch (PDF)", type=["pdf"])

# EXTRACT DATA
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

# FIELDS
if "extracted_data" in st.session_state:
    extracted_data = st.session_state["extracted_data"]
    st.success("✅ Daten erfolgreich extrahiert!")

    st.subheader("🧾 Rechnungs Informationen")
    
    # BUCHUNGSDATUM
    buchungsdatum = st.date_input("Buchungsdatum", value=date.today())
    
    # BELEGDATUM & BELEGNUMMER
    doc_info = extracted_data.get("document_info", {})
    belegdatum = st.text_input("Belegdatum", value=doc_info.get("belegdatum", ""))
    belegnummer = st.text_input("Belegnummer", value=doc_info.get("belegnummer", ""))

    summary = extracted_data.get("summary", {})
    
    # STEURSATZ
    tax_rate = st.text_input("Steuersatz (%)", value=summary.get("tax_rate", ""))
    
    # NWST
    tax_amount = st.number_input("MWST.", value=summary.get("tax_amount", 0.0), step=0.01)
    
    # NETTOBETRAG
    net_total = st.number_input("Nettobetrag", value=summary.get("net_total", 0.0), step=0.01)
    gross_total = st.number_input("Bruttobetrag", value=summary.get("gross_total", 0.0), step=0.01)

    # CSV Export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Buchungsdatum", "Belegdatum", "Belegnummer",
        "Steuersatz", "Mehrwertsteuer", "Netto", "Brutto"
    ])
    writer.writerow([
        buchungsdatum.strftime("%Y-%m-%d"),
        belegdatum,
        belegnummer,
        tax_rate,
        tax_amount,
        net_total,
        gross_total
    ])

    st.download_button(
        label="💾 CSV-Datei herunterladen",
        data=output.getvalue(),
        file_name=f"rechnung_{belegnummer}.csv",
        mime="text/csv"
    )

    # Zurücksetzen
    if st.button("🔁 Neue Datei hochladen / Zurücksetzen"):
        st.session_state.clear()
        st.experimental_rerun()