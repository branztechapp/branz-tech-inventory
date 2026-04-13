import streamlit as st
import pandas as pd
from st_gsheets_connection import GSheetsConnection
from fpdf import FPDF
import datetime
import io
import plotly.express as px

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH POS", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .main-card { background: #1e293b; padding: 20px; border-radius: 15px; border: 1px solid #334155; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    div[data-baseweb="input"] { background-color: #1e293b !important; border: 1px solid #3b82f6 !important; }
    [data-testid="stMetricValue"] { color: #60a5fa !important; font-size: 2rem !important; }
    .stTable { background-color: #1e293b; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        df = data.copy()
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=['Produk'])
        
        # Standarisasi Data
        df['Barcode'] = df['Barcode'].astype(str).str.split('.').str[0].str.strip()
        df['Stok'] = pd.to_numeric(df['Stok'], errors='coerce').fillna(0).astype(int)
        df['Harga Jual'] = pd.to_numeric(df['Harga Jual'], errors='coerce').fillna(0)
        df['Harga Modal'] = pd.to_numeric(df.get('Harga Modal', 0), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame(columns=['Produk', 'Stok', 'Harga Jual', 'Barcode', 'Harga Modal'])

# --- 3. SESSION INITIALIZATION ---
if 'auth' not in st.session_state:
    st.session_state.update({
        'auth': False, 'user': None, 'role': None, 
        'cart': {}, 'history': [], 'df_local': load_data(), 
        'receipt_bin': None
    })

# --- 4. CORE FUNCTIONS ---
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
    pdf.set_font("Helvetica", size=8)
    pdf.cell(60, 4, f"Tgl: {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True)
    pdf.cell(60, 4, f"Kasir: {cashier} | Cust: {cust}", ln=True)
    pdf.cell(60, 2, "-"*35, ln=True)
    
    for item, qty in cart_data.items():
        price = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
        pdf.set_font("Helvetica", 'B', 8)
        pdf.multi_cell(60, 4, f"{item}")
        pdf.set_font("Helvetica", size=8)
        pdf.cell(60, 4, f"{qty} x {price:,.0f} = {qty*price:,.0f}", ln=True, align='R')
    
    pdf.cell(60, 2, "-"*35, ln=True)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(60, 8, f"TOTAL: Rp {total:,.0f}", ln=True, align='R')
    pdf.set_font("Helvetica", 'I', 7)
    pdf.cell(60, 10, "Terima Kasih Atas Kunjungan Anda", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- 5. LOGIN SYSTEM ---
if not st.session_state.auth:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        st.title("💎 LOGIN")
        u = st.text_input("Username").lower()
        p = st.text_input("Password", type="password")
        if st.button("MASUK"):
            if u == "admin" and p == "branz123":
                st.session_state.update({"auth": True, "user": "Admin", "role": "admin"})
                st.rerun()
            elif u == "staff" and p == "aisyah99":
                st.session_state.update({"auth": True, "user": "Aisyah", "role": "staff"})
                st.rerun()
            else: st.error("Akses Ditolak")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 6. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("BRANZ TECH")
    st.markdown(f"**{st.session_state.user}** | `{st.session_state.role.upper()}`")
    menu = st.radio("Navigasi", ["🛒 Kasir POS", "📦 Inventaris", "📜 Riwayat"])
    
    if st.session_state.role == "admin":
        st.divider()
        with st.expander("🛠️ Update Master Stok"):
            with st.form("stock_form"):
                f_name = st.text_input("Produk")
                f_modal = st.number_input("Harga Modal", min_value=0)
                f_jual = st.number_input("Harga Jual", min_value=0)
                f_stok = st.number_input("Stok", min_value=0)
                if st.form_submit_button("Simpan ke Cloud"):
                    df_up = st.session_state.df_local.copy()
                    if f_name in df_up['Produk'].values:
                        idx = df_up[df_up['Produk'] == f_name].index[0]
                        df_up.loc[idx, ['Stok', 'Harga Jual', 'Harga Modal']] = [f_stok, f_jual, f_modal]
                    else:
                        new_row = pd.DataFrame([{'Produk': f_name, 'Stok': f_stok, 'Harga Jual': f_jual, 'Harga Modal': f_modal}])
                        df_up = pd.concat([df_up, new_row], ignore_index=True)
                    conn.update(spreadsheet=URL_DB, data=df_up)
                    st.session_state.df_local = df_up
                    st.success("Tersimpan!")
                    st.rerun()

    st.divider()
    if st.button("🔄 Refresh Data"):
        st.session_state.df_local = load_data()
        st.rerun()
    if st.button("🚪 Keluar"):
        st.session_state.auth = False
        st.rerun()

# --- 7. KASIR MODULE ---
if menu == "🛒 Kasir POS":
    df = st.session_state.df_local
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        barcode = st.text_input("⚡ SCAN BARCODE", help="Arahkan scanner ke sini").strip()
        if barcode:
            match = df[df['Barcode'] == barcode]
            if not match.empty:
                if process_cart(match.iloc[0]['Produk']): st.toast("✅ Ditambahkan")
                else: st.error("Stok Habis!")
            else: st.warning("Barcode Tidak Terdaftar")
            st.rerun()
            
        st.subheader("Pencarian Produk")
        p_sel = st.selectbox("Cari Nama Barang", [""] + sorted(df['Produk'].tolist()))
        if p_sel and st.button(f"➕ Tambah {p_sel}"):
            if process_cart(p_sel): st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.subheader("🛒 Keranjang")
        cust_name = st.text_input("Nama Pelanggan", "Umum")
        
        if not st.session_state.cart:
            st.info("Keranjang kosong.")
        else:
            total_belanja = 0
            for itm, q in list(st.session_state.cart.items()):
                harga = df[df['Produk'] == itm]['Harga Jual'].values[0]
                sub = harga * q
                total_belanja += sub
                with st.container(border=True):
                    sc1, sc2 = st.columns([3, 1])
                    sc1.write(f"**{itm}**\n{q}x @ {harga:,.0f}")
                    if sc2.button("❌", key=f"del_{itm}"):
                        process_cart(itm, "remove")
                        st.rerun()
            
            st.divider()
            disc = st.number_input("Diskon (Rp)", value=0, step=500)
            net_total = max(0, total_belanja - disc)
            st.metric("TOTAL BAYAR", f"Rp {net_total:,.0f}")
            
            if st.button("🏁 SELESAI & CETAK", type="primary"):
                conn.update(spreadsheet=URL_DB, data=st.session_state.df_local)
                st.session_state.receipt_bin = make_pdf(st.session_state.cart, net_total, cust_name, st.session_state.user, df)
                st.session_state.history.append({"Jam": datetime.datetime.now().strftime("%H:%M"), "Cust": cust_name, "Total": net_total})
                st.session_state.cart = {}
                st.success("Data Cloud Terupdate!")
                st.rerun()

        if st.session_state.receipt_bin:
            st.download_button("📥 DOWNLOAD STRUK PDF", st.session_state.receipt_bin, 
                             file_name=f"Struk_{datetime.datetime.now().strftime('%H%M%S')}.pdf", mime="application/pdf")

# --- 8. INVENTARIS ---
elif menu == "📦 Inventaris":
    st.title("📦 Kontrol Inventaris")
    df = st.session_state.df_local
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(df[['Barcode', 'Produk', 'Stok', 'Harga Jual']], use_container_width=True, hide_index=True)
    with col2:
        st.subheader("Visual Stok")
        fig = px.pie(df, values='Stok', names='Produk', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)

# --- 9. RIWAYAT ---
elif menu == "📜 Riwayat":
    st.title("📜 Transaksi Hari Ini")
    if st.session_state.history:
        st.table(st.session_state.history)
    else:
        st.info("Belum ada aktivitas penjualan.")
