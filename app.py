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

# --- 2. DATA ENGINE ---
# Kredensial dibersihkan dari karakter spasi tak terlihat
service_account_info = {
    "type": "service_account",
    "project_id": "branz-tech-pos",
    "private_key_id": "577a5f3591e532f094844bbdfadff8f11d0c4415",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQClnYwGprwHmO5m\ncCkAaBZH0tExIwkZ4LIYKgFlSlAAl6A1QcMjomajGcl20OelAbZJ5Aq4foUwxE4O\nYlDAp5BqjjsrWce8BpwC8bFOeJ0/us66dh5pUhIbao1NtWN0F5SUBYXbHb594xtc\njWaEh9aLZNUG3bJufXlQ6m514UTy0KSuUK00pamuehszWqlTs4gg93YzxJ72PS5b\nZWniKgSV27tycja34SpTjBeCIBUuqu4TfPnhsisbYAiJCFpDBcA02bWwlkFR5Ii2\nKxZPrHnE4F9+hrG7UE6Ico3jqEtSkPUnjLy82PPH8SGqmWDBwbqqKcl3ro1NZBzt\njbS/DhtLAgMBAAECggEAGnDHrTwrYs8gqIwZj64OeJMIwN6GEnKUHFWAeYpesWmD\ns1z3aZYA6uMwDd8WTHq0fqGAsKnKW9nLWHKLz+YwoUJp4ebog3VOrQ2nMA8Dk+wg\nGxbGjiwDJgth2dkuspcdKnCjSTM7eV+ru5/7kQca0pBbjkgQt6EioC99SSaY2mcB\nQpQ6Rv2qRcIMzaAF1bk1AtbqAJSLK8eDYhbVzuaW1+5faothOb3xa9bfS6xteLFu\nlvC1IiY1vs+0pdCUEC0OLl7haVaDZiGS+UuZKQVKH+ox0YcRNmZNGkpJ+js4H9Y0\n2Xji5YYSh6ectOVbD9LPCvOB1qYn8zYTIg8j3/HY8QKBgQDXm/y/C0JUZ658PHj4\nwAiq+IPUvIxZ4UPijxk7L3YRVScqNrab2uKylVN9K0HTZ/dyRJ+ukbOy9kM82VIW\nnmZEbbDcNaS7SF62+i3g2Q2ZdFBGGrxjoXSdTAqE+bsGJIduqg9D4cdpbXCuASWE\nXjrvrUINO5WNT3mk/PY9i+dCyQKBgQDEo/5SvakVI0LcNrI8lYzl6obwbwKLyL3p\nCKca3JS8gchgkfXLIk4tg9XTW+QHE5RON3RNw0AeCCgjHorvlHKBDW2Cfn43XAbV\nBCD3/JeCD+muFWZ1/tu6nexF+JoyC44MFrwGjz7aMlK9AIebYAfo0btO3NjbWwNL\nVTfsRezDcwKBgQCkJh8jt8e1CQa/kS6se09eEzwS78WO/EC5sSaNd9HU2lap/ePC\n/r9PJP7eMdu4vtOWDIbh2g3Mt05zeiTUEZ5chIJ89N5Is41gk1HweG+xH+upo9s/\nowFsbCMqIBLyV0dAyno6vR8btfVulHLitvb52JeMCYwPfK1pHim+q8/SeQKBgFHA\n2Kivv49RNKf3eYzkpEqmgemOTaGuGP68oTTyxkfFMXis1mLY5WXY7NpN1vT2N+94\n8Lqv1YVm4MERHrRSpHRxD7l0O6dqdFC1wbs4Ygkp8n502T9vcQ0aQTQqEnmCAlGW\nVh/oCDqRN4LqqHZ5q3ApWlWETgiMw0bbrD9oJvJvAoGAKhMLuw6ScwftLn/O7FlT\n6NwVPBzIczVUSvbswIw6W2D0AEzwwJ/Fysm8AGmQZpuGsAJegJ5huRKdVGyvGmRM\nQyeBgQevXX519iNbAuBLHcxWFCWzdHZ2fgg6lMd28e72Qc7feudJKW45dd4i8fhj\nx6Pigg5Tg1JuYn45+zmKkwM=\n-----END PRIVATE KEY-----\n",
    "client_email": "gsheets-connector@branz-tech-pos.iam.gserviceaccount.com"
}

# Perbaikan Inisialisasi Koneksi
conn = st.connection("gsheets", type=GSheetsConnection, service_account=service_account_info)

URL_SHEET = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        data = conn.read(spreadsheet=URL_SHEET, ttl=0)
        # Bersihkan nama kolom dari spasi atau karakter aneh
        data.columns = [str(c).strip() for c in data.columns]
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0)
        return df_clean
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return pd.DataFrame()

def update_gsheets_stock(cart_items):
    try:
        df_current = conn.read(spreadsheet=URL_SHEET, ttl=0)
        df_current.columns = [str(c).strip() for c in df_current.columns]

        for item, qty_beli in cart_items.items():
            idx = df_current[df_current['Produk'] == item].index
            if not idx.empty:
                stok_sekarang = df_current.loc[idx, 'Stok'].values[0]
                df_current.loc[idx, 'Stok'] = stok_sekarang - qty_beli
        
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
        # Menghitung valuasi dengan kolom yang dibersihkan
        total_val = (df['Stok'] * df['Harga Jual']).sum()
        c1.metric("Valuasi Stok", f"Rp {total_val:,.0f}")
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
                amount = st.number_input("Jumlah Beli", min_value=1, max_value=int(stok_avail) if stok_avail > 0 else 1, value=1)
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
            # Perbaikan pencarian barcode (menyamakan tipe data)
            match = df[df['Barcode'].astype(str).str.contains(str(b_code))]
            if not match.empty:
                name = match['Produk'].values[0]
                st.info(f"Terdeteksi: {name}")
                if st.button("Tambah 1 ke Keranjang"):
                    st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1
                    st.rerun()
            else: st.warning("Produk tidak terdaftar.")
