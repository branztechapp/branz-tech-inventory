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
    .stButton>button { border-radius: 10px !important; transition: 0.2s; font-weight: 600 !important; }
    .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
    [data-testid="stMetricValue"] { color: #60a5fa !important; }
    div[data-baseweb="input"] { border: 1px solid #3b82f6 !important; }
    .cart-row { background: rgba(255, 255, 255, 0.03); padding: 10px; border-radius: 8px; margin-bottom: 5px; }
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
if 'role' not in st.session_state: st.session_state.role = None
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'history' not in st.session_state: st.session_state.history = []
if 'df_local' not in st.session_state: st.session_state.df_local = load_data()
if 'receipt_bin' not in st.session_state: st.session_state.receipt_bin = None
if 'last_total' not in st.session_state: st.session_state.last_total = 0

# --- 4. LOGIC FUNCTIONS ---
def add_to_cart(p_name):
    df = st.session_state.df_local
    idx_list = df[df['Produk'] == p_name].index
    if not idx_list.empty:
        idx = idx_list[0]
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

def generate_receipt(cart_data, total_final, customer, cashier, df_ref):
    # Stabilized Font & Format
    pdf = FPDF(format=(80, 150)) 
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=5)
    
    # Header
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(60, 8, "BRANZ TECH", ln=True, align='C')
    pdf.set_font("Helvetica", size=8)
    pdf.cell(60, 4, f"Tgl  : {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True)
    pdf.cell(60, 4, f"Kasir: {cashier.upper()}", ln=True)
    pdf.cell(60, 4, f"Cust : {customer}", ln=True)
    pdf.cell(60, 4, "-"*35, ln=True)
    
    # Items
    total_items = 0
    for item, qty in cart_data.items():
        price = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
        subtotal = qty * price
        total_items += subtotal
        pdf.set_font("Helvetica", 'B', 8)
        pdf.multi_cell(60, 4, f"{item}")
        pdf.set_font("Helvetica", size=8)
        pdf.cell(60, 4, f"{qty} x {price:,.0f} = {subtotal:,.0f}", ln=True, align='R')
    
    # Footer
    pdf.cell(60, 4, "-"*35, ln=True)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(60, 8, f"TOTAL: Rp {total_final:,.0f}", ln=True, align='R')
    pdf.ln(5)
    pdf.set_font("Helvetica", 'I', 7)
    pdf.cell(60, 4, "Terima Kasih - BRANZ TECH", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- 5. LOGIN SYSTEM (AISYAH & ADMIN) ---
if not st.session_state.auth:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.title("💎 BRANZ LOGIN")
        u = st.text_input("Username (admin/staff)").lower()
        p = st.text_input("Password", type="password")
        if st.button("MASUK SISTEM", use_container_width=True, type="primary"):
            if u == "admin" and p == "branz123":
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, "admin"
                st.rerun()
            elif u == "staff" and p == "aisyah99":
                st.session_state.auth, st.session_state.user, st.session_state.role = True, "Aisyah", "staff"
                st.rerun()
            else:
                st.error("Login Gagal! Periksa Username/Password.")
    st.stop()

# --- 6. MAIN UI ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    st.caption(f"Status: {st.session_state.role.upper()}")
    
    options = ["🛒 Kasir POS", "📦 Cek Stok"]
    if st.session_state.role == "admin":
        options.append("📜 Log Transaksi")
    
    menu = st.radio("Menu Utama", options)
    st.divider()
    
    if st.button("🔄 Sinkron Data"):
        st.cache_data.clear()
        st.session_state.df_local = load_data()
        st.rerun()
    
    if st.button("🚪 Keluar Aplikasi"):
        st.session_state.auth = False
        st.session_state.cart = {}
        st.rerun()

# --- KASIR POS ---
if menu == "🛒 Kasir POS":
    st.title("🛒 TERMINAL KASIR")
    df = st.session_state.df_local

    col_scan, col_cust = st.columns([2, 1])
    with col_scan:
        # Placeholder for auto-focus
        barcode = st.text_input("⚡ SCAN BARCODE", key="barcode_input", help="Klik di sini sebelum scan").strip()
        if barcode:
            match = df[df['Barcode'] == barcode]
            if not match.empty:
                if add_to_cart(match.iloc[0]['Produk']):
                    st.toast(f"Ditambahkan: {match.iloc[0]['Produk']}")
                else: st.error("Stok Kosong!")
            else: st.warning("Barcode Tidak Terdaftar")
            # Clear input automatically via rerun
            st.session_state.barcode_input = "" 
            st.rerun()

    with col_cust:
        customer_name = st.text_input("Nama Pelanggan", "Umum")

    st.divider()

    c1, c2 = st.columns([1.3, 1])

    with c1:
        st.subheader("Pencarian Manual")
        search_q = st.selectbox("Cari Nama Produk", [""] + sorted(df['Produk'].tolist()))
        if search_q:
            if st.button(f"Tambah {search_q}", use_container_width=True):
                if add_to_cart(search_q): st.rerun()

    with c2:
        st.subheader("📋 Daftar Belanja")
        total_price = 0
        if not st.session_state.cart:
            st.info("Keranjang kosong. Silakan scan barang.")
        else:
            for item, qty in list(st.session_state.cart.items()):
                price = df[df['Produk'] == item]['Harga Jual'].values[0]
                total_price += (price * qty)
                
                with st.container():
                    col_info, col_btn = st.columns([2, 1])
                    col_info.write(f"**{item}**\n{qty} x {price:,.0f}")
                    with col_btn:
                        b1, b2, b3 = st.columns(3)
                        if b1.button("➕", key=f"p_{item}"): add_to_cart(item); st.rerun()
                        if b2.button("➖", key=f"m_{item}"): remove_from_cart(item); st.rerun()
                        if b3.button("🗑️", key=f"d_{item}"):
                            idx = df[df['Produk'] == item].index[0]
                            st.session_state.df_local.at[idx, 'Stok'] += qty
                            del st.session_state.cart[item]; st.rerun()

            st.divider()
            st.session_state.last_total = st.number_input("Total Akhir (Rp)", value=float(total_price), step=500.0)
            st.metric("TOTAL BAYAR", f"Rp {st.session_state.last_total:,.0f}")

            if st.button("🏁 SELESAI & CETAK STRUK", use_container_width=True, type="primary"):
                if st.session_state.cart:
                    # Generate PDF and store in bin
                    st.session_state.receipt_bin = generate_receipt(
                        st.session_state.cart, st.session_state.last_total, customer_name, st.session_state.user, df
                    )
                    # Log to History
                    st.session_state.history.insert(0, {
                        "Waktu": datetime.datetime.now().strftime("%H:%M:%S"),
                        "Pelanggan": customer_name,
                        "Total": st.session_state.last_total,
                        "Kasir": st.session_state.user
                    })
                    # Reset Cart but keep receipt_bin
                    st.session_state.cart = {}
                    st.success("Transaksi Berhasil Disimpan!")
                    st.rerun()
                else:
                    st.warning("Tambahkan barang dulu!")

            # Stable Receipt Download Button
            if st.session_state.receipt_bin:
                st.download_button(
                    label="📥 DOWNLOAD / PRINT STRUK",
                    data=st.session_state.receipt_bin,
                    file_name=f"Struk_BRANZ_{datetime.datetime.now().strftime('%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# --- CEK STOK ---
elif menu == "📦 Cek Stok":
    st.title("📦 Inventaris Produk")
    st.dataframe(st.session_state.df_local, use_container_width=True, hide_index=True)

# --- LOG (ADMIN) ---
elif menu == "📜 Log Transaksi":
    st.title("📜 Riwayat Penjualan")
    if st.session_state.history:
        st.table(pd.DataFrame(st.session_state.history))
    else:
        st.info("Belum ada transaksi.")
