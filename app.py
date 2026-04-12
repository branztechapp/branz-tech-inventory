import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF

# --- CONFIG ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide")

# --- DATABASE ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Menambahkan parameter headers=0 agar baris pertama dianggap judul kolom
        data = conn.read(spreadsheet=url, ttl=0)
        return data.dropna(subset=['Produk'])
    except Exception as e:
        st.error(f"Error Database: {e}")
        return pd.DataFrame()

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🛡️ BRANZ TECH SaaS")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        # Daftar Partner Anda
        partners = {"admin": "branz123", "aisyah": "aisyah99", "nikmat": "cireng77"}
        if u in partners and partners[u] == p:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Gagal!")
    st.stop()

# --- FILTERING DATA ---
full_df = load_data()
# Mengambil data HANYA yang Owner_ID-nya sama dengan user yang login
df = full_df[full_df['Owner_ID'] == st.session_state.user] if not full_df.empty else full_df

st.sidebar.title(f"Partner: {st.session_state.user.upper()}")
menu = st.sidebar.radio("Menu", ["Stok Saya", "Scan Barcode", "Kasir"])

if menu == "Stok Saya":
    st.title(f"📦 Inventaris {st.session_state.user}")
    st.dataframe(df, use_container_width=True)

elif menu == "Scan Barcode":
    st.title("📷 Scanner HP")
    cam = st.camera_input("Scan Barcode")
    if cam:
        data = decode(Image.open(cam))
        if data:
            code = data[0].data.decode('utf-8')
            st.success(f"Barcode: {code}")
            item = df[df['Barcode'].astype(str) == code]
            if not item.empty:
                st.write(item)
            else:
                st.warning("Produk tidak ada di database Anda.")

elif menu == "Kasir":
    st.title("💸 Kasir Digital & Cetak Struk")
    
    if not df.empty:
        col_k1, col_k2 = st.columns([1, 1])
        
        with col_k1:
            prod = st.selectbox("Pilih Produk", df['Produk'].unique())
            qty = st.number_input("Jumlah Beli", min_value=1, step=1)
            
            # Ambil detail produk dari dataframe
            data_produk = df[df['Produk'] == prod].iloc[0]
            harga = data_produk['Harga Jual']
            total = harga * qty
            
            st.subheader(f"Total: Rp {total:,.0f}")

        # Tombol untuk generate PDF
        if st.button("Generate Struk POS"):
            # --- LOGIKA STRUK POS (VERTIKAL) ---
            pdf = FPDF(format=(80, 150)) # Ukuran kertas termal 80mm
            pdf.add_page()
            
            # Header Toko
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(60, 8, txt="BRANZ TECH PRO", ln=1, align='C')
            pdf.set_font("Arial", '', 8)
            pdf.cell(60, 5, txt=f"Partner: {st.session_state.user.upper()}", ln=1, align='C')
            pdf.cell(60, 5, txt=f"{datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1, align='C')
            pdf.cell(60, 5, txt="-"*40, ln=1, align='C')

            # Detail Barang
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(30, 8, txt="Item", ln=0)
            pdf.cell(10, 8, txt="Qty", ln=0)
            pdf.cell(20, 8, txt="Total", ln=1, align='R')
            
            pdf.set_font("Arial", '', 9)
            # Potong nama produk jika terlalu panjang agar tidak berantakan di struk
            nama_pendek = prod[:15]
            pdf.cell(30, 8, txt=f"{nama_pendek}", ln=0)
            pdf.cell(10, 8, txt=f"{qty}", ln=0)
            pdf.cell(20, 8, txt=f"{total:,.0f}", ln=1, align='R')
            
            # Footer & Total
            pdf.cell(60, 5, txt="-"*40, ln=1, align='C')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(30, 10, txt="TOTAL", ln=0)
            pdf.cell(20, 10, txt=f"Rp {total:,.0f}", ln=1, align='R')
            
            pdf.set_font("Arial", 'I', 8)
            pdf.ln(5)
            pdf.cell(60, 5, txt="Terima Kasih Telah Berbelanja", ln=1, align='C')

            # Simpan sementara dan berikan tombol download
            file_name = f"struk_{datetime.now().strftime('%H%M%S')}.pdf"
            pdf.output(file_name)
            
            with open(file_name, "rb") as f:
                st.download_button(
                    label="📥 Download Struk (Siap Cetak)",
                    data=f,
                    file_name=file_name,
                    mime="application/pdf"
                )
    else:
        st.warning("Data inventaris Anda masih kosong.")
