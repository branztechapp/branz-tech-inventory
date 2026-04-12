import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIG & STYLING (MEWAH) ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

# CSS untuk tampilan berkelas
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    div.stButton > button:first-child {
        background-color: #00ffcc;
        color: #0e1117;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        transition: 0.3s;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background-color: #00d4aa;
        box-shadow: 0px 0px 15px #00ffcc;
    }
    .stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url, ttl=0)
        return data.dropna(subset=['Produk'])
    except Exception as e:
        st.error(f"Error Database: {e}")
        return pd.DataFrame()

# --- 3. LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🛡️ BRANZ TECH SaaS")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        partners = {"admin": "branz123", "aisyah": "aisyah99", "nikmat": "cireng77"}
        if u in partners and partners[u] == p:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Akses Ditolak!")
    st.stop()

# --- 4. DATA PROCESSING ---
full_df = load_data()
df = full_df[full_df['Owner_ID'] == st.session_state.user] if not full_df.empty else full_df

# --- 5. SIDEBAR ---
with st.sidebar:
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🚀 BRANZ TECH")
    
    st.write(f"Logged in as: **{st.session_state.user.upper()}**")
    st.markdown("---")
    menu = st.radio("Navigation", ["📊 Dashboard", "📦 Stok Saya", "📷 Scan Barcode", "💸 Kasir"])
    
    if st.button("Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 6. MENU LOGIC ---

if menu == "📊 Dashboard":
    st.title(f"📈 Business Overview: {st.session_state.user.upper()}")
    
    if not df.empty:
        # Hitung Metrik Otomatis
        total_omzet_potensial = (df['Stok'] * df['Harga Jual']).sum()
        stok_kritis = df[df['Stok'] <= 10].shape[0]
        total_item = df.shape[0]

        # Tampilan Metrik Berkelas
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Estimasi Omzet", f"Rp {total_omzet_potensial:,.0f}")
        col2.metric("📦 Stok Kritis (<10)", f"{stok_kritis} Produk", delta=f"{stok_kritis}", delta_color="inverse")
        col3.metric("📑 Total Jenis Produk", f"{total_item} Item")
        
        st.markdown("---")
        st.subheader("Produk Dengan Stok Terbanyak")
        st.bar_chart(df.set_index('Produk')['Stok'])
    else:
        st.warning("Belum ada data untuk ditampilkan.")

elif menu == "📦 Stok Saya":
    st.title("📦 Inventaris Produk")
    st.dataframe(df.style.highlight_max(axis=0, subset=['Stok'], color='#1e3a3a'), use_container_width=True)

elif menu == "📷 Scan Barcode":
    st.title("📷 Scanner HP Pro")
    cam = st.camera_input("Scan Barcode")
    if cam:
        data = decode(Image.open(cam))
        if data:
            code = data[0].data.decode('utf-8')
            st.success(f"Barcode Terdeteksi: {code}")
            item = df[df['Barcode'].astype(str) == code]
            if not item.empty:
                st.write(item)
            else:
                st.warning("Produk tidak terdaftar di akun Anda.")

elif menu == "💸 Kasir":
    st.title("💸 Terminal Kasir")
    if not df.empty:
        col_k1, col_k2 = st.columns([1, 1])
        with col_k1:
            prod = st.selectbox("Pilih Produk", df['Produk'].unique())
            qty = st.number_input("Jumlah Beli", min_value=1, step=1)
            
            data_produk = df[df['Produk'] == prod].iloc[0]
            harga = data_produk['Harga Jual']
            total = harga * qty
            st.subheader(f"Total: Rp {total:,.0f}")

        if st.button("🔥 Generate Struk POS"):
            pdf = FPDF(format=(80, 150))
            pdf.add_page()
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(60, 8, txt="BRANZ TECH PRO", ln=1, align='C')
            pdf.set_font("Arial", '', 8)
            pdf.cell(60, 5, txt=f"Mitra: {st.session_state.user.upper()}", ln=1, align='C')
            pdf.cell(60, 5, txt=f"{datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1, align='C')
            pdf.cell(60, 5, txt="-"*40, ln=1, align='C')

            pdf.set_font("Arial", 'B', 9)
            pdf.cell(30, 8, txt="Item", ln=0)
            pdf.cell(10, 8, txt="Qty", ln=0)
            pdf.cell(20, 8, txt="Total", ln=1, align='R')
            
            pdf.set_font("Arial", '', 9)
            pdf.cell(30, 8, txt=f"{prod[:15]}", ln=0)
            pdf.cell(10, 8, txt=f"{qty}", ln=0)
            pdf.cell(20, 8, txt=f"{total:,.0f}", ln=1, align='R')
            
            pdf.cell(60, 5, txt="-"*40, ln=1, align='C')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(30, 10, txt="TOTAL", ln=0)
            pdf.cell(20, 10, txt=f"Rp {total:,.0f}", ln=1, align='R')
            
            pdf.set_font("Arial", 'I', 8)
            pdf.ln(5)
            pdf.cell(60, 5, txt="Terima Kasih - Branz Tech", ln=1, align='C')

            file_name = f"struk_{datetime.now().strftime('%H%M%S')}.pdf"
            pdf.output(file_name)
            with open(file_name, "rb") as f:
                st.download_button("📥 Unduh Struk", f, file_name=file_name, mime="application/pdf")
