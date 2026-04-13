import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import datetime
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH POS", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .main-card { background: #1e293b; padding: 20px; border-radius: 15px; border: 1px solid #334155; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    div[data-baseweb="input"] { background-color: #1e293b !important; border: 1px solid #3b82f6 !important; }
    [data-testid="stMetricValue"] { color: #60a5fa !important; font-size: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        df = data.copy()
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=['Produk'])
        
        # Penanganan tipe data yang stabil untuk mencegah error .str
        df['Barcode'] = df['Barcode'].astype(str).str.split('.').str[0].str.strip()
        df['Stok'] = pd.to_numeric(df['Stok'], errors='coerce').fillna(0).astype(int)
        df['Harga Jual'] = pd.to_numeric(df['Harga Jual'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual', 'Barcode'])

# --- 3. SESSION INITIALIZATION ---
states = {
    'auth': False, 'user': None, 'role': None, 
    'cart': {}, 'history': [], 'df_local': None, 
    'receipt_bin': None, 'last_total': 0
}
for key, val in states.items():
    if key not in st.session_state: st.session_state[key] = val

if st.session_state.df_local is None:
    st.session_state.df_local = load_data()

# --- 4. CORE LOGIC ---
def process_cart(p_name, action="add"):
    df = st.session_state.df_local
    idx = df[df['Produk'] == p_name].index[0]
    
    if action == "add":
        if df.at[idx, 'Stok'] > 0:
            st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1
            st.session_state.df_local.at[idx, 'Stok'] -= 1
            return True
    elif action == "remove":
        if p_name in st.session_state.cart:
            st.session_state.df_local.at[idx, 'Stok'] += 1
            if st.session_state.cart[p_name] > 1:
                st.session_state.cart[p_name] -= 1
            else:
                del st.session_state.cart[p_name]
    return False

def make_pdf(cart_data, total, cust, cashier, df_ref):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(60, 10, "BRANZ TECH", ln=True, align='C')
    pdf.set_font("Helvetica", size=9)
    pdf.cell(60, 5, f"Tgl: {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True)
    pdf.cell(60, 5, f"Kasir: {cashier}", ln=True)
    pdf.cell(60, 5, f"Cust: {cust}", ln=True)
    pdf.cell(60, 2, "-"*40, ln=True)
    
    for item, qty in cart_data.items():
        price = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
        pdf.multi_cell(60, 5, f"{item}")
        pdf.cell(60, 5, f"{qty} x {price:,.0f} = {qty*price:,.0f}", ln=True, align='R')
    
    pdf.cell(60, 2, "-"*40, ln=True)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(60, 10, f"TOTAL: Rp {total:,.0f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- 5. SIMPLE LOGIN ---
if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        st.title("💎 POS LOGIN")
        u = st.text_input("Username").lower()
        p = st.text_input("Password", type="password")
        if st.button("MASUK SISTEM"):
            if u == "admin" and p == "branz123":
                st.session_state.auth, st.session_state.user, st.session_state.role = True, "Admin", "admin"
                st.rerun()
            elif u == "staff" and p == "aisyah99":
                st.session_state.auth, st.session_state.user, st.session_state.role = True, "Aisyah", "staff"
                st.rerun()
            else: st.error("Login Gagal")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 6. UI LAYOUT ---
with st.sidebar:
    st.title("BRANZ TECH")
    st.info(f"User: {st.session_state.user} ({st.session_state.role})")
    menu = st.radio("Menu", ["🛒 Kasir POS", "📦 Inventaris", "📜 Riwayat"])
    st.divider()
    if st.button("🔄 Sync Cloud"):
        st.cache_data.clear()
        st.session_state.df_local = load_data()
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

# --- POS MODULE ---
if menu == "🛒 Kasir POS":
    df = st.session_state.df_local
    
    # Scanner & Header
    c_scan, c_name = st.columns([3, 1])
    with c_scan:
        barcode_in = st.text_input("⚡ SCAN BARCODE", key="bc_input", placeholder="Arahkan scanner ke sini...").strip()
        if barcode_in:
            match = df[df['Barcode'] == barcode_in]
            if not match.empty:
                if process_cart(match.iloc[0]['Produk']): st.toast("Produk Berhasil Ditambah")
                else: st.error("Stok Habis")
            else: st.warning("Barcode Tidak Ditemukan")
            st.session_state.bc_input = "" 
            st.rerun()
            
    with c_name:
        cust_name = st.text_input("Pelanggan", "Umum")

    st.divider()
    
    # Manual & Cart Split
    left, right = st.columns([1, 1.2])
    
    with left:
        st.subheader("Pencarian Manual")
        p_select = st.selectbox("Pilih Produk", [""] + sorted(df['Produk'].tolist()))
        if p_select and st.button(f"Tambah {p_select}"):
            if process_cart(p_select): st.rerun()

    with right:
        st.subheader("🛒 Keranjang Belanja")
        if not st.session_state.cart:
            st.info("Belum ada barang.")
        else:
            total_raw = 0
            for itm, q in list(st.session_state.cart.items()):
                prc = df[df['Produk'] == itm]['Harga Jual'].values[0]
                total_raw += (prc * q)
                with st.expander(f"{itm} (x{q})", expanded=True):
                    sc1, sc2 = st.columns([2, 1])
                    sc1.write(f"Rp {prc*q:,.0f}")
                    if sc2.button("Hapus", key=f"del_{itm}"):
                        process_cart(itm, "remove")
                        st.rerun()
            
            st.divider()
            disc = st.number_input("Diskon (Rp)", value=0, step=1000)
            final_total = max(0, total_raw - disc)
            st.metric("TOTAL AKHIR", f"Rp {final_total:,.0f}")
            
            if st.button("🏁 SELESAI & CETAK", type="primary"):
                st.session_state.receipt_bin = make_pdf(st.session_state.cart, final_total, cust_name, st.session_state.user, df)
                st.session_state.history.append({"Waktu": datetime.datetime.now().strftime("%H:%M"), "Cust": cust_name, "Total": final_total})
                st.session_state.cart = {}
                st.success("Transaksi Sukses!")
                st.rerun()

        if st.session_state.receipt_bin:
            st.download_button("📥 DOWNLOAD STRUK TERAKHIR", st.session_state.receipt_bin, 
                             file_name=f"Struk_{datetime.datetime.now().strftime('%H%M%S')}.pdf", mime="application/pdf")

# --- INVENTORY MODULE ---
elif menu == "📦 Inventaris":
    st.title("📦 Data Stok Barang")
    st.dataframe(st.session_state.df_local, use_container_width=True, hide_index=True)

# --- HISTORY MODULE ---
elif menu == "📜 Riwayat":
    st.title("📜 Riwayat Penjualan")
    if st.session_state.history:
        st.table(st.session_state.history)
    else:
        st.info("Belum ada data hari ini.")
