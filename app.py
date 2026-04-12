import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import datetime
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
        .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
        .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
        [data-testid="stMetricValue"] { color: #60a5fa !important; }
        div[data-baseweb="input"] { border: 1px solid #3b82f6 !important; }
        /* Styling khusus untuk tombol +/- agar sejajar */
        .qty-text { font-size: 1.2rem; font-weight: bold; text-align: center; padding-top: 5px; }
        </style>
        """, unsafe_allow_html=True)

apply_custom_style()

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip()
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0).astype(int)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        df_clean['Barcode'] = df_clean['Barcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_clean['Barcode'] = df_clean['Barcode'].replace(['nan', 'None', ''], 'KOSONG')
        return df_clean
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual', 'Barcode'])

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'history' not in st.session_state: st.session_state.history = []
if 'df_local' not in st.session_state: st.session_state.df_local = load_data()

# --- 4. FUNCTIONS ---
def update_qty(item_name, delta):
    """Fungsi pusat untuk tambah/kurang item agar state tetap sinkron"""
    df = st.session_state.df_local
    idx = df[df['Produk'] == item_name].index[0]
    current_qty = st.session_state.cart.get(item_name, 0)
    
    if delta > 0: # Tambah
        if df.at[idx, 'Stok'] > 0:
            st.session_state.cart[item_name] = current_qty + 1
            st.session_state.df_local.at[idx, 'Stok'] -= 1
        else:
            st.error(f"Stok {item_name} habis!")
    else: # Kurang
        if current_qty > 1:
            st.session_state.cart[item_name] = current_qty - 1
            st.session_state.df_local.at[idx, 'Stok'] += 1
        else:
            # Jika qty 1 dikurangi, hapus dari keranjang
            st.session_state.df_local.at[idx, 'Stok'] += 1
            del st.session_state.cart[item_name]

# --- 5. LOGIN SYSTEM ---
if not st.session_state.auth:
    _, col_center, _ = st.columns([1, 1, 1])
    with col_center:
        st.title("💎 LOGIN")
        u = st.text_input("Username").lower().strip()
        p = st.text_input("Password", type="password")
        if st.button("AUTHENTICATE", use_container_width=True):
            users = {"admin": "branz123", "aisyah": "aisyah99"}
            if u in users and users[u] == p:
                st.session_state.auth, st.session_state.user = True, u
                st.rerun()
            else: st.error("Akses Ditolak")
    st.stop()

# --- 6. NAVIGATION ---
with st.sidebar:
    st.title("💎 BRANZ TECH")
    st.write(f"User: **{st.session_state.user.upper()}**")
    menu = st.radio("Menu", ["🛒 POS Kasir", "📦 Inventaris", "📜 Log Transaksi"])
    st.divider()
    if st.button("🔄 Sync Cloud"):
        st.cache_data.clear()
        st.session_state.df_local = load_data()
        st.rerun()

# --- 7. MAIN LOGIC ---

if menu == "🛒 POS Kasir":
    st.title("🛒 POS Terminal")
    df = st.session_state.df_local
    
    # 1. Barcode Scanner (Picu otomatis dengan enter)
    scan_val = st.text_input("⚡ SCAN BARCODE", key="scanner", help="Tekan Enter setelah scan").strip()
    if scan_val:
        match = df[df['Barcode'] == scan_val]
        if not match.empty:
            update_qty(match.iloc[0]['Produk'], 1)
            # Reset text input barcode setelah sukses
            st.rerun() 
        elif scan_val != "":
            st.warning("Barcode tidak terdaftar!")

    col_l, col_r = st.columns([1.2, 1])
    
    with col_l:
        cust = st.text_input("Nama Pelanggan / WA", placeholder="08xxxx")
        st.divider()
        st.subheader("🔍 Pilih Produk Manual")
        options = [f"{r['Produk']} | Stok: {r['Stok']}" for _, r in df.iterrows()]
        pick = st.selectbox("Cari Produk", [""] + options)
        if pick:
            p_selected = pick.split(" | ")[0]
            if st.button("➕ Tambah ke Keranjang", use_container_width=True):
                update_qty(p_selected, 1)
                st.rerun()

    with col_r:
        st.subheader("📝 Keranjang Belanja")
        if not st.session_state.cart:
            st.info("Keranjang kosong. Scan barcode atau pilih produk manual.")
        else:
            subtotal = 0
            for item, qty in list(st.session_state.cart.items()):
                price = df[df['Produk'] == item]['Harga Jual'].values[0]
                item_total = price * qty
                subtotal += item_total
                
                # Baris Item di Keranjang
                with st.container():
                    c_info, c_ops = st.columns([1.5, 1])
                    c_info.markdown(f"**{item}** \n`Rp {price:,.0f} x {qty}`")
                    
                    # Tombol Aksi (+, -, Delete)
                    c1, c2, c3, c4 = c_ops.columns([1, 1, 1, 1])
                    if c1.button("➖", key=f"m_{item}"):
                        update_qty(item, -1)
                        st.rerun()
                    
                    c2.markdown(f"<div class='qty-text'>{qty}</div>", unsafe_allow_html=True)
                    
                    if c3.button("➕", key=f"p_{item}"):
                        update_qty(item, 1)
                        st.rerun()
                        
                    if c4.button("🗑️", key=f"d_{item}"):
                        # Kembalikan stok saat dihapus
                        idx = df[df['Produk'] == item].index[0]
                        st.session_state.df_local.at[idx, 'Stok'] += qty
                        del st.session_state.cart[item]
                        st.rerun()
                st.divider()

            # Kalkulasi Akhir
            disc = st.number_input("Diskon (Rp)", min_value=0, step=500, value=0)
            total_akhir = max(0, subtotal - disc)
            
            st.metric("Total Bayar", f"Rp {total_akhir:,.0f}", delta=f"- Rp {disc:,.0f}" if disc > 0 else None)
            
            if st.button("🏁 SELESAIKAN & CETAK", use_container_width=True, type="primary"):
                # Simpan Log
                now = datetime.datetime.now()
                entry = {
                    "Tanggal": now.strftime("%Y-%m-%d"),
                    "Waktu": now.strftime("%H:%M:%S"),
                    "Pelanggan": cust if cust else "Umum",
                    "Item": ", ".join([f"{k}(x{v})" for k,v in st.session_state.cart.items()]),
                    "Total": total_akhir
                }
                st.session_state.history.insert(0, entry)
                st.session_state.cart = {} # Reset Keranjang
                st.success("Transaksi Berhasil!")
                st.balloons()
                st.rerun()

elif menu == "📦 Inventaris":
    st.title("📦 Database Inventaris")
    search = st.text_input("Cari Nama atau Barcode...").lower()
    
    # Filter Data
    id_df = st.session_state.df_local.copy()
    if search:
        mask = id_df['Produk'].str.lower().str.contains(search) | id_df['Barcode'].str.lower().str.contains(search)
        id_df = id_df[mask]
    
    st.dataframe(id_df, use_container_width=True, hide_index=True)

elif menu == "📜 Log Transaksi":
    st.title("📜 Riwayat Transaksi")
    if st.session_state.history:
        st.table(pd.DataFrame(st.session_state.history))
    else:
        st.info("Belum ada transaksi hari ini.")
