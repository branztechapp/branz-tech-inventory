import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
    .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
    .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
# URL Spreadsheet Anda
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"

# Koneksi otomatis membaca dari [connections.gsheets] di Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # PENTING: Spreadsheet harus disebutkan di sini
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip() 
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        return df_clean
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return pd.DataFrame()

def save_to_cloud(dataframe):
    try:
        # PENTING: Spreadsheet harus disebutkan di sini agar tidak error "must be specified"
        conn.update(spreadsheet=URL_DB, data=dataframe)
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Gagal Update Cloud: {e}")
        return False

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'df_local' not in st.session_state:
    st.session_state.df_local = load_data()

# --- 4. LOGIN SYSTEM ---
if not st.session_state.auth:
    _, col_center, _ = st.columns([1, 1, 1])
    with col_center:
        st.title("💎 LOGIN")
        u = st.text_input("Username").lower().strip()
        p = st.text_input("Password", type="password")
        if st.button("AUTHENTICATE", use_container_width=True):
            users = {"admin": "branz123", "aisyah": "aisyah99"}
            if u in users and users[u] == p:
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Access Denied")
    st.stop()

# --- 5. NAVIGATION ---
df = st.session_state.df_local

with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    st.divider()
    menu = st.radio("Menu Navigasi", ["📊 Dashboard", "📦 Inventaris", "🛒 Kasir (POS)"])
    st.divider()
    if st.button("🔄 Sinkron Cloud (Refresh)", use_container_width=True):
        st.session_state.df_local = load_data()
        st.rerun()
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 6. PAGE LOGIC ---
if menu == "📊 Dashboard":
    st.title("📈 Business Analytics")
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Asset (Stok)", f"Rp {(df['Stok'] * df['Harga Jual']).sum():,.0f}")
        c2.metric("Varian Produk", len(df))
        c3.metric("Item Stok Rendah", len(df[df['Stok'] < 5]))
        st.subheader("Grafik Persediaan")
        st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventaris":
    st.title("📦 Database Produk")
    search = st.text_input("Cari Nama Produk...")
    filt_df = df[df['Produk'].str.contains(search, case=False)] if search else df
    st.dataframe(filt_df, use_container_width=True, hide_index=True)

elif menu == "🛒 Kasir (POS)":
    st.title("🛒 POS Terminal")
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.subheader("Input Produk")
        prod_options = [f"{r['Produk']} | Sisa: {int(r['Stok'])}" for _, r in df.iterrows()]
        pick = st.selectbox("Pilih Barang", [""] + prod_options)
        
        if pick:
            name_only = pick.split(" | ")[0]
            current_stock = df[df['Produk'] == name_only]['Stok'].values[0]
            qty = st.number_input("Jumlah Beli", min_value=1, max_value=int(current_stock) if current_stock > 0 else 1, value=1)
            
            if st.button("➕ Tambah ke Keranjang", use_container_width=True):
                if current_stock >= qty:
                    st.session_state.cart[name_only] = st.session_state.cart.get(name_only, 0) + qty
                    idx = df[df['Produk'] == name_only].index
                    st.session_state.df_local.loc[idx, 'Stok'] -= qty
                    st.rerun()
                else:
                    st.error("Stok tidak mencukupi!")

    with col_right:
        st.subheader("📝 Detail Pesanan")
        total_belanja = 0
        if not st.session_state.cart:
            st.info("Keranjang kosong.")
        else:
            for item, q in list(st.session_state.cart.items()):
                price = df[df['Produk'] == item]['Harga Jual'].values[0]
                sub = price * q
                total_belanja += sub
                c_item, c_del = st.columns([4, 1])
                c_item.write(f"**{item}** \n{q} x Rp {price:,.0f} = Rp {sub:,.0f}")
                if c_del.button("🗑️", key=f"del_{item}"):
                    idx = df[df['Produk'] == item].index
                    st.session_state.df_local.loc[idx, 'Stok'] += st.session_state.cart[item]
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            st.write(f"### TOTAL: Rp {total_belanja:,.0f}")
            
            if st.button("💎 SELESAIKAN & SIMPAN CLOUD", use_container_width=True):
                with st.spinner("Mengupdate Google Sheets..."):
                    if save_to_cloud(st.session_state.df_local):
                        st.success("Transaksi Berhasil!")
                        st.session_state.cart = {}
                        st.rerun()
