import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import datetime
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
        .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
        .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
        div[data-baseweb="input"] { border: 1px solid #3b82f6 !important; }
        /* Styling untuk dataframes */
        [data-testid="stMetricValue"] { font-size: 1.8rem; color: #3b82f6; }
        </style>
        """, unsafe_allow_html=True)

apply_custom_style()

# --- 2. DATA ENGINE (Optimasi Koneksi) ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip() 
        # Filter hanya baris yang punya nama Produk
        df_clean = data.dropna(subset=['Produk']).copy()
        
        # Konversi Tipe Data dengan Aman
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0).astype(int)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        
        # Penanganan Barcode (Sering jadi penyebab error CR1137)
        if 'Barcode' not in df_clean.columns:
            df_clean['Barcode'] = ""
        
        # Memastikan semua barcode adalah string dan bersih dari spasi/.0
        df_clean['Barcode'] = (df_clean['Barcode'].astype(str)
                               .str.replace('.0', '', regex=False)
                               .str.strip()
                               .replace(['nan', 'None'], ''))
        
        return df_clean
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual', 'Barcode'])

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'history' not in st.session_state: st.session_state.history = []
# Menggunakan df_local agar stok berkurang secara realtime di UI sebelum disync ke database
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
def generate_receipt(cart_data, total, customer, user, df_ref):
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

# --- 6. NAVIGATION ---
df = st.session_state.df_local

with st.sidebar:
    st.title("💎 BRANZ TECH")
    st.write(f"Kasir: **{st.session_state.user.upper()}**")
    st.divider()
    menu = st.radio("Navigasi", ["📊 Dashboard", "🛒 Kasir (POS)", "📦 Inventaris", "📜 Riwayat Transaksi"])
    
    st.divider()
    if st.button("🔄 Sinkron Database"):
        st.cache_data.clear()
        st.session_state.df_local = load_data()
        st.success("Data terbaru dimuat!")
        st.rerun()

# --- 7. LOGIC PER HALAMAN ---

if menu == "🛒 Kasir (POS)":
    st.title("🛒 POS Terminal")
    
    # Input Scan Barcode - Perbaikan Error Filter
    bc_pos = st.text_input("⚡ SCAN BARCODE", key="scan_main").strip()
    
    if bc_pos:
        # Perbaikan pencarian: pastikan mencari di kolom Barcode yang sudah distring-kan
        match = df[df['Barcode'] == bc_pos]
        if not match.empty:
            p_name = match.iloc[0]['Produk']
            current_stok = st.session_state.df_local.loc[st.session_state.df_local['Barcode'] == bc_pos, 'Stok'].values[0]
            
            if current_stok > 0:
                st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1
                st.session_state.df_local.loc[st.session_state.df_local['Barcode'] == bc_pos, 'Stok'] -= 1
                st.toast(f"Ditambahkan: {p_name}")
            else:
                st.error("Stok Habis!")
        else:
            st.warning("Produk tidak ditemukan!")

    col_l, col_r = st.columns([1.5, 1])
    
    with col_l:
        cust = st.text_input("Nama Pelanggan / WA", placeholder="08...")
        st.divider()
        # Pencarian Manual (Aman dari error string)
        options = [f"{r['Produk']} | Stok: {r['Stok']}" for _, r in df.iterrows()]
        pick = st.selectbox("Cari Produk Manual", [""] + options)
        
        if pick:
            name = pick.split(" | ")[0]
            q_add = st.number_input("Jumlah", min_value=1, value=1)
            if st.button("➕ Tambah Manual"):
                st.session_state.cart[name] = st.session_state.cart.get(name, 0) + q_add
                st.session_state.df_local.loc[st.session_state.df_local['Produk'] == name, 'Stok'] -= q_add
                st.rerun()

    with col_r:
        st.subheader("📝 Keranjang")
        subtotal = 0
        if not st.session_state.cart:
            st.info("Keranjang Kosong")
        
        for item, qty in list(st.session_state.cart.items()):
            item_data = df[df['Produk'] == item]
            if not item_data.empty:
                price = item_data['Harga Jual'].values[0]
                subtotal += (price * qty)
                
                c_name, c_qty, c_del = st.columns([2, 1.5, 0.5])
                c_name.write(f"**{item}**")
                
                # Edit Jumlah Langsung
                new_qty = c_qty.number_input("Qty", min_value=1, value=qty, key=f"q_{item}", label_visibility="collapsed")
                if new_qty != qty:
                    diff = new_qty - qty
                    st.session_state.df_local.loc[st.session_state.df_local['Produk'] == item, 'Stok'] -= diff
                    st.session_state.cart[item] = new_qty
                    st.rerun()
                
                if c_del.button("🗑️", key=f"del_{item}"):
                    st.session_state.df_local.loc[st.session_state.df_local['Produk'] == item, 'Stok'] += qty
                    del st.session_state.cart[item]
                    st.rerun()

        st.divider()
        disc = st.number_input("Diskon (Rp)", min_value=0, step=500)
        total = max(0, subtotal - disc)
        st.metric("Total Bayar", f"Rp {total:,.0f}")
        
        if st.button("🏁 SELESAIKAN TRANSAKSI", use_container_width=True) and st.session_state.cart:
            now = datetime.datetime.now()
            st.session_state.history.insert(0, {
                "Tanggal": now.strftime("%Y-%m-%d"),
                "Waktu": now.strftime("%H:%M:%S"),
                "Pelanggan": cust if cust else "Umum",
                "Item": str(st.session_state.cart),
                "Total": total
            })
            # Buat Receipt PDF
            receipt = generate_receipt(st.session_state.cart, total, cust, st.session_state.user, df)
            if receipt:
                st.download_button("📥 Download Struk", data=receipt, file_name=f"Struk_{now.strftime('%H%M%S')}.pdf", mime="application/pdf")
            
            st.session_state.cart = {}
            st.success("Transaksi Berhasil Disimpan!")
            st.balloons()

elif menu == "📊 Dashboard":
    st.title("📈 Dashboard")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Produk", len(df))
    c2.metric("Nilai Aset", f"Rp {(df['Stok']*df['Harga Jual']).sum():,.0f}")
    c3.metric("Transaksi Hari Ini", len(st.session_state.history))
    
    st.subheader("Stok Produk Saat Ini")
    st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventaris":
    st.title("📦 Database Inventaris")
    
    # Perbaikan Error CR1135: Menggunakan .map() bukan .applymap()
    # Menampilkan stok rendah dengan warna merah
    styled_df = df.style.map(lambda x: 'color: #ff4b4b; font-weight: bold' if x < 5 else '', subset=['Stok'])
    st.dataframe(styled_df, use_container_width=True)

elif menu == "📜 Riwayat Transaksi":
    st.title("📜 Log Transaksi Harian")
    if not st.session_state.history:
        st.info("Belum ada transaksi hari ini.")
    else:
        log_df = pd.DataFrame(st.session_state.history)
        st.dataframe(log_df, use_container_width=True)
        
        # FITUR EKSPOR EXCEL
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            log_df.to_excel(writer, index=False, sheet_name='Laporan_Harian')
        
        st.download_button(
            label="📥 Simpan Laporan ke Excel",
            data=buffer.getvalue(),
            file_name=f"Laporan_BranzTech_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
