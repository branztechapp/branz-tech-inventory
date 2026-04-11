import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import urllib.parse

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

# Fungsi format mata uang
def format_rp(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- 2. SISTEM LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 BRANZ TECH LOGIN")
    user = st.text_input("Username")
    passw = st.text_input("Password", type="password")
    if st.button("Masuk"):
        if user == "admin" and passw == "branz123":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Username/Password salah!")
    st.stop()

# --- 3. KONEKSI GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # ttl=0 memastikan aplikasi selalu ambil data terbaru dari Sheets
    df = conn.read(spreadsheet=url, ttl=0)
    # Bersihkan baris kosong berdasarkan kolom Produk
    df = df.dropna(subset=['Produk'])
except Exception as e:
    st.error(f"Koneksi GSheets Gagal: {e}")
    st.stop()

# --- 4. SIDEBAR & NAVIGASI ---
with st.sidebar:
    st.title("🚀 BRANZ TECH")
    st.write(f"📅 {datetime.now().strftime('%d/%m/%Y')}")
    menu = st.radio("Menu Utama", ["Dashboard & Grafik", "Update Stok", "Transaksi Penjualan"])
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 5. DASHBOARD & GRAFIK ---
if menu == "Dashboard & Grafik":
    st.title("📊 Analisis Bisnis Real-Time")
    
    col1, col2 = st.columns(2)
    with col1:
        total_stok = df['Stok'].sum()
        st.metric("Total Stok Barang", f"{int(total_stok)} Pcs")
    with col2:
        df['Total Modal'] = df['Stok'] * df['Harga Modal']
        nilai_aset = df['Total Modal'].sum()
        st.metric("Nilai Aset (Modal)", format_rp(nilai_aset))

    st.divider()

    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("📦 Status Stok")
        fig = px.bar(df, x="Produk", y="Stok", color="Stok", 
                     color_continuous_scale="RdYlGn", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("📑 Data Inventaris")
        st.dataframe(df[['Barcode', 'Produk', 'Stok', 'Harga Jual']], use_container_width=True)

# --- 6. UPDATE STOK ---
elif menu == "Update Stok":
    st.title("📥 Input Produk Baru")
    st.info("Silakan update data langsung di Google Sheets untuk sinkronisasi permanen.")
    st.link_button("📂 Buka Google Sheets", url)
    st.write("Data saat ini di Sheets:")
    st.table(df)

# --- 7. TRANSAKSI ---
elif menu == "Transaksi Penjualan":
    st.title("💸 Kasir Digital")
    produk_pilih = st.selectbox("Pilih Barang", df['Produk'].unique())
    qty = st.number_input("Jumlah Terjual", min_value=1, step=1)
    
    # Ambil data produk terpilih
    data_p = df[df['Produk'] == produk_pilih].iloc[0]
    total_bayar = data_p['Harga Jual'] * qty
    laba = (data_p['Harga Jual'] - data_p['Harga Modal']) * qty
    
    st.write(f"Total Bayar: **{format_rp(total_bayar)}**")
    
    if st.button("Proses & Hitung Laba"):
        st.balloons()
        st.success(f"Transaksi Berhasil! Laba: {format_rp(laba)}")
        
        # Link Notif WA jika stok kritis
        sisa_stok = data_p['Stok'] - qty
        if sisa_stok <= 5:
            pesan = f"⚠️ *STOK KRITIS: {produk_pilih}*\nSisa: {sisa_stok} pcs."
            wa_url = f"https://wa.me/?text={urllib.parse.quote(pesan)}"
            st.link_button("📲 Kirim Notif WA ke Owner", wa_url)
