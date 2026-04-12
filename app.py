import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import datetime

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
        .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
        .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
        div[data-baseweb="input"] { border: 1px solid #3b82f6 !important; }
        </style>
        """, unsafe_allow_html=True)

apply_custom_style()

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        # Menangani error "Spreadsheet must be specified" dengan memanggil URL langsung
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip() 
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0).astype(int)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        
        if 'Barcode' not in df_clean.columns:
            df_clean['Barcode'] = ""
        df_clean['Barcode'] = df_clean['Barcode'].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df_clean
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual', 'Barcode'])

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'history' not in st.session_state: st.session_state.history = []
if 'df_local' not in st.session_state: st.session_state.df_local = load_data()

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
                st.session_state.auth, st.session_state.user = True, u
                st.rerun()
            else: st.error("Access Denied")
    st.stop()

# --- 5. RECEIPT GENERATOR ---
def generate_receipt(cart_data, subtotal, discount, total, customer, user, df_ref):
    try:
        pdf = FPDF(format=(80, 150))
        pdf.add_page(); pdf.set_font("Courier", 'B', 10)
        pdf.cell(70, 5, "BRANZ TECH PRESTIGE", ln=True, align='C')
        pdf.set_font("Courier", size=8)
        pdf.cell(70, 4, f"Tgl: {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True)
        pdf.cell(70, 4, f"Kasir: {user.upper()} | Cust: {customer if customer else 'Umum'}", ln=True)
        pdf.cell(70, 4, "-"*35, ln=True)
        for item, q in cart_data.items():
            price = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
            pdf.cell(70, 4, f"{item[:20]} x{q} @{price:,.0f}", ln=True)
        pdf.cell(70, 4, "-"*35, ln=True)
        pdf.cell(70, 5, f"TOTAL: Rp {total:,.0f}", ln=True, align='R')
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# --- 6. PAGE LOGIC ---
df = st.session_state.df_local

with st.sidebar:
    st.title("BRANZ TECH")
    menu = st.radio("Navigasi", ["📊 Dashboard", "🛒 Kasir (POS)", "📦 Inventaris"])
    if st.button("🔄 Sinkron Database"):
        st.cache_data.clear()
        st.session_state.df_local = load_data()
        st.rerun()

if menu == "🛒 Kasir (POS)":
    st.title("🛒 POS Terminal")
    
    # Input Utama: Scan Barcode
    bc_pos = st.text_input("⚡ SCAN BARCODE", key="scan_main")
    if bc_pos:
        match = df[df['Barcode'] == bc_pos.strip()]
        if not match.empty:
            p_name = match.iloc[0]['Produk']
            if st.session_state.df_local.loc[df['Barcode'] == bc_pos.strip(), 'Stok'].values[0] > 0:
                st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1
                st.session_state.df_local.loc[df['Barcode'] == bc_pos.strip(), 'Stok'] -= 1
                st.toast(f"Ditambahkan: {p_name}")
            else: st.error("Stok Habis!")

    col_l, col_r = st.columns([1.5, 1])
    
    with col_l:
        cust = st.text_input("Nama Pelanggan / WA", placeholder="0857...")
        st.divider()
        # Pilih Manual
        options = [f"{r['Produk']} | Stok: {r['Stok']}" for _, r in df.iterrows()]
        pick = st.selectbox("Cari Produk Manual", [""] + options)
        if pick:
            name = pick.split(" | ")[0]
            q_add = st.number_input("Jumlah", min_value=1, value=1)
            if st.button("➕ Tambah ke Keranjang"):
                st.session_state.cart[name] = st.session_state.cart.get(name, 0) + q_add
                st.session_state.df_local.loc[df['Produk'] == name, 'Stok'] -= q_add
                st.rerun()

    with col_r:
        st.subheader("📝 Keranjang")
        subtotal = 0
        if not st.session_state.cart: st.info("Keranjang Kosong")
        
        for item, qty in list(st.session_state.cart.items()):
            price = df[df['Produk'] == item]['Harga Jual'].values[0]
            subtotal += (price * qty)
            
            # FITUR BARU: Edit Jumlah & Hapus
            c_name, c_qty, c_del = st.columns([2, 1.5, 0.5])
            c_name.write(f"**{item}**")
            
            # Edit Jumlah Langsung
            new_qty = c_qty.number_input("Qty", min_value=1, value=qty, key=f"q_{item}", label_visibility="collapsed")
            if new_qty != qty:
                diff = new_qty - qty
                st.session_state.df_local.loc[df['Produk'] == item, 'Stok'] -= diff
                st.session_state.cart[item] = new_qty
                st.rerun()
            
            # Tombol Hapus (Kembalikan stok)
            if c_del.button("🗑️", key=f"del_{item}"):
                st.session_state.df_local.loc[df['Produk'] == item, 'Stok'] += qty
                del st.session_state.cart[item]
                st.rerun()

        st.divider()
        disc = st.number_input("Diskon (Rp)", min_value=0, step=500)
        total = subtotal - disc
        st.metric("Total Bayar", f"Rp {max(0, total):,.0f}")
        
        if st.button("🏁 SELESAIKAN TRANSAKSI", use_container_width=True) and st.session_state.cart:
            st.session_state.history.insert(0, {
                "Waktu": datetime.datetime.now().strftime("%H:%M:%S"),
                "Pelanggan": cust if cust else "Umum",
                "Item": str(st.session_state.cart),
                "Total": total
            })
            receipt = generate_receipt(st.session_state.cart, subtotal, disc, total, cust, st.session_state.user, df)
            st.download_button("📥 Download Struk", data=receipt, file_name="struk.pdf", mime="application/pdf")
            st.session_state.cart = {}
            st.success("Tersimpan!")
            st.balloons()

elif menu == "📊 Dashboard":
    st.title("📈 Dashboard")
    c1, c2 = st.columns(2)
    c1.metric("Total Produk", len(df))
    c2.metric("Nilai Aset", f"Rp {(df['Stok']*df['Harga Jual']).sum():,.0f}")
    st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventaris":
    st.title("📦 Database Inventaris")
    # Perbaikan error CR1135: Menggunakan .map() bukan .applymap()
    st.dataframe(df.style.map(lambda x: 'color: red' if x < 3 else '', subset=['Stok']), use_container_width=True)
