import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import urllib.parse

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

# --- SISTEM LOGIN SEDERHANA ---
def login():
    st.title("🔒 BRANZ TECH Login")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Masuk"):
        if user == "admin" and pw == "branz123": # Ganti sesuai keinginan
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Username/Password Salah")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# --- DATABASE & FORMATTING ---
def format_rupiah(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# Simulasi Database (Nanti kita hubungkan ke link GSheets kamu)
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=["Barcode", "Produk", "Stok", "Harga Modal", "Harga Jual", "Exp Date"])
if 'sales' not in st.session_state:
    st.session_state.sales = pd.DataFrame(columns=["Waktu", "Produk", "Laba"])

# --- SIDEBAR (LOGO & MENU) ---
with st.sidebar:
    # Ganti URL di bawah dengan link gambar logo BRANZ TECH kamu
    st.image("https://via.placeholder.com/150?text=BRANZ+TECH", width=150)
    st.title("BRANZ TECH")
    st.write(f"User: **{datetime.now().strftime('%d %B %Y')}**")
    menu = st.radio("Navigasi", ["Dashboard", "Update Stok", "Kasir/Penjualan"])
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# --- HALAMAN 1: DASHBOARD OPTIMASI ---
if menu == "Dashboard":
    st.title("📊 Analisis Bisnis Pro")
    
    total_laba = st.session_state.sales['Laba'].sum()
    st.metric("Total Keuntungan", format_rupiah(total_laba))

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📦 Inventory Chart")
        if not st.session_state.inventory.empty:
            fig = px.pie(st.session_state.inventory, values='Stok', names='Produk', 
                         hole=0.4, title="Komposisi Stok Barang")
            st.plotly_chart(fig, use_container_width=True)
            
    with col2:
        st.subheader("📈 Profit Tracker")
        if not st.session_state.sales.empty:
            fig_line = px.area(st.session_state.sales, x="Waktu", y="Laba", 
                               title="Tren Keuntungan", color_discrete_sequence=['#00CC96'])
            st.plotly_chart(fig_line, use_container_width=True)

# --- HALAMAN 2: UPDATE STOK ---
elif menu == "Update Stok":
    st.title("📥 Manajemen Gudang")
    # ... (Kode Input sama seperti sebelumnya namun ditambahkan format rupiah saat tampil)
    st.data_editor(st.session_state.inventory) # Member bisa edit langsung di tabel

# --- HALAMAN 3: KASIR ---
elif menu == "Kasir/Penjualan":
    st.title("💸 Kasir Digital")
    # ... (Kode Kasir dengan format_rupiah(laba))
