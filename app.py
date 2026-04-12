import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Konfigurasi Halaman
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide")
st.title("🚀 BRANZ TECH INVENTORY")

# Link Google Sheets Anda
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url, ttl=0)
    st.success("✅ Koneksi Berhasil!")
    
    # Menampilkan tabel data
    st.subheader("Data Inventaris Real-Time")
    st.dataframe(df, use_container_width=True)
    
except Exception as e:
    st.error(f"❌ Gagal memuat data: {e}")
