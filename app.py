import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import datetime

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

# Optimasi: CSS dipindah ke fungsi agar rapi
def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
        .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
        .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
        </style>
        """, unsafe_allow_html=True)

apply_custom_style()

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60) # Optimasi: Cache data selama 1 menit agar tidak terus-terusan hit API
def load_data():
    try:
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip() 
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        return df_clean
    except Exception:
        st.error("Koneksi Gagal: Cek URL Spreadsheet.")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual'])

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
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Access Denied")
    st.stop()

# --- 5. FUNGSI CETAK STRUK (REAL-TIME GENERATION) ---
def generate_receipt(cart_data, subtotal, discount, tax, total, customer, user, df_ref):
    # Diambil tepat saat fungsi dipanggil
    now_ts = datetime.datetime.now().strftime('%d/%m/%y %H:%M:%S')
    
    pdf = FPDF(format=(80, 150)) 
    pdf.add_page()
    pdf.set_margins(5, 5, 5)
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(70, 5, "BRANZ TECH PRESTIGE", ln=True, align='C')
    pdf.set_font("Courier", size=8)
    pdf.cell(70, 4, "Jombang, Jawa Timur", ln=True, align='C')
    pdf.cell(70, 4, "-"*35, ln=True, align='C')
    
    pdf.cell(70, 4, f"Tgl: {now_ts}", ln=True)
    pdf.cell(70, 4, f"Kasir: {user.upper()}", ln=True)
    pdf.cell(70, 4, f"Cust : {customer if customer else 'Umum'}", ln=True)
    pdf.cell(70, 4, "="*35, ln=True, align='C')
    
    for item, q in cart_data.items():
        price = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
        pdf.set_font("Courier", 'B', 8)
        pdf.cell(70, 4, f"{item[:25]}", ln=True)
        pdf.set_font("Courier", size=8)
        pdf.cell(35, 4, f"  {q} x {price:,.0f}", 0)
        pdf.cell(35, 4, f"{price*q:,.0f}", 0, 1, 'R')
    
    pdf.cell(70, 4, "-"*35, ln=True, align='C')
    pdf.cell(40, 5, "Subtotal", 0)
    pdf.cell(30, 5, f"{subtotal:,.0f}", 0, 1, 'R')
    if discount > 0:
        pdf.cell(40, 5, "Diskon", 0); pdf.cell(30, 5, f"-{discount:,.0f}", 0, 1, 'R')
    if tax > 0:
        pdf.cell(40, 5, "PPN 11%", 0); pdf.cell(30, 5, f"{tax:,.0f}", 0, 1, 'R')
        
    pdf.set_font("Courier", 'B', 10)
    pdf.cell(40, 7, "TOTAL", 0); pdf.cell(30, 7, f"Rp {total:,.0f}", 0, 1, 'R')
    pdf.set_font("Courier", 'B', 8)
    pdf.cell(70, 8, "*** TERIMA KASIH ***", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- 6. NAVIGATION ---
df = st.session_state.df_local

with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    # Menampilkan jam digital sederhana di sidebar yang update tiap interaksi
    st.write(f"🕒 {datetime.datetime.now().strftime('%H:%M:%S')}") 
    st.divider()
    menu = st.radio("Menu Navigasi", ["📊 Dashboard", "🛒 Kasir (POS)", "📦 Inventaris Stok", "📜 Riwayat Transaksi"])
    
    if st.button("🔄 Reload Data", use_container_width=True):
        st.cache_data.clear() # Membersihkan cache saat reload manual
        st.session_state.df_local = load_data()
        st.rerun()

# --- 7. PAGE LOGIC ---

if menu == "📊 Dashboard":
    st.title("📈 Business Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Produk", len(df))
    low_stock = len(df[df['Stok'] < 3])
    c2.metric("Stok Kritis (<3)", low_stock)
    c3.metric("Estimasi Aset", f"Rp {(df['Stok'] * df['Harga Jual']).sum():,.0f}")
    st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventaris Stok":
    st.title("📦 Database Inventaris")
    search = st.text_input("Cari Produk...")
    def color_stock(val):
        return 'color: #ff4b4b' if val < 3 else 'color: white'
    display_df = df[df['Produk'].str.contains(search, case=False)] if search else df
    st.dataframe(display_df.style.map(color_stock, subset=['Stok']), use_container_width=True)

elif menu == "📜 Riwayat Transaksi":
    st.title("📜 Log Transaksi Harian")
    if not st.session_state.history:
        st.info("Belum ada transaksi.")
    else:
        # Optimasi: Menggunakan DataFrame agar tampilan log lebih rapi
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)

elif menu == "🛒 Kasir (POS)":
    st.title("🛒 POS Terminal")
    col_pos, col_cart = st.columns([1.4, 1])

    with col_pos:
        st.subheader("👤 Data Pelanggan")
        cust_name = st.text_input("Nama Pelanggan / WA")
        st.divider()
        st.subheader("🛍️ Pilih Produk")
        options = [f"{r['Produk']} | Stok: {int(r['Stok'])}" for _, r in df.iterrows()]
        pick = st.selectbox("Cari Barang", [""] + options)
        
        if pick:
            name = pick.split(" | ")[0]
            current_s = df[df['Produk'] == name]['Stok'].values[0]
            q_input = st.number_input("Jumlah", min_value=1, max_value=int(current_s) if current_s > 0 else 1)
            
            if st.button("➕ Tambah Ke Keranjang", use_container_width=True):
                st.session_state.cart[name] = st.session_state.cart.get(name, 0) + q_input
                st.session_state.df_local.loc[df['Produk'] == name, 'Stok'] -= q_input
                st.rerun()

    with col_cart:
        st.subheader("📝 Keranjang")
        subtotal = 0
        if not st.session_state.cart:
            st.write("Kosong")
        else:
            for item, q in list(st.session_state.cart.items()):
                prc = df[df['Produk'] == item]['Harga Jual'].values[0]
                subtotal += (prc * q)
                c_info, c_del = st.columns([4, 1])
                c_info.write(f"**{item}** ({q}x)")
                if c_del.button("🗑️", key=f"del_{item}"):
                    st.session_state.df_local.loc[df['Produk'] == item, 'Stok'] += q
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            col_d, col_t = st.columns(2)
            disc = col_d.number_input("Diskon (Rp)", min_value=0, step=500)
            tax_rate = col_t.selectbox("Pajak", [0, 0.11], format_func=lambda x: "PPN 11%" if x > 0 else "0%")
            
            tax_val = (subtotal - disc) * tax_rate
            total_akhir = subtotal - disc + tax_val
            
            st.write(f"Subtotal: Rp {subtotal:,.0f}")
            st.write(f"### Total: Rp {total_akhir:,.0f}")
            
            if st.button("🏁 SELESAIKAN TRANSAKSI", use_container_width=True):
                # CAPTURE WAKTU REAL-TIME DETIK INI
                exact_time = datetime.datetime.now()
                time_str = exact_time.strftime("%H:%M:%S")
                
                # Masukkan ke history
                st.session_state.history.insert(0, { # Insert di index 0 supaya transaksi terbaru di paling atas
                    "Waktu": time_str,
                    "Pelanggan": cust_name if cust_name else "Umum",
                    "Item": ", ".join([f"{k} ({v})" for k, v in st.session_state.cart.items()]),
                    "Total": f"Rp {total_akhir:,.0f}"
                })
                
                # Buat Struk
                pdf_output = generate_receipt(st.session_state.cart, subtotal, disc, tax_val, total_akhir, cust_name, st.session_state.user, df)
                
                st.download_button(
                    label="📥 Download Struk (PDF)",
                    data=pdf_output,
                    file_name=f"Struk_{exact_time.strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                st.session_state.cart = {}
                st.success(f"Berhasil disimpan pukul {time_str}")
                st.balloons()
