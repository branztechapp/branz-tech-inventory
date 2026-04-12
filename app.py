import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import datetime
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
    .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
    .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
    [data-testid="stMetricValue"] { color: #60a5fa !important; }
    div[data-baseweb="input"] { border: 1px solid #3b82f6 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip()
        df = data.dropna(subset=['Produk']).copy()
        df['Stok'] = pd.to_numeric(df['Stok'], errors='coerce').fillna(0).astype(int)
        df['Harga Jual'] = pd.to_numeric(df['Harga Jual'], errors='coerce').fillna(0)
        df['Barcode'] = df['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        return df
    except Exception as e:
        st.error(f"Koneksi GSheets Gagal: {e}")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual', 'Barcode'])

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'history' not in st.session_state: st.session_state.history = []
if 'df_local' not in st.session_state: st.session_state.df_local = load_data()

# --- 4. LOGIC FUNCTIONS ---
def add_to_cart(p_name):
    df = st.session_state.df_local
    idx = df[df['Produk'] == p_name].index[0]
    if df.at[idx, 'Stok'] > 0:
        st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1
        st.session_state.df_local.at[idx, 'Stok'] -= 1
        return True
    return False

def remove_from_cart(p_name):
    if p_name in st.session_state.cart:
        df = st.session_state.df_local
        idx = df[df['Produk'] == p_name].index[0]
        st.session_state.df_local.at[idx, 'Stok'] += 1
        
        if st.session_state.cart[p_name] > 1:
            st.session_state.cart[p_name] -= 1
        else:
            del st.session_state.cart[p_name]

# --- 5. LOGIN ---
if not st.session_state.auth:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.title("💎 LOGIN")
        u = st.text_input("User").lower()
        p = st.text_input("Pass", type="password")
        if st.button("LOGIN"):
            if u == "admin" and p == "branz123":
                st.session_state.auth, st.session_state.user = True, u
                st.rerun()
    st.stop()

# --- 6. MAIN UI ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    menu = st.radio("Menu", ["🛒 Kasir", "📦 Stok", "📜 Log"])
    if st.button("🔄 Sync Data"):
        st.cache_data.clear()
        st.session_state.df_local = load_data()
        st.rerun()

if menu == "🛒 Kasir":
    st.title("🛒 BRANZ POS")
    df = st.session_state.df_local

    # Barcode Input
    barcode_val = st.text_input("⚡ SCAN BARCODE", key="scan_input").strip()
    if barcode_val:
        match = df[df['Barcode'] == barcode_val]
        if not match.empty:
            if add_to_cart(match.iloc[0]['Produk']):
                st.toast(f"Ditambahkan: {match.iloc[0]['Produk']}")
            else:
                st.error("Stok Habis!")
        st.rerun() # Penting agar input kosong kembali setelah enter

    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        cust = st.text_input("Nama Pelanggan", "Umum")
        st.divider()
        options = [f"{r['Produk']} | Stok: {r['Stok']}" for _, r in df.iterrows()]
        pick = st.selectbox("Pilih Manual", [""] + options)
        if pick:
            p_sel = pick.split(" | ")[0]
            if st.button("➕ Tambah ke Keranjang"):
                add_to_cart(p_sel)
                st.rerun()

    with c2:
        st.subheader("📝 Keranjang")
        subtotal = 0
        for item, qty in list(st.session_state.cart.items()):
            harga = df[df['Produk'] == item]['Harga Jual'].values[0]
            subtotal += (harga * qty)
            
            # Baris Item dengan Tombol +/-
            with st.container():
                col_n, col_p, col_m, col_d = st.columns([2, 0.6, 0.6, 0.6])
                col_n.write(f"**{item}**\n{qty} x {harga:,.0f}")
                
                if col_p.button("➕", key=f"p_{item}"):
                    add_to_cart(item)
                    st.rerun()
                
                if col_m.button("➖", key=f"m_{item}"):
                    remove_from_cart(item)
                    st.rerun()
                
                if col_d.button("🗑️", key=f"d_{item}"):
                    idx = df[df['Produk'] == item].index[0]
                    st.session_state.df_local.at[idx, 'Stok'] += qty
                    del st.session_state.cart[item]
                    st.rerun()
            st.divider()

        total = st.number_input("Total Final (Diskon Manual)", value=float(subtotal))
        st.metric("Total Bayar", f"Rp {total:,.0f}")
        
        if st.button("🏁 SELESAI & CETAK", use_container_width=True):
            if st.session_state.cart:
                st.session_state.history.append({"Waktu": datetime.datetime.now(), "Total": total})
                st.session_state.cart = {}
                st.success("Transaksi Berhasil!")
                st.balloons()
            else:
                st.warning("Keranjang Kosong")

elif menu == "📦 Stok":
    st.title("📦 Inventaris")
    st.dataframe(st.session_state.df_local, use_container_width=True)

elif menu == "📜 Log":
    st.title("📜 Log Transaksi")
    st.write(st.session_state.history)
