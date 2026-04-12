import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
import datetime
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
    .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
    .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
    .critical-stock { color: #ff4b4b; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
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

# --- 5. FUNGSI CETAK PDF (Dengan Pajak & Diskon) ---
def generate_receipt(cart_data, subtotal, discount, tax, total, customer, user, df_ref):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "BRANZ TECH PRESTIGE", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 7, f"Tanggal: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.cell(190, 7, f"Pelanggan: {customer if customer else 'Umum'}", ln=True, align='C')
    pdf.cell(190, 7, f"Kasir: {user.upper()}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(80, 10, "Produk", 1)
    pdf.cell(20, 10, "Qty", 1)
    pdf.cell(45, 10, "Harga", 1)
    pdf.cell(45, 10, "Subtotal", 1, ln=True)
    
    pdf.set_font("Arial", size=11)
    for item, q in cart_data.items():
        price = df_ref[df_ref['Produk'] == item]['Harga Jual'].values[0]
        pdf.cell(80, 10, str(item), 1)
        pdf.cell(20, 10, str(q), 1)
        pdf.cell(45, 10, f"{price:,.0f}", 1)
        pdf.cell(45, 10, f"{price*q:,.0f}", 1, ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(145, 7, "Subtotal:", 0, 0, 'R')
    pdf.cell(45, 7, f"Rp {subtotal:,.0f}", 0, 1, 'R')
    pdf.cell(145, 7, f"Diskon:", 0, 0, 'R')
    pdf.cell(45, 7, f"- Rp {discount:,.0f}", 0, 1, 'R')
    pdf.cell(145, 7, f"Pajak (PPN):", 0, 0, 'R')
    pdf.cell(45, 7, f"Rp {tax:,.0f}", 0, 1, 'R')
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(145, 10, "TOTAL AKHIR:", 0, 0, 'R')
    pdf.cell(45, 10, f"Rp {total:,.0f}", 0, 1, 'R')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(190, 10, "Terima kasih atas kunjungan Anda!", 0, 0, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 6. NAVIGATION ---
df = st.session_state.df_local

with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    st.divider()
    menu = st.radio("Menu Navigasi", ["📊 Dashboard", "🛒 Kasir (POS)", "📦 Inventaris Stok", "📜 Riwayat Transaksi"])
    st.divider()
    
    # Fitur 5: Export Laporan
    st.subheader("💾 Backup Data")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Inventaris (CSV)", data=csv, file_name=f"Inventaris_BranzTech_{datetime.date.today()}.csv", mime='text/csv', use_container_width=True)
    
    if st.button("🔄 Sync Cloud Data", use_container_width=True):
        st.session_state.df_local = load_data()
        st.rerun()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 7. PAGE LOGIC ---

if menu == "📊 Dashboard":
    st.title("📈 Business Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Produk", len(df))
    # Fitur 4: Alert Stok Kritis
    low_stock_count = len(df[df['Stok'] < 3])
    c2.metric("Stok Kritis (<3)", low_stock_count, delta=-low_stock_count, delta_color="inverse")
    c3.metric("Estimasi Aset", f"Rp {(df['Stok'] * df['Harga Jual']).sum():,.0f}")
    
    if low_stock_count > 0:
        st.warning(f"Ada {low_stock_count} produk yang hampir habis! Segera cek Inventaris.")
    st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventaris Stok":
    st.title("📦 Database Inventaris")
    search = st.text_input("Cari Produk...")
    
    # Fitur 4: Highlight Stok Rendah
    def highlight_low_stock(val):
        color = 'red' if val < 3 else 'white'
        return f'color: {color}'

    display_df = df[df['Produk'].str.contains(search, case=False)] if search else df
    st.dataframe(display_df.style.applymap(highlight_low_stock, subset=['Stok']), use_container_width=True)

elif menu == "📜 Riwayat Transaksi":
    st.title("📜 Log Transaksi Harian")
    if not st.session_state.history:
        st.info("Belum ada transaksi hari ini.")
    else:
        history_df = pd.DataFrame(st.session_state.history)
        st.dataframe(history_df, use_container_width=True)
        st.metric("Total Penjualan Sesi Ini", f"Rp {history_df['Total'].sum():,.0f}")

elif menu == "🛒 Kasir (POS)":
    st.title("🛒 POS Terminal")
    
    col_pos, col_cart = st.columns([1.4, 1])

    with col_pos:
        # Fitur 3: Manajemen Pelanggan
        st.subheader("👤 Data Pelanggan")
        cust_name = st.text_input("Nama Pelanggan / WA", placeholder="Contoh: Budi - 0812...")
        
        st.divider()
        st.subheader("🛍️ Pilih Produk")
        options = [f"{r['Produk']} | Stok: {int(r['Stok'])}" for _, r in df.iterrows()]
        pick = st.selectbox("Cari Barang", [""] + options)
        
        if pick:
            name = pick.split(" | ")[0]
            current_s = df[df['Produk'] == name]['Stok'].values[0]
            q_input = st.number_input("Jumlah Beli", min_value=1, max_value=int(current_s) if current_s > 0 else 1, value=1)
            
            if st.button("➕ Tambah ke Keranjang", use_container_width=True):
                st.session_state.cart[name] = st.session_state.cart.get(name, 0) + q_input
                st.session_state.df_local.loc[df['Produk'] == name, 'Stok'] -= q_input
                st.rerun()

    with col_cart:
        st.subheader("📝 Keranjang")
        subtotal = 0
        if not st.session_state.cart:
            st.write("Keranjang kosong.")
        else:
            for item, q in list(st.session_state.cart.items()):
                prc = df[df['Produk'] == item]['Harga Jual'].values[0]
                res = prc * q
                subtotal += res
                c_info, c_del = st.columns([4, 1])
                c_info.write(f"**{item}** ({q}x)")
                if c_del.button("🗑️", key=f"del_{item}"):
                    st.session_state.df_local.loc[df['Produk'] == item, 'Stok'] += q
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            # Fitur 2: Diskon & Pajak
            col_d, col_t = st.columns(2)
            disc_input = col_d.number_input("Diskon (Rp)", min_value=0, step=500)
            tax_rate = col_t.selectbox("Pajak (PPN)", [0, 0.11], format_func=lambda x: f"{int(x*100)}%")
            
            tax_val = (subtotal - disc_input) * tax_rate
            total_akhir = subtotal - disc_input + tax_val
            
            st.write(f"Subtotal: Rp {subtotal:,.0f}")
            st.write(f"Total Akhir: **Rp {total_akhir:,.0f}**")
            
            if st.button("🏁 SELESAIKAN TRANSAKSI", use_container_width=True):
                # Fitur 1: Simpan ke Riwayat
                new_log = {
                    "Waktu": datetime.datetime.now().strftime("%H:%M:%S"),
                    "Pelanggan": cust_name if cust_name else "Umum",
                    "Item": ", ".join(st.session_state.cart.keys()),
                    "Total": total_akhir
                }
                st.session_state.history.append(new_log)
                
                # Buat PDF
                receipt_pdf = generate_receipt(st.session_state.cart, subtotal, disc_input, tax_val, total_akhir, cust_name, st.session_state.user, df)
                
                st.download_button("📥 Download Struk PDF", data=receipt_pdf, file_name=f"BRANZ_{datetime.datetime.now().strftime('%H%M%S')}.pdf", mime="application/pdf", use_container_width=True)
                
                st.session_state.cart = {}
                st.success("Transaksi Berhasil Dicatat!")
                st.balloons()
