import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF

# --- CONFIG ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide")

# --- DATABASE ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Menambahkan parameter headers=0 agar baris pertama dianggap judul kolom
        data = conn.read(spreadsheet=url, ttl=0)
        return data.dropna(subset=['Produk'])
    except Exception as e:
        st.error(f"Error Database: {e}")
        return pd.DataFrame()

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🛡️ BRANZ TECH SaaS")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        # Daftar Partner Anda
        partners = {"admin": "branz123", "aisyah": "aisyah99", "nikmat": "cireng77"}
        if u in partners and partners[u] == p:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Gagal!")
    st.stop()

# --- FILTERING DATA ---
full_df = load_data()
# Mengambil data HANYA yang Owner_ID-nya sama dengan user yang login
df = full_df[full_df['Owner_ID'] == st.session_state.user] if not full_df.empty else full_df

st.sidebar.title(f"Partner: {st.session_state.user.upper()}")
menu = st.sidebar.radio("Menu", ["Stok Saya", "Scan Barcode", "Kasir"])

if menu == "Stok Saya":
    st.title(f"📦 Inventaris {st.session_state.user}")
    st.dataframe(df, use_container_width=True)

elif menu == "Scan Barcode":
    st.title("📷 Scanner HP")
    cam = st.camera_input("Scan Barcode")
    if cam:
        data = decode(Image.open(cam))
        if data:
            code = data[0].data.decode('utf-8')
            st.success(f"Barcode: {code}")
            item = df[df['Barcode'].astype(str) == code]
            if not item.empty:
                st.write(item)
            else:
                st.warning("Produk tidak ada di database Anda.")

elif menu == "Kasir":
    st.title("💸 Cetak Struk")
    if not df.empty:
        prod = st.selectbox("Pilih Produk", df['Produk'].unique())
        if st.button("Download Struk PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=15)
            pdf.cell(200, 10, txt=f"STRUK BRANZ TECH - {st.session_state.user}", ln=1, align='C')
            pdf.cell(200, 10, txt=f"Produk: {prod}", ln=2)
            pdf.output("struk.pdf")
            with open("struk.pdf", "rb") as f:
                st.download_button("Klik untuk Simpan Struk", f, file_name="struk.pdf")
