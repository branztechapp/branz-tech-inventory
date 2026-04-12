import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
import datetime

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

# --- 2. DATA ENGINE ---
URL_SHEET = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

# Inisialisasi koneksi
conn = st.connection("branz_tech_db", type=GSheetsConnection)

def load_data():
    try:
        # Ambil data terbaru dengan TTL=0 agar tidak mengambil cache lama
        data = conn.read(spreadsheet=URL_SHEET, ttl=0)
        data.columns = data.columns.str.strip() 
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        return df_clean
    except Exception as e:
        st.error(f"Gagal Load Data: {e}")
        return pd.DataFrame()

def save_to_google_sheets(dataframe):
    try:
        # Metode update yang lebih paksa
        conn.update(spreadsheet=URL_SHEET, data=dataframe)
        st.cache_data.clear() # Bersihkan cache agar data baru terbaca
        return True
    except Exception as e:
        st.error(f"Gagal Simpan ke Cloud: {e}")
        return False

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'last_receipt' not in st.session_state: st.session_state.last_receipt = None

# Load data hanya sekali di awal sesi
if 'df_local' not in st.session_state:
    st.session_state.df_local = load_data()

# --- 4. LOGIN SYSTEM ---
if not st.session_state.auth:
    st.title("💎 BRANZ TECH LOGIN")
    u = st.text_input("Username").lower()
    p = st.text_input("Password", type="password")
    if st.button("Masuk"):
        users = {"admin": "branz123", "aisyah": "aisyah99"}
        if u in users and users[u] == p:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 5. NAVIGATION ---
df = st.session_state.df_local

with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    menu = st.radio("Menu", ["📊 Dashboard", "📦 Inventaris", "🛒 Kasir (POS)"])
    
    if st.button("🔄 Paksa Sinkron Cloud"):
        st.session_state.df_local = load_data()
        st.rerun()

# --- 6. LOGIKA KASIR (INTI PERUBAHAN) ---
if menu == "🛒 Kasir (POS)":
    st.title("🛒 Kasir")
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        product_list = [f"{row['Produk']} | Stok: {int(row['Stok'])}" for _, row in df.iterrows()]
        pilih = st.selectbox("Pilih Produk", [""] + product_list)
        
        if pilih:
            nama_p = pilih.split(" | ")[0]
            stok_skrg = df[df['Produk'] == nama_p]['Stok'].values[0]
            qty = st.number_input("Jumlah", min_value=1, max_value=int(stok_skrg), value=1)
            
            if st.button("➕ Tambah Ke Keranjang"):
                st.session_state.cart[nama_p] = st.session_state.cart.get(nama_p, 0) + qty
                # KURANGI STOK DI MEMORI LOKAL DULU
                idx = df[df['Produk'] == nama_p].index
                st.session_state.df_local.loc[idx, 'Stok'] -= qty
                st.rerun()

    with col2:
        st.subheader("Keranjang")
        total = 0
        for p, q in list(st.session_state.cart.items()):
            harga = df[df['Produk'] == p]['Harga Jual'].values[0]
            subtotal = harga * q
            total += subtotal
            st.write(f"{p} ({q}) = Rp {subtotal:,.0f}")
        
        st.write(f"### TOTAL: Rp {total:,.0f}")
        
        if st.button("✅ SELESAIKAN TRANSAKSI"):
            if st.session_state.cart:
                with st.spinner("Menyimpan ke Google Sheets... Mohon Tunggu..."):
                    # DISINILAH DATA DIKIRIM KE CLOUD
                    berhasil = save_to_google_sheets(st.session_state.df_local)
                    
                    if berhasil:
                        st.success("Stok Terupdate di Cloud!")
                        st.session_state.cart = {} # Kosongkan keranjang
                        st.rerun()
            else:
                st.warning("Keranjang masih kosong")

elif menu == "📊 Dashboard":
    st.title("Dashboard")
    st.metric("Total Stok Barang", int(df['Stok'].sum()))
    st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventaris":
    st.title("Daftar Barang")
    st.table(df[['Produk', 'Stok', 'Harga Jual']])
