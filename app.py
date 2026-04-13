import streamlit as st
from st_gsheets_connection import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. KONFIGURASI HALAMAN & STYLE ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .main-card { background: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 1.8rem !important; }
    </style>
    """, unsafe_allow_html=True)

# Fungsi format mata uang
def format_rp(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- 2. SISTEM LOGIN ---
users = {
    "admin": "branz123",
    "agen_aisyah": "aisyah99",
    "agen_nikmat": "cireng77"
}

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'cart': {}})

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        st.title("🔒 BRANZ TECH LOGIN")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if u in users and users[u] == p:
                st.session_state.auth = True
                st.session_state.user = u
                st.session_state.role = "admin" if u == "admin" else "staff"
                st.rerun()
            else: st.error("Login Gagal!")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 3. KONEKSI DATA ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        df = data.copy().dropna(subset=['Produk'])
        df['Stok'] = pd.to_numeric(df['Stok']).fillna(0).astype(int)
        df['Harga Modal'] = pd.to_numeric(df['Harga Modal']).fillna(0)
        df['Harga Jual'] = pd.to_numeric(df['Harga Jual']).fillna(0)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

if 'df_local' not in st.session_state:
    st.session_state.df_local = load_data()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🚀 BRANZ TECH")
    st.write(f"👤 **{st.session_state.user}** ({st.session_state.role})")
    menu = st.radio("Menu Utama", ["Dashboard", "Kasir POS", "Update Stok"])
    st.divider()
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 5. DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Analisis Bisnis")
    df = st.session_state.df_local
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Stok", f"{df['Stok'].sum()} Pcs")
    m2.metric("Nilai Aset", format_rp((df['Stok'] * df['Harga Modal']).sum()))
    m3.metric("Potensi Profit", format_rp(((df['Harga Jual'] - df['Harga Modal']) * df['Stok']).sum()))
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(df, x="Produk", y="Stok", color="Stok", title="Level Stok Barang", color_continuous_scale="Viridis")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("📋 Daftar Inventaris")
        st.dataframe(df[['Produk', 'Stok', 'Harga Jual']], use_container_width=True, hide_index=True)

# --- 6. KASIR POS (PRO) ---
elif menu == "Kasir POS":
    st.title("💸 Kasir Digital")
    df = st.session_state.df_local
    
    col_input, col_cart = st.columns([1, 1.2])
    
    with col_input:
        st.subheader("Input Barang")
        p_pilih = st.selectbox("Cari Produk", df['Produk'].unique())
        qty = st.number_input("Jumlah", min_value=1, step=1)
        
        if st.button("➕ Tambah ke Keranjang"):
            stok_ada = df[df['Produk'] == p_pilih]['Stok'].values[0]
            qty_skrg = st.session_state.cart.get(p_pilih, 0)
            
            if (qty_skrg + qty) <= stok_ada:
                st.session_state.cart[p_pilih] = qty_skrg + qty
                st.toast(f"{p_pilih} ditambahkan!")
            else:
                st.error("Stok tidak mencukupi!")

    with col_cart:
        st.subheader("🛒 Keranjang")
        if not st.session_state.cart:
            st.info("Keranjang kosong")
        else:
            grand_total = 0
            for item, q in list(st.session_state.cart.items()):
                harga = df[df['Produk'] == item]['Harga Jual'].values[0]
                subtotal = harga * q
                grand_total += subtotal
                c_item, c_del = st.columns([3, 1])
                c_item.write(f"**{item}** ({q}x) - {format_rp(subtotal)}")
                if c_del.button("❌", key=f"del_{item}"):
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            st.subheader(f"Total: {format_rp(grand_total)}")
            
            if st.button("🏁 SELESAI & UPDATE CLOUD", type="primary"):
                # Update Stok di DataFrame Lokal
                for item, q in st.session_state.cart.items():
                    idx = df[df['Produk'] == item].index[0]
                    df.at[idx, 'Stok'] -= q
                
                # Push ke Google Sheets
                conn.update(spreadsheet=URL_DB, data=df)
                st.session_state.df_local = df
                st.session_state.cart = {}
                st.success("Transaksi Berhasil & Stok Terpotong!")
                st.balloons()
                st.rerun()

# --- 7. UPDATE STOK (ADMIN ONLY) ---
elif menu == "Update Stok":
    st.title("📥 Manajemen Data & Stok")
    df = st.session_state.df_local

    if st.session_state.role == "admin":
        with st.expander("🛠️ Form Edit Stok / Produk Baru", expanded=True):
            with st.form("edit_form"):
                f_nama = st.text_input("Nama Produk (Sesuai database atau Baru)")
                f_modal = st.number_input("Harga Modal", min_value=0)
                f_jual = st.number_input("Harga Jual", min_value=0)
                f_stok = st.number_input("Jumlah Stok", min_value=0)
                f_bc = st.text_input("Barcode (Opsional)")
                
                if st.form_submit_button("Simpan Permanen ke Cloud"):
                    df_up = df.copy()
                    if f_nama in df_up['Produk'].values:
                        idx = df_up[df_up['Produk'] == f_nama].index[0]
                        df_up.at[idx, 'Stok'] = f_stok
                        df_up.at[idx, 'Harga Modal'] = f_modal
                        df_up.at[idx, 'Harga Jual'] = f_jual
                        if f_bc: df_up.at[idx, 'Barcode'] = f_bc
                    else:
                        new_row = pd.DataFrame([{'Produk': f_nama, 'Stok': f_stok, 'Harga Modal': f_modal, 'Harga Jual': f_jual, 'Barcode': f_bc}])
                        df_up = pd.concat([df_up, new_row], ignore_index=True)
                    
                    conn.update(spreadsheet=URL_DB, data=df_up)
                    st.session_state.df_local = df_up
                    st.success("Data Berhasil Diupdate!")
                    st.rerun()
    else:
        st.warning("Hanya Admin yang dapat mengedit data stok.")
        st.table(df[['Produk', 'Stok', 'Harga Jual']])
