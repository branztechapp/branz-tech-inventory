import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
import datetime
import io

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
    .terminal-card { background: rgba(30, 41, 59, 0.4); border-radius: 20px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.05); }
    .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
    .stButton>button:hover { border: 1px solid #0ea5e9; color: #0ea5e9; box-shadow: 0 0 15px rgba(14, 165, 233, 0.3); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
URL_SHEET = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Mengambil data stok terbaru (TTL=0 agar selalu fresh)."""
    try:
        data = conn.read(spreadsheet=URL_SHEET, ttl=0)
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0)
        return df_clean
    except Exception as e:
        st.error(f"Gagal Load Data: {e}")
        return pd.DataFrame()

def process_transaction(cart_items):
    """Fungsi Inti: Update stok di Google Sheets."""
    try:
        # 1. Ambil data terbaru dari Cloud
        df_latest = conn.read(spreadsheet=URL_SHEET, ttl=0)
        
        # 2. Kurangi stok di memori
        for item, qty_beli in cart_items.items():
            idx = df_latest[df_latest['Produk'] == item].index
            if not idx.empty:
                stok_lama = df_latest.loc[idx, 'Stok'].values[0]
                df_latest.loc[idx, 'Stok'] = stok_lama - qty_beli
        
        # 3. Kirim balik ke Google Sheets (WAJIB SERVICE ACCOUNT)
        conn.update(spreadsheet=URL_SHEET, data=df_latest)
        return True
    except Exception as e:
        st.error(f"Update Gagal: Pastikan Service Account di Secrets sudah BENAR. \n Detail: {e}")
        return False

# --- 3. RECEIPT GENERATOR ---
def generate_receipt(cart_items, total, operator, df_data):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 8, "BRANZ TECH", ln=True, align="C")
    pdf.set_font("Courier", "", 8)
    pdf.cell(0, 4, "="*25, ln=True, align="C")
    pdf.cell(0, 5, f"Tgl: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 5, f"Staff: {operator.upper()}", ln=True)
    pdf.cell(0, 5, "-"*31, ln=True)
    for item, qty in cart_items.items():
        price = df_data[df_data['Produk'] == item]['Harga Jual'].values[0]
        pdf.cell(0, 5, f"{item[:25]}", ln=True)
        pdf.cell(0, 5, f"  {qty} x {price:,.0f} = {qty*price:,.0f}", ln=True)
    pdf.cell(0, 5, "-"*31, ln=True)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(0, 10, f"TOTAL: Rp {total:,.0f}", ln=True, align="R")
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTH & SESSION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'last_receipt' not in st.session_state: st.session_state.last_receipt = None

if not st.session_state.auth:
    st.title("💎 BRANZ TECH")
    u = st.text_input("User").lower()
    p = st.text_input("Pass", type="password")
    if st.button("LOGIN"):
        if u == "admin" and p == "branz123":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- 5. MAIN LOGIC ---
df = load_data() # Stok akan selalu refresh setiap kali halaman reload
menu = st.sidebar.radio("Navigasi", ["🛒 POS Kasir", "📦 Stok Inventaris"])

if menu == "🛒 POS Kasir":
    st.title("🛒 Terminal Penjualan")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
        # Menampilkan stok real-time di dropdown
        list_prod = [f"{r['Produk']} (Tersedia: {int(r['Stok'])})" for _, r in df.iterrows()]
        pick_raw = st.selectbox("Pilih Produk", [""] + list_prod)
        amount = st.number_input("Qty", min_value=1, value=1)
        if st.button("➕ TAMBAH"):
            if pick_raw:
                p_name = pick_raw.split(" (Tersedia:")[0]
                st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + amount
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.subheader("📝 Detail Belanja")
        total = 0
        for p, q in list(st.session_state.cart.items()):
            prc = df[df['Produk'] == p]['Harga Jual'].values[0]
            total += (prc * q)
            st.write(f"**{p}** x{q}")
        
        st.write(f"### TOTAL: Rp {total:,.0f}")
        
        # TOMBOL SAKTI: Update Cloud & Siapkan Struk
        if st.button("💎 PROSES & KURANGI STOK"):
            if st.session_state.cart:
                with st.spinner("Sinkronisasi stok ke Google Sheets..."):
                    if process_transaction(st.session_state.cart):
                        st.session_state.last_receipt = generate_receipt(st.session_state.cart, total, st.session_state.user, df)
                        st.session_state.cart = {}
                        st.success("Stok Cloud Berhasil Berkurang!")
                        st.rerun() # Ini akan memicu load_data() baru sehingga tampilan stok ikut berkurang

        if st.session_state.last_receipt:
            st.download_button("📥 CETAK STRUK", st.session_state.last_receipt, file_name="Struk.pdf")

elif menu == "📦 Stok Inventaris":
    st.title("📦 Stok Real-Time")
    st.dataframe(df[['Produk', 'Stok', 'Harga Jual']], use_container_width=True, hide_index=True)
