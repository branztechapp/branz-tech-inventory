import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
import datetime
import io

# --- 1. CONFIG & ELITE STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
    .login-box {
        background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px);
        padding: 40px; border-radius: 25px; border: 1px solid rgba(255, 255, 255, 0.1);
        max-width: 450px; margin: auto;
    }
    .terminal-card {
        background: rgba(30, 41, 59, 0.4); border-radius: 20px;
        padding: 20px; border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
    .stButton>button:hover { border: 1px solid #0ea5e9; color: #0ea5e9; box-shadow: 0 0 15px rgba(14, 165, 233, 0.3); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (Koneksi Baru: branz_tech_db) ---
URL_SHEET = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"
conn = st.connection("branz_tech_db", type=GSheetsConnection)

def load_data():
    """Mengambil data dan membersihkan nama kolom secara otomatis."""
    try:
        data = conn.read(spreadsheet=URL_SHEET, ttl=0)
        # --- PEMBERSIH KOLOM OTOMATIS ---
        data.columns = data.columns.str.strip() 
        
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0)
        return df_clean
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return pd.DataFrame()

def update_gsheets_stock(cart_items):
    """Mengurangi stok di Google Sheets dengan validasi kolom."""
    try:
        df_current = conn.read(spreadsheet=URL_SHEET, ttl=0)
        # --- PEMBERSIH KOLOM OTOMATIS ---
        df_current.columns = df_current.columns.str.strip()

        for item, qty_beli in cart_items.items():
            idx = df_current[df_current['Produk'] == item].index
            if not idx.empty:
                stok_sekarang = df_current.loc[idx, 'Stok'].values[0]
                if stok_sekarang < qty_beli:
                    st.error(f"Stok {item} tidak cukup! (Tersisa: {stok_sekarang})")
                    return False
                df_current.loc[idx, 'Stok'] = stok_sekarang - qty_beli
        
        # Kirim data ke Google Sheets menggunakan koneksi branz_tech_db
        conn.update(spreadsheet=URL_SHEET, data=df_current)
        return True
    except Exception as e:
        st.error(f"Gagal Update! Detail: {e}")
        return False

# --- 3. RECEIPT GENERATOR ---
def generate_receipt(cart_items, total, operator, df_data):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 8, "BRANZ TECH", ln=True, align="C")
    pdf.set_font("Courier", "", 8)
    pdf.cell(0, 4, "Inventory Automation System", ln=True, align="C")
    pdf.cell(0, 4, "="*25, ln=True, align="C")
    
    pdf.cell(0, 5, f"Tgl: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 5, f"Staff: {operator.upper()}", ln=True)
    pdf.cell(0, 5, "-"*31, ln=True)
    
    for item, qty in cart_items.items():
        price = df_data[df_data['Produk'] == item]['Harga Jual'].values[0]
        pdf.set_font("Courier", "B", 8)
        pdf.cell(0, 5, f"{item[:25]}", ln=True)
        pdf.set_font("Courier", "", 8)
        pdf.cell(0, 5, f"  {qty} x {price:,.0f} = {qty*price:,.0f}", ln=True)
    
    pdf.cell(0, 5, "-"*31, ln=True)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(0, 10, f"TOTAL: Rp {total:,.0f}", ln=True, align="R")
    pdf.cell(0, 5, "="*25, ln=True, align="C")
    pdf.set_font("Courier", "I", 8)
    pdf.cell(0, 5, "Terima Kasih", ln=True, align="C")
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTH & SESSION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'last_receipt' not in st.session_state: st.session_state.last_receipt = None

if not st.session_state.auth:
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>💎 BRANZ TECH</h2>", unsafe_allow_html=True)
        u = st.text_input("Username").lower().strip()
        p = st.text_input("Password", type="password")
        if st.button("AUTHENTICATE", use_container_width=True):
            users = {"admin": ["branz123", "ADMIN"], "aisyah": ["aisyah99", "STAFF"]}
            if u in users and users[u][0] == p:
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, users[u][1]
                st.rerun()
            else: st.error("Access Denied")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. DATA LOADING & NAV ---
df = load_data()

with st.sidebar:
    st.markdown(f"### 🛡️ {st.session_state.role}")
    st.write(f"User: **{st.session_state.user.upper()}**")
    st.divider()
    menu = st.radio("Navigasi", ["📊 Dashboard", "📦 Inventaris", "🛒 Kasir (POS)", "📷 Scan Barcode"])
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 6. PAGE LOGIC ---
if menu == "📊 Dashboard":
    st.title("📈 Analitik Bisnis")
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Valuasi Stok", f"Rp {(df['Stok'] * df['Harga Jual']).sum():,.0f}")
        c2.metric("Varian Produk", len(df))
        c3.metric("Stok Rendah (<5)", len(df[df['Stok'] < 5]))
        st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventaris":
    st.title("📦 Data Produk")
    search = st.text_input("Cari nama produk...")
    display_df = df[df['Produk'].str.contains(search, case=False)] if search else df
    st.dataframe(display_df, use_container_width=True, hide_index=True)

elif menu == "🛒 Kasir (POS)":
    st.title("🛒 POS Terminal")
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
        if not df.empty:
            product_list = [f"{row['Produk']} (Sisa: {int(row['Stok'])})" for _, row in df.iterrows()]
            pick_raw = st.selectbox("Pilih Produk", [""] + product_list)
            if pick_raw:
                pick_name = pick_raw.split(" (Sisa:")[0]
                stok_avail = df[df['Produk'] == pick_name]['Stok'].values[0]
                amount = st.number_input("Jumlah Beli", min_value=1, max_value=int(stok_avail), value=1)
                if st.button("➕ TAMBAH", use_container_width=True):
                    st.session_state.cart[pick_name] = st.session_state.cart.get(pick_name, 0) + amount
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.subheader("📝 Pesanan")
        if not st.session_state.cart:
            st.info("Keranjang kosong.")
        else:
            total = 0
            for prod, q in list(st.session_state.cart.items()):
                price = df[df['Produk'] == prod]['Harga Jual'].values[0]
                sub = price * q
                total += sub
                c_a, c_b = st.columns([4, 1])
                c_a.write(f"**{prod}** \n{q} x Rp {price:,.0f} = Rp {sub:,.0f}")
                if c_b.button("🗑️", key=f"del_{prod}"):
                    del st.session_state.cart[prod]
                    st.rerun()
            
            st.divider()
            st.write(f"### TOTAL: Rp {total:,.0f}")
            
            if st.button("💎 SELESAIKAN & CETAK STRUK", use_container_width=True):
                with st.spinner("Sinkronisasi Stok Cloud..."):
                    if update_gsheets_stock(st.session_state.cart):
                        receipt = generate_receipt(st.session_state.cart, total, st.session_state.user, df)
                        st.session_state.last_receipt = receipt
                        st.session_state.cart = {}
                        st.success("Transaksi Selesai!")
                        st.rerun()

        if st.session_state.last_receipt:
            st.download_button("📥 DOWNLOAD STRUK", st.session_state.last_receipt, 
                             file_name=f"STRUK_BRANZ.pdf", 
                             mime="application/pdf", use_container_width=True)

elif menu == "📷 Scan Barcode":
    st.title("📷 Scanner")
    img_file = st.camera_input("Arahkan barcode ke kamera")
    if img_file:
        decoded = decode(Image.open(img_file))
        if decoded:
            b_code = decoded[0].data.decode('utf-8')
            match = df[df['Barcode'].astype(str) == b_code]
            if not match.empty:
                name = match['Produk'].values[0]
                st.info(f"Terdeteksi: {name}")
                if st.button("Tambah 1 ke Keranjang"):
                    st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1
                    st.rerun()
            else: st.warning("Produk tidak terdaftar.")
