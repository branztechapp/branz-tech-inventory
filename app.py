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
        [data-testid="stMetricValue"] { color: #60a5fa !important; }
        div[data-baseweb="input"] { border: 1px solid #3b82f6 !important; }
        </style>
        """, unsafe_allow_html=True)

apply_custom_style()

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip()
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0).astype(int)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        
        if 'Barcode' in df_clean.columns:
            df_clean['Barcode'] = (df_clean['Barcode']
                                   .astype(str)
                                   .str.replace(r'\.0$', '', regex=True)
                                   .str.strip()
                                   .replace(['nan', 'None', ''], 'KOSONG'))
        else:
            df_clean['Barcode'] = 'KOSONG'
        return df_clean
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual', 'Barcode'])

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
                st.session_state.auth, st.session_state.user = True, u
                st.rerun()
            else: st.error("Akses Ditolak")
    st.stop()

# --- 5. RECEIPT GENERATOR ---
def generate_receipt(cart_data, total, customer, user, df_ref):
    try:
        pdf = FPDF(format=(80, 150))
        pdf.add_page()
        pdf.set_font("Courier", 'B', 12)
        pdf.cell(60, 8, "BRANZ TECH", ln=True, align='C')
        pdf.set_font("Courier", size=8)
        pdf.cell(60, 4, f"Kasir: {user.upper()}", ln=True)
        pdf.cell(60, 4, f"Cust : {customer if customer else 'Umum'}", ln=True)
        pdf.cell(60, 4, "-"*30, ln=True)
        for item, q in cart_data.items():
            price = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
            pdf.cell(60, 4, f"{item[:18]} x{q}", ln=True)
            pdf.cell(60, 4, f"   @ {price:,.0f} = {price*q:,.0f}", ln=True)
        pdf.cell(60, 4, "-"*30, ln=True)
        pdf.set_font("Courier", 'B', 10)
        pdf.cell(60, 8, f"TOTAL: Rp {total:,.0f}", ln=True, align='R')
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# --- 6. NAVIGATION ---
with st.sidebar:
    st.title("💎 BRANZ TECH")
    st.write(f"User: **{st.session_state.user.upper()}**")
    menu = st.radio("Menu", ["🛒 POS Kasir", "📦 Inventaris", "📜 Log Transaksi"])
    
    st.divider()
    if st.button("🔄 Sync Cloud"):
        st.cache_data.clear()
        st.session_state.df_local = load_data()
        st.rerun()
    
    if st.button("⚠️ Reset Log Harian"):
        st.session_state.history = []
        st.rerun()

# --- 7. MAIN LOGIC ---

if menu == "🛒 POS Kasir":
    st.title("🛒 POS Terminal")
    df = st.session_state.df_local
    
    # 1. Barcode Scanner
    scan_val = st.text_input("⚡ SCAN BARCODE", key="scanner").strip()
    if scan_val:
        match = df[df['Barcode'] == scan_val]
        if not match.empty:
            p_name = match.iloc[0]['Produk']
            if df.loc[match.index[0], 'Stok'] > 0:
                st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1
                st.session_state.df_local.loc[match.index[0], 'Stok'] -= 1
                st.toast(f"✅ {p_name} ditambahkan!")
            else: st.error("Stok Habis!")
        else: st.warning("Barcode tidak terdaftar!")

    col_l, col_r = st.columns([1.5, 1])
    
    with col_l:
        cust = st.text_input("Nama Pelanggan / WA", placeholder="08xxxx")
        
        # 2. Fitur Tambah Manual (Pencarian Dropdown)
        st.divider()
        st.subheader("🔍 Cari Produk Manual")
        options = [f"{r['Produk']} | Stok: {r['Stok']}" for _, r in df.iterrows()]
        pick = st.selectbox("Pilih Produk", [""] + options)
        if pick:
            p_selected = pick.split(" | ")[0]
            q_add = st.number_input("Jumlah", min_value=1, value=1)
            if st.button("➕ Tambahkan ke Keranjang"):
                current_stok = df[df['Produk'] == p_selected]['Stok'].values[0]
                if current_stok >= q_add:
                    st.session_state.cart[p_selected] = st.session_state.cart.get(p_selected, 0) + q_add
                    st.session_state.df_local.loc[df['Produk'] == p_selected, 'Stok'] -= q_add
                    st.rerun()
                else:
                    st.error("Stok tidak mencukupi!")

    with col_r:
        st.subheader("📝 Detail Keranjang")
        subtotal = 0
        if not st.session_state.cart:
            st.info("Keranjang Kosong")
        else:
            for item, qty in list(st.session_state.cart.items()):
                price = df[df['Produk'] == item]['Harga Jual'].values[0]
                subtotal += (price * qty)
                
                c_name, c_qty, c_del = st.columns([2, 1.5, 0.5])
                c_name.write(f"**{item}**")
                
                # 3. Fitur Update Qty Langsung di Keranjang
                new_qty = c_qty.number_input("Qty", min_value=1, value=qty, key=f"q_{item}", label_visibility="collapsed")
                if new_qty != qty:
                    diff = new_qty - qty
                    st.session_state.df_local.loc[df['Produk'] == item, 'Stok'] -= diff
                    st.session_state.cart[item] = new_qty
                    st.rerun()
                
                if c_del.button("🗑️", key=f"del_{item}"):
                    st.session_state.df_local.loc[df['Produk'] == item, 'Stok'] += qty
                    del st.session_state.cart[item]
                    st.rerun()

        st.divider()
        disc = st.number_input("Diskon (Rp)", min_value=0, step=500)
        total_akhir = max(0, subtotal - disc)
        st.metric("Total Bayar", f"Rp {total_akhir:,.0f}")
        
        if st.button("🏁 SELESAIKAN & CETAK", use_container_width=True) and st.session_state.cart:
            now = datetime.datetime.now()
            entry = {
                "Tanggal": now.strftime("%Y-%m-%d"),
                "Waktu": now.strftime("%H:%M:%S"),
                "Pelanggan": cust if cust else "Umum",
                "Item": str(st.session_state.cart),
                "Total": total_akhir
            }
            st.session_state.history.insert(0, entry)
            receipt_pdf = generate_receipt(st.session_state.cart, total_akhir, cust, st.session_state.user, df)
            if receipt_pdf:
                st.download_button("📥 Unduh Struk", data=receipt_pdf, file_name=f"INV-{now.strftime('%H%M%S')}.pdf")
            st.session_state.cart = {}
            st.success("Tersimpan!")
            st.balloons()

elif menu == "📦 Inventaris":
    st.title("📦 Database Inventaris")
    search = st.text_input("Cari Nama/Barcode...").lower()
    mask = (st.session_state.df_local['Produk'].astype(str).str.lower().str.contains(search) | 
            st.session_state.df_local['Barcode'].astype(str).str.lower().str.contains(search))
    st.dataframe(st.session_state.df_local[mask].style.map(
        lambda x: 'color: #ff4b4b; font-weight: bold' if x < 5 else '', subset=['Stok']
    ), use_container_width=True)

elif menu == "📜 Log Transaksi":
    st.title("📜 Log Transaksi Harian")
    if st.session_state.history:
        log_df = pd.DataFrame(st.session_state.history)
        st.dataframe(log_df, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            log_df.to_excel(writer, index=False, sheet_name='Laporan')
        st.download_button(
            label="📥 Simpan ke Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"Laporan_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("Belum ada riwayat transaksi.")
