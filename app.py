import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
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

# --- 2. DATA ENGINE (READ ONLY) ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Membaca data awal dari Google Sheets
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip() 
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        return df_clean
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual'])

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

# --- 5. FUNGSI CETAK PDF ---
def generate_receipt(cart_data, total_price, user, df_ref):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "BRANZ TECH PRESTIGE", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, f"Tanggal: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.cell(190, 5, f"Kasir: {user.upper()}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(90, 10, "Produk", 1)
    pdf.cell(30, 10, "Qty", 1)
    pdf.cell(35, 10, "Harga", 1)
    pdf.cell(35, 10, "Subtotal", 1, ln=True)
    
    pdf.set_font("Arial", size=12)
    for item, q in cart_data.items():
        price = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
        sub = price * q
        pdf.cell(90, 10, str(item), 1)
        pdf.cell(30, 10, str(q), 1)
        pdf.cell(35, 10, f"{price:,.0f}", 1)
        pdf.cell(35, 10, f"{sub:,.0f}", 1, ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, f"TOTAL: Rp {total_price:,.0f}", ln=True, align='R')
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(190, 10, "Terima kasih telah berbelanja!", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 6. NAVIGATION ---
df = st.session_state.df_local

with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    st.divider()
    menu = st.radio("Menu Navigasi", ["📊 Dashboard", "🛒 Kasir (POS)", "📦 Inventaris Stok"])
    st.divider()
    if st.button("🔄 Reset & Reload Cloud Data"):
        st.session_state.df_local = load_data()
        st.session_state.cart = {}
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# --- 7. PAGE LOGIC ---

if menu == "📊 Dashboard":
    st.title("📈 Business Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Produk", len(df))
    c2.metric("Stok Rendah (<5)", len(df[df['Stok'] < 5]))
    c3.metric("Estimasi Nilai Barang", f"Rp {(df['Stok'] * df['Harga Jual']).sum():,.0f}")
    st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventaris Stok":
    st.title("📦 Database Inventaris")
    st.info("Data ini adalah stok real-time di aplikasi (setelah dipotong transaksi).")
    search = st.text_input("Cari Produk...")
    if search:
        st.dataframe(df[df['Produk'].str.contains(search, case=False)], use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif menu == "🛒 Kasir (POS)":
    st.title("🛒 POS Terminal")
    
    # Fitur Scanner Barcode
    with st.expander("📸 Scan Barcode"):
        cam_input = st.camera_input("Arahkan Barcode ke Kamera")
        if cam_input:
            decoded = decode(Image.open(cam_input))
            for d in decoded:
                b_code = d.data.decode("utf-8")
                st.success(f"Barcode Terdeteksi: {b_code}")
                # Jika ingin otomatis masuk keranjang berdasarkan ID produk, logika ditambahkan di sini

    col_pos, col_cart = st.columns([1.5, 1])

    with col_pos:
        st.subheader("Pilih Produk")
        # Format: "Nama Produk | Stok: 10"
        options = [f"{r['Produk']} | Stok: {int(r['Stok'])}" for _, r in df.iterrows()]
        pick = st.selectbox("Cari/Pilih Barang", [""] + options)
        
        if pick:
            name = pick.split(" | ")[0]
            current_s = df[df['Produk'] == name]['Stok'].values[0]
            
            q_input = st.number_input("Jumlah Beli", min_value=1, max_value=int(current_s) if current_s > 0 else 1, value=1)
            
            if st.button("➕ Tambahkan ke Keranjang", use_container_width=True):
                if current_s >= q_input:
                    # Tambah ke keranjang
                    st.session_state.cart[name] = st.session_state.cart.get(name, 0) + q_input
                    # Potong stok lokal (Inventaris)
                    st.session_state.df_local.loc[df['Produk'] == name, 'Stok'] -= q_input
                    st.success(f"{name} berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error("Stok Habis!")

    with col_cart:
        st.subheader("📝 Detail Pesanan")
        total = 0
        if not st.session_state.cart:
            st.write("Keranjang kosong.")
        else:
            for item, q in list(st.session_state.cart.items()):
                prc = df[df['Produk'] == item]['Harga Jual'].values[0]
                subtotal = prc * q
                total += subtotal
                
                c_info, c_del = st.columns([4, 1])
                c_info.write(f"**{item}** \n{q} x Rp {prc:,.0f} = Rp {subtotal:,.0f}")
                if c_del.button("🗑️", key=f"del_{item}"):
                    # Kembalikan stok jika batal
                    st.session_state.df_local.loc[df['Produk'] == item, 'Stok'] += q
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            st.write(f"## Total: Rp {total:,.0f}")
            
            # Tombol Selesaikan Transaksi
            if st.button("🏁 SELESAIKAN & CETAK STRUK", use_container_width=True):
                # Buat PDF
                receipt_pdf = generate_receipt(st.session_state.cart, total, st.session_state.user, df)
                
                # Sediakan tombol download
                st.download_button(
                    label="📥 Ambil Struk (PDF)",
                    data=receipt_pdf,
                    file_name=f"BRANZ_{datetime.datetime.now().strftime('%H%M%S')}.pdf",
                    mime="application/pdf"
                )
                
                # Reset keranjang setelah transaksi dianggap "Selesai" (stok sudah terpotong otomatis tadi)
                st.session_state.cart = {}
                st.balloons()
