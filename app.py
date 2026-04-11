import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- KONFIGURASI ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

def format_rp(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- LOGIN ---
users = {"admin": "branz123", "agen_aisyah": "aisyah99", "agen_nikmat": "cireng77"}

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 BRANZ TECH LOGIN")
    user = st.text_input("Username")
    passw = st.text_input("Password", type="password")
    if st.button("Masuk"):
        if user in users and users[user] == passw:
            st.session_state.auth = True
            st.session_state.user_now = user
            st.rerun()
        else:
            st.error("Username/Password salah!")
    st.stop()

# --- DATA ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url, ttl=0)
    df = df.dropna(subset=['Produk'])
except:
    st.error("Gagal terhubung ke Google Sheets.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🚀 BRANZ TECH")
    st.write(f"👤 User: **{st.session_state.user_now}**")
    menu = st.radio("Menu", ["Dashboard", "Transaksi"])
    if st.button("Logout"):
        st.session_state.auth = False
        st.rerun()

# --- DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Dashboard Inventaris")
    st.dataframe(df[['Produk', 'Stok', 'Harga Jual']], use_container_width=True)
    fig = px.bar(df, x="Produk", y="Stok", title="Grafik Stok")
    st.plotly_chart(fig, use_container_width=True)

# --- TRANSAKSI ---
else:
    st.title("💸 Kasir")
    produk_pilih = st.selectbox("Pilih Produk", df['Produk'].unique())
    qty = st.number_input("Jumlah", min_value=1, step=1)
    if st.button("Cetak Struk"):
        st.success("Transaksi Berhasil!")
        st.write(f"Produk: {produk_pilih}")
        st.write(f"Total: {format_rp(df[df['Produk']==produk_pilih]['Harga Jual'].values[0] * qty)}")
