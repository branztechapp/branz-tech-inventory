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
if 'role' not in st.session_state: st.session_state.role = None
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'history' not in st.session_state: st.session_state.history = []
if 'df_local' not in st.session_state: st.session_state.df_local = load_data()
if 'receipt_ready' not in st.session_state: st.session_state.receipt_ready = None

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

def generate_receipt_pdf(cart_data, total_akhir, customer_name, cashier_name, df_ref):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(60, 8, "BRANZ TECH", ln=True, align='C')
    pdf.set_font("Courier", size=8)
    pdf.cell(60, 4, f"Tgl  : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(60, 4, f"Kasir: {cashier_name.upper()}", ln=True)
    pdf.cell(60, 4, f"Cust : {customer_name}", ln=True)
    pdf.cell(60, 4, "-"*30, ln=True)
    
    for item, qty in cart_data.items():
        harga = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
        pdf.multi_cell(60, 4, f"{item}")
        pdf.cell(60, 4, f"   {qty} x {harga:,.0f} = {qty*harga:,.0f}", ln=True)
    
    pdf.cell(60, 4, "-"*30, ln=True)
    pdf.set_font("Courier", 'B', 10)
    pdf.cell(60, 8, f"TOTAL: Rp {total_akhir:,.0f}", ln=True, align='R')
    pdf.set_font("Courier", size=7)
    pdf.cell(60, 10, "Terima Kasih - BRANZ TECH", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 5. LOGIN SYSTEM (AISYAH & STAFF) ---
if not st.session_state.auth:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.title("💎 AISYAH LOGIN")
        u = st.text_input("Username").lower()
        p = st.text_input("Password", type="password")
        if st.button("MASUK SISTEM", use_container_width=True, type="primary"):
            if u == "admin" and p == "branz123":
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, "admin"
                st.rerun()
            elif u == "staff" and p == "aisyah99":
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, "staff"
                st.rerun()
            else: 
                st.error("Username atau Password Salah!")
    st.stop()

# --- 6. MAIN UI ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    st.caption(f"Role: {st.session_state.role.capitalize()}")
    
    # Menu Filter berdasarkan Role
    if st.session_state.role == "admin":
        menu_options = ["🛒 Kasir", "📦 Stok Barang", "📜 Log Transaksi"]
    else:
        menu_options = ["🛒 Kasir", "📦 Stok Barang"] # Staff tidak bisa lihat Log detail
        
    menu = st.radio("Navigasi", menu_options)
    st.divider()
    
    if st.button("🔄 Sync Cloud Data"):
        st.cache_data.clear()
        st.session_state.df_local = load_data()
        st.rerun()
        
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

# --- KASIR ---
if menu == "🛒 Kasir":
    st.title("🛒 POS TERMINAL")
    df = st.session_state.df_local

    barcode_val = st.text_input("⚡ SCAN BARCODE", key="scan_input").strip()
    if barcode_val:
        match = df[df['Barcode'] == barcode_val]
        if not match.empty:
            if add_to_cart(match.iloc[0]['Produk']):
                st.toast(f"✅ {match.iloc[0]['Produk']} Ditambahkan")
            else: st.error("Stok Habis!")
        else: st.warning("Barcode Tidak Dikenal")
        st.rerun()

    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        cust = st.text_input("Nama Pelanggan", "Umum")
        st.divider()
        options = [f"{r['Produk']} | Stok: {r['Stok']}" for _, r in df.iterrows()]
        pick = st.selectbox("Pilih Produk", [""] + options)
        if pick:
            p_sel = pick.split(" | ")[0]
            if st.button("➕ Tambah Ke Keranjang", use_container_width=True):
                if add_to_cart(p_sel): st.rerun()

    with c2:
        st.subheader("📝 Bill")
        subtotal = 0
        if not st.session_state.cart:
            st.info("Keranjang Kosong")
        else:
            for item, qty in list(st.session_state.cart.items()):
                harga = df[df['Produk'] == item]['Harga Jual'].values[0]
                subtotal += (harga * qty)
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

            total = st.number_input("Total Bayar", value=float(subtotal))
            
            if st.button("🏁 CETAK & SIMPAN", use_container_width=True, type="primary"):
                pdf_bytes = generate_receipt_pdf(st.session_state.cart, total, cust, st.session_state.user, df)
                st.session_state.receipt_ready = pdf_bytes
                
                st.session_state.history.insert(0, {
                    "Waktu": datetime.datetime.now().strftime("%H:%M:%S"),
                    "User": st.session_state.user,
                    "Pelanggan": cust,
                    "Total": total
                })
                st.session_state.cart = {}
                st.success("Tersimpan!")
                st.rerun()

            if st.session_state.receipt_ready:
                st.download_button(
                    label="📥 DOWNLOAD STRUK PDF",
                    data=st.session_state.receipt_ready,
                    file_name=f"Struk-BRANZ-{datetime.datetime.now().strftime('%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# --- STOK ---
elif menu == "📦 Stok Barang":
    st.title("📦 Inventaris Produk")
    st.dataframe(st.session_state.df_local, use_container_width=True, hide_index=True)

# --- LOG (ADMIN ONLY) ---
elif menu == "📜 Log Transaksi":
    st.title("📜 Riwayat Penjualan")
    if st.session_state.history:
        st.table(pd.DataFrame(st.session_state.history))
    else:
        st.info("Belum ada riwayat.")
