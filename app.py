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
    .stButton>button { border-radius: 10px !important; transition: 0.3s; }
    .stButton>button:hover { border: 1px solid #0ea5e9; color: #0ea5e9; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (OPTIMIZED) ---
URL_SHEET = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

# Inisialisasi koneksi global agar lebih cepat
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Mengambil data stok terbaru tanpa cache agar real-time."""
    try:
        # Menggunakan ttl=0 sangat penting untuk POS agar stok tidak 'delay'
        data = conn.read(spreadsheet=URL_SHEET, ttl=0)
        return data.dropna(subset=['Produk'])
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return pd.DataFrame()

def update_gsheets_stock(cart_items):
    """Mengupdate stok ke Google Sheets menggunakan Service Account."""
    try:
        # Ambil data paling baru tepat sebelum update untuk menghindari tabrakan data
        df_latest = conn.read(spreadsheet=URL_SHEET, ttl=0)
        updated_df = df_latest.copy()
        
        for item, qty in cart_items.items():
            idx = updated_df[updated_df['Produk'] == item].index
            if not idx.empty:
                current_stock = updated_df.loc[idx, 'Stok'].values[0]
                # Update stok secara matematis
                updated_df.loc[idx, 'Stok'] = current_stock - qty
        
        # PENTING: Operasi update memerlukan JSON Service Account di Secrets!
        conn.update(spreadsheet=URL_SHEET, data=updated_df)
        return True
    except Exception as e:
        st.error(f"Gagal Update: Gunakan Service Account untuk akses tulis! \n r: {e}")
        return False

# --- 3. RECEIPT GENERATOR ---
def generate_receipt(cart_items, total, operator, df_data):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 8, "BRANZ TECH", ln=True, align="C")
    pdf.set_font("Courier", "", 8)
    pdf.cell(0, 4, "Premium Inventory System", ln=True, align="C")
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
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTH & SESSION INITIALIZATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'user' not in st.session_state: st.session_state.user = ""
if 'role' not in st.session_state: st.session_state.role = "GUEST" 
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'last_receipt' not in st.session_state: st.session_state.last_receipt = None

if not st.session_state.auth:
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>💎 BRANZ TECH PRESTIGE</h2>", unsafe_allow_html=True)
        u = st.text_input("Username").lower().strip()
        p = st.text_input("Password", type="password")
        if st.button("AUTHENTICATE", use_container_width=True):
            users = {"admin": ["branz123", "ADMIN"], "aisyah": ["aisyah99", "STAFF"]}
            if u in users and users[u][0] == p:
                st.session_state.auth = True
                st.session_state.user = u
                st.session_state.role = users[u][1]
                st.rerun()
            else:
                st.error("Access Denied")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. DATA LOADING ---
df = load_data()

# --- 6. MAIN NAVIGATION ---
with st.sidebar:
    st.markdown(f"### 🛡️ {st.session_state.role}")
    st.write(f"Active: **{st.session_state.user.upper()}**")
    st.divider()
    menu = st.radio("Menu", ["📊 Dashboard", "📦 Stok", "📷 Scan", "🛒 Kasir (POS)"])
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 7. PAGE LOGIC ---
if menu == "📊 Dashboard":
    st.title("📈 Ringkasan Bisnis")
    if not df.empty:
        c1, c2 = st.columns(2)
        total_value = (df['Stok'] * df['Harga Jual']).sum()
        c1.metric("Omzet Potensial", f"Rp {total_value:,.0f}")
        c2.metric("Total Produk", len(df))
        st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Stok":
    st.title("📦 Inventaris Produk")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif menu == "🛒 Kasir (POS)":
    st.title("🛒 POS Terminal")
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
        if not df.empty:
            choices = [""] + sorted(df['Produk'].tolist())
            pick = st.selectbox("Pilih Produk", choices)
            amount = st.number_input("Qty", min_value=1, value=1)
            if st.button("➕ TAMBAH KE KERANJANG", use_container_width=True):
                if pick:
                    st.session_state.cart[pick] = st.session_state.cart.get(pick, 0) + amount
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.subheader("📝 Detail Pesanan")
        if not st.session_state.cart:
            st.info("Keranjang kosong.")
        else:
            total = 0
            for prod, q in list(st.session_state.cart.items()):
                # Gunakan data dari df yang sudah di-load
                price = df[df['Produk'] == prod]['Harga Jual'].values[0]
                sub = price * q
                total += sub
                col_a, col_b = st.columns([4, 1])
                col_a.write(f"**{prod}** \n{q} x Rp {price:,.0f} = Rp {sub:,.0f}")
                if col_b.button("🗑️", key=f"del_{prod}"):
                    del st.session_state.cart[prod]
                    st.rerun()
            
            st.divider()
            st.write(f"### TOTAL: Rp {total:,.0f}")
            
            if st.button("💎 SELESAIKAN & CETAK STRUK", use_container_width=True):
                with st.spinner("Mengirim data ke cloud..."):
                    # Update stok menggunakan fungsi yang sudah dioptimasi
                    if update_gsheets_stock(st.session_state.cart):
                        receipt = generate_receipt(st.session_state.cart, total, st.session_state.user, df)
                        st.session_state.last_receipt = receipt
                        st.session_state.cart = {}
                        st.success("Transaksi Berhasil!")
                        st.rerun()

        if st.session_state.last_receipt:
            st.download_button("📥 DOWNLOAD STRUK TERAKHIR", st.session_state.last_receipt, 
                             file_name=f"Struk_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf", 
                             mime="application/pdf", use_container_width=True)

elif menu == "📷 Scan":
    st.title("📷 Barcode Scanner")
    img_file = st.camera_input("Scan Barcode")
    if img_file:
        decoded_objs = decode(Image.open(img_file))
        if decoded_objs:
            b_code = decoded_objs[0].data.decode('utf-8')
            st.success(f"Terdeteksi: {b_code}")
            match = df[df['Barcode'].astype(str) == b_code]
            if not match.empty:
                name = match['Produk'].values[0]
                st.write(f"Produk ditemukan: **{name}**")
                if st.button("Tambah ke Keranjang"):
                    st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1
                    st.rerun()
        else:
            st.warning("Barcode tidak terbaca.")
