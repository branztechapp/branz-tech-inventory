import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import urllib.parse
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

# Fungsi format mata uang
def format_rp(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- 2. SISTEM LOGIN (MULTI-USER) ---
# Daftar user untuk agen/member
users = {
    "admin": "branz123",
    "agen_aisyah": "aisyah99",
    "agen_nikmat": "cireng77"
}

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 BRANZ TECH LOGIN")
    user = st.text_input("Username")
    passw = st.text_input("Password", type="password")
    if st.button("Masuk"):
        if user in users and users[user] == passw:
            st.session_state.auth = True
            st.session_state.user_now = user
            st.rerun()
        else:
            st.error("Username/Password salah!")
    st.stop()

# --- 3. KONEKSI GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url, ttl=0)
    df = df.dropna(subset=['Produk'])
except Exception as e:
    st.error(f"Koneksi GSheets Gagal: {e}")
    st.stop()

# --- 4. SIDEBAR & NAVIGASI (OPTIMASI LOGO) ---
with st.sidebar:
    current_dir = os.path.dirname(__file__)
    logo_path = os.path.join(current_dir, "logo.png")
    
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        try:
            st.image("logo.png", width=200)
        except:
            st.title("🚀 BRANZ TECH")
    
    st.write(f"👤 User: **{st.session_state.user_now}**")
    st.write(f"📅 {datetime.now().strftime('%d/%m/%Y')}")
    st.divider()
    menu = st.radio("Menu Utama", ["Dashboard & Grafik", "Update Stok", "Transaksi Penjualan"])
    st.divider()
    
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 5. DASHBOARD & GRAFIK ---
if menu == "Dashboard & Grafik":
    st.title("📊 Analisis Bisnis Real-Time")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        total_stok = df['Stok'].sum()
        st.metric("Total Stok", f"{int(total_stok)} Pcs")
    with col2:
        df['Total Modal'] = df['Stok'] * df['Harga Modal']
        nilai_aset = df['Total Modal'].sum()
        st.metric("Nilai Aset (Modal)", format_rp(nilai_aset))
    with col3:
        potensi_laba = ((df['Harga Jual'] - df['Harga Modal']) * df['Stok']).sum()
        st.metric("Potensi Laba Stok", format_rp(potensi_laba))

    st.divider()

    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("📦 Status Stok")
        fig = px.bar(df, x="Produk", y="Stok", color="Stok", 
                     color_continuous_scale="RdYlGn", text_auto=True,
                     title="Jumlah Stok Saat Ini")
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("💰 Analisis Harga Jual")
        fig_price = px.scatter(df, x="Produk", y="Harga Jual", size="Stok", color="Produk",
                               title="Perbandingan Harga Jual & Volume Stok")
        st.plotly_chart(fig_price, use_container_width=True)

    st.subheader("📑 Data Inventaris Lengkap")
    st.dataframe(df[['Barcode', 'Produk', 'Stok', 'Harga Modal', 'Harga Jual']], use_container_width=True)

# --- 6. UPDATE STOK ---
elif menu == "Update Stok":
    st.title("📥 Input Produk Baru")
    st.info("Silakan update data langsung di Google Sheets Anda untuk perubahan permanen.")
    st.link_button("📂 Buka Google Sheets", url)
    st.divider()
    st.subheader("Data yang tersimpan saat ini:")
    st.table(df)

# --- 7. TRANSAKSI & STRUK DIGITAL ---
elif menu == "Transaksi Penjualan":
    st.title("💸 Kasir Digital")
    
    with st.container(border=True):
        produk_pilih = st.selectbox("Pilih Barang", df['Produk'].unique())
        qty = st.number_input("Jumlah Terjual", min_value=1, step=1)
        
        data_p = df[df['Produk'] == produk_pilih].iloc[0]
        harga_jual = data_p['Harga Jual']
        harga_modal = data_p['Harga Modal']
        total_bayar = harga_jual * qty
        laba = (harga_jual - harga_modal) * qty
        sisa_stok_tampilan = data_p['Stok'] - qty

        st.write(f"Harga Satuan: **{format_rp(harga_jual)}**")
        st.write(f"Total Bayar: **{format_rp(total_bayar)}**")
        
        if st.button("Proses & Cetak Struk"):
            if qty > data_p['Stok']:
                st.error(f"Gagal! Stok tidak mencukupi (Sisa: {data_p['Stok']})")
            else:
                st.balloons()
                st.success(f"Transaksi Berhasil!")
                
                # --- STRUK DIGITAL DENGAN NOMOR WA ANDA ---
                with st.expander("📝 LIHAT STRUK PENJUALAN", expanded=True):
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; padding:20px; border-radius:10px; background-color: #1e1e1e; font-family: 'Courier New', Courier, monospace;">
                    <h3 style="text-align:center; margin-bottom: 5px;">BRANZ TECH PRO</h3>
                    <p style="text-align:center; font-size: 14px; margin-top: 0px;">
                        Jombang, Jawa Timur<br>
                        WA: 085704223340
                    </p>
                    <hr style="border-top: 1px dashed #bbb;">
                    <p style="font-size: 14px;">
                        <b>Tanggal :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
                        <b>Kasir   :</b> {st.session_state.user_now}<br>
                        <b>Produk  :</b> {produk_pilih}
                    </p>
                    <hr style="border-top: 1px dashed #bbb;">
                    <table style="width:100%; font-size: 14px;">
                        <tr>
                            <td>{qty} pcs x {format_rp(harga_jual)}</td>
                            <td style="text-align:right;">{format_rp(total_bayar)}</td>
                        </tr>
                    </table>
                    <hr style="border-top: 1px dashed #bbb;">
                    <h3 style="text-align:right;">TOTAL: {format_rp(total_bayar)}</h3>
                    <hr style="border-top: 1px dashed #bbb;">
                    <p style="text-align:center; font-size: 12px; margin-top: 20px;">
                        <i>Terima kasih telah berbelanja!<br>
                        Simpan struk ini sebagai bukti transaksi resmi.</i>
                    </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Notifikasi WA ke nomor Anda jika stok menipis
                if sisa_stok_tampilan <= 5:
                    st.warning(f"⚠️ Stok Hampir Habis! Sisa: {int(sisa_stok_tampilan)}")
                    pesan = f"⚠️ *PERINGATAN BRANZ TECH*\nStok *{produk_pilih}* sisa {int(sisa_stok_tampilan)} pcs."
                    # Mengarahkan langsung ke nomor Anda
                    wa_url = f"https://wa.me/6285704223340?text={urllib.parse.quote(pesan)}"
                    st.link_button("📲 Kirim Notifikasi WA ke Owner", wa_url)
