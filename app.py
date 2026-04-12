import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
import datetime
import io

# --- 1. CONFIG & ELITE STYLING ---
st.set_page_config(page_title="BRANZ TECH VIP", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
    .login-box {
        background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px);
        padding: 50px; border-radius: 35px; border: 1px solid rgba(255, 255, 255, 0.1);
        max-width: 450px; margin: auto;
    }
    .terminal-card {
        background: rgba(30, 41, 59, 0.4); border-radius: 25px;
        padding: 25px; border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .cart-box {
        background: linear-gradient(145deg, #0ea5e9, #2563eb);
        border-radius: 30px; padding: 30px; color: white;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }
    .stButton>button { border-radius: 12px !important; font-weight: bold !important; transition: 0.3s; }
    .stButton>button:hover { transform: scale(1.02); }
    [data-testid="stMetricValue"] { font-size: 24px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

@st.cache_data(ttl=5)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(spreadsheet=url, ttl=0).dropna(subset=['Produk'])
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

# --- 3. RECEIPT GENERATOR (STABLE VERSION) ---
def generate_receipt(cart_items, total, operator, df_data):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 8, "BRANZ TECH", ln=True, align="C")
    pdf.set_font("Courier", "", 8)
    pdf.cell(0, 4, "Premium Digital Solutions", ln=True, align="C")
    pdf.cell(0, 4, "="*25, ln=True, align="C")
    
    now_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 5, f"Tgl: {now_str}", ln=True)
    pdf.cell(0, 5, f"Kasir: {operator.upper()}", ln=True)
    pdf.cell(0, 5, "-"*31, ln=True)
    
    for item, qty in cart_items.items():
        price = df_data[df_data['Produk'] == item]['Harga Jual'].values[0]
        subtotal = qty * price
        pdf.set_font("Courier", "B", 8)
        pdf.cell(0, 5, f"{item[:25]}", ln=True)
        pdf.set_font("Courier", "", 8)
        pdf.cell(0, 5, f"  {qty} x {price:,.0f} = {subtotal:,.0f}", ln=True)
    
    pdf.cell(0, 5, "-"*31, ln=True)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(0, 10, f"TOTAL: Rp {total:,.0f}", ln=True, align="R")
    pdf.ln(5)
    pdf.set_font("Courier", "I", 7)
    pdf.cell(0, 5, "Barang yang sudah dibeli", ln=True, align="C")
    pdf.cell(0, 5, "tidak dapat ditukar/dikembalikan.", ln=True, align="C")
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTH & SESSION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'last_receipt' not in st.session_state: st.session_state.last_receipt = None

if not st.session_state.auth:
    _, center, _ = st.columns([1, 1.8, 1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>💎 BRANZ TECH</h2>", unsafe_allow_html=True)
        u = st.text_input("Access ID").lower().strip()
        p = st.text_input("Secret Key", type="password")
        if st.button("UNLOCK SYSTEM", use_container_width=True):
            users = {"admin": ["branz123", "ADMIN"], "aisyah": ["aisyah99", "ADMIN"]}
            if u in users and users[u][0] == p:
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, users[u][1]
                st.rerun()
            else:
                st.error("Credential Salah")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. MAIN APP ---
df = load_data()

with st.sidebar:
    st.markdown(f"### 🛡️ {st.session_state.role}")
    st.caption(f"Operator: {st.session_state.user.upper()}")
    st.divider()
    menu = st.radio("MENU", ["🛒 Kasir Digital", "📷 Scan Barcode", "📊 Dashboard", "📦 Inventory"])
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.auth = False
        st.session_state.cart = {}
        st.rerun()

if menu == "🛒 Kasir Digital":
    st.title("🛒 POS Terminal")
    col_in, col_cart = st.columns([1.4, 1])
    
    with col_in:
        st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
        if not df.empty:
            prod_list = sorted(df['Produk'].tolist())
            sel_prod = st.selectbox("Cari Produk", [""] + prod_list)
            qty = st.number_input("Jumlah", min_value=1, value=1)
            
            if st.button("➕ TAMBAH KE KERANJANG", use_container_width=True):
                if sel_prod:
                    st.session_state.cart[sel_prod] = st.session_state.cart.get(sel_prod, 0) + qty
                    st.toast(f"✅ {sel_prod} Berhasil ditambah!")
                    st.rerun()
                else:
                    st.warning("Pilih produk dulu!")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_cart:
        st.markdown('<div class="cart-box">', unsafe_allow_html=True)
        st.subheader("📝 Detail Pesanan")
        total_akhir = 0
        
        if not st.session_state.cart:
            st.info("Keranjang masih kosong.")
        else:
            for item, q in list(st.session_state.cart.items()):
                harga = df[df['Produk'] == item]['Harga Jual'].values[0]
                sub = harga * q
                total_akhir += sub
                
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{item}** \n{q} x Rp {harga:,.0f} = **Rp {sub:,.0f}**")
                if c2.button("🗑️", key=f"del_{item}"):
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            st.markdown(f"## TOTAL: Rp {total_akhir:,.0f}")
            
            if st.button("💎 SELESAIKAN & CETAK STRUK", use_container_width=True):
                receipt = generate_receipt(st.session_state.cart, total_akhir, st.session_state.user, df)
                st.session_state.last_receipt = receipt
                st.session_state.cart = {} # Bersihkan keranjang
                st.balloons()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Area khusus Download Struk agar tidak hilang
        if st.session_state.last_receipt:
            st.success("Transaksi sebelumnya berhasil dicetak!")
            st.download_button(
                label="📥 DOWNLOAD STRUK TERAKHIR (PDF)", 
                data=st.session_state.last_receipt, 
                file_name=f"Struk_BT_{datetime.datetime.now().strftime('%H%M%S')}.pdf", 
                mime="application/pdf", 
                use_container_width=True
            )
            if st.button("Mulai Transaksi Baru", use_container_width=True):
                st.session_state.last_receipt = None
                st.rerun()

elif menu == "📷 Scan Barcode":
    st.title("📷 Scanner Barcode")
    st.info("Arahkan barcode ke kamera laptop/HP Anda.")
    cam = st.camera_input("Scanner Aktif")
    if cam:
        img = Image.open(cam)
        decoded = decode(img)
        if decoded:
            code = decoded[0].data.decode('utf-8')
            st.success(f"Barcode Terdeteksi: {code}")
            if 'Barcode' in df.columns:
                match = df[df['Barcode'].astype(str) == code]
                if not match.empty:
                    p_name = match['Produk'].values[0]
                    st.markdown(f"### Produk: **{p_name}**")
                    if st.button(f"Tambah {p_name} ke Keranjang", use_container_width=True):
                        st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1
                        st.success("Masuk Keranjang!")
                else:
                    st.error("Produk tidak ditemukan di database.")
        else:
            st.warning("Barcode tidak terbaca, coba lebih dekat/fokus.")

elif menu == "📊 Dashboard":
    st.title("📊 Ringkasan Bisnis")
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        omzet = (df['Stok'] * df['Harga Jual']).sum()
        col1.metric("Omzet Potensial", f"Rp {omzet:,.0f}")
        col2.metric("Total Jenis Produk", len(df))
        col3.metric("Total Item Stok", int(df['Stok'].sum()))
        
        st.subheader("Stok per Produk")
        st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventory":
    st.title("📦 Kelola Stok")
    st.dataframe(df, use_container_width=True, hide_index=True)
