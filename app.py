import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

# --- DATABASE CONNECTION ---
# Pastikan URL ini sesuai dengan Google Sheets Anda
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url, ttl=0)
        return data.dropna(subset=['Produk'])
    except:
        return pd.DataFrame(columns=["Barcode", "Produk", "Stok", "Harga Modal", "Harga Jual", "Exp Date"])

def format_rupiah(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- SISTEM LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 BRANZ TECH Login")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Masuk"):
        if user == "admin" and pw == "branz123":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Username/Password Salah")
    st.stop()

# --- LOAD DATA ASLI ---
df = load_data()

# --- SIDEBAR ---
with st.sidebar:
    # Menggunakan placeholder jika logo belum di-upload
    st.image("https://via.placeholder.com/150?text=BRANZ+TECH", width=150)
    st.title("BRANZ TECH")
    st.write(f"Tanggal: **{datetime.now().strftime('%d %m %Y')}**")
    menu = st.radio("Navigasi", ["Dashboard", "Update Stok", "Kasir/Penjualan"])
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# --- HALAMAN 1: DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Analisis Bisnis Pro")
    
    # Metrik Utama
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Total Produk", len(df))
    with col_m2:
        total_stok = df['Stok'].sum() if not df.empty else 0
        st.metric("Total Stok", f"{int(total_stok)} pcs")
    with col_m3:
        aset = (df['Stok'] * df['Harga Jual']).sum() if not df.empty else 0
        st.metric("Nilai Aset Jual", format_rupiah(aset))

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Komposisi Stok")
        if not df.empty:
            fig = px.pie(df, values='Stok', names='Produk', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("📈 Grafik Stok Barang")
        if not df.empty:
            fig_bar = px.bar(df, x="Produk", y="Stok", color="Stok")
            st.plotly_chart(fig_bar, use_container_width=True)

# --- HALAMAN 2: UPDATE STOK ---
elif menu == "Update Stok":
    st.title("📥 Manajemen Gudang")
    st.info("Silakan update data melalui Google Sheets, lalu refresh aplikasi ini.")
    st.link_button("Buka Google Sheets", url)
    st.divider()
    st.write("Data Saat Ini:")
    st.dataframe(df, use_container_width=True)

# --- HALAMAN 3: KASIR ---
else:
    st.title("💸 Kasir Digital")
    if not df.empty:
        pilih = st.selectbox("Pilih Produk", df['Produk'].unique())
        qty = st.number_input("Jumlah Beli", min_value=1, step=1)
        
        harga = df[df['Produk'] == pilih]['Harga Jual'].values[0]
        total = harga * qty
        
        st.subheader(f"Total Bayar: {format_rupiah(total)}")
        if st.button("Proses & Cetak"):
            st.success("Transaksi Berhasil (Simulasi)")
            st.balloons()
    else:
        st.warning("Data produk kosong.")
