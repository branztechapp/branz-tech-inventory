import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import urllib.parse

# Setup Halaman
st.set_page_config(page_title="BRANZ TECH Pro", layout="wide")

# Database Sederhana
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=[
        "Barcode", "Produk", "Stok", "Harga Modal", "Harga Jual", "Exp Date"
    ])
if 'sales_history' not in st.session_state:
    st.session_state.sales_history = pd.DataFrame(columns=["Waktu", "Produk", "Laba"])

# Fungsi Kirim WA
def kirim_wa(nama_produk, sisa_stok):
    pesan = f"⚠️ *PERINGATAN BRANZ TECH*\n\nStok produk *{nama_produk}* hampir habis!\nSisa stok: *{sisa_stok} pcs*.\nSegera lakukan restok agar penjualan tetap lancar!"
    url = f"https://wa.me/?text={urllib.parse.quote(pesan)}"
    return url

# --- UI SIDEBAR ---
st.sidebar.title("🚀 BRANZ TECH")
menu = st.sidebar.radio("Menu Utama", ["Dashboard & Grafik", "Update Stok", "Transaksi Penjualan"])

# --- HALAMAN 1: DASHBOARD & GRAFIK ---
if menu == "Dashboard & Grafik":
    st.title("📊 Analisis Bisnis Real-Time")
    
    # Indikator Utama
    total_laba = st.session_state.sales_history['Laba'].sum()
    st.metric("Total Laba Bersih", f"Rp {total_laba:,.0f}")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Status Stok Barang")
        if not st.session_state.inventory.empty:
            fig_stok = px.bar(st.session_state.inventory, x="Produk", y="Stok", color="Stok",
                             color_continuous_scale="RdYlGn", title="Jumlah Stok per Produk")
            st.plotly_chart(fig_stok, use_container_width=True)
        else:
            st.info("Belum ada data produk.")

    with col2:
        st.subheader("📈 Tren Laba")
        if not st.session_state.sales_history.empty:
            fig_laba = px.line(st.session_state.sales_history, x="Waktu", y="Laba", 
                              title="Pertumbuhan Laba", markers=True)
            st.plotly_chart(fig_laba, use_container_width=True)
        else:
            st.info("Belum ada riwayat penjualan.")

# --- HALAMAN 2: UPDATE STOK ---
elif menu == "Update Stok":
    st.title("📥 Input Produk Baru")
    with st.form("form_stok"):
        col_a, col_b = st.columns(2)
        barcode = col_a.text_input("ID/Barcode")
        nama = col_b.text_input("Nama Produk")
        stok_awal = col_a.number_input("Jumlah Stok", min_value=1)
        modal = col_b.number_input("Harga Modal", min_value=0)
        jual = col_a.number_input("Harga Jual", min_value=0)
        exp = col_b.date_input("Masa Kedaluwarsa")
        
        if st.form_submit_button("Simpan ke Database"):
            new_row = pd.DataFrame([[barcode, nama, stok_awal, modal, jual, exp]], 
                                   columns=st.session_state.inventory.columns)
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
            st.success("Data Tersimpan!")

# --- HALAMAN 3: PENJUALAN & NOTIF WA ---
elif menu == "Transaksi Penjualan":
    st.title("💸 Kasir Digital")
    if st.session_state.inventory.empty:
        st.warning("Isi stok dulu di menu Update Stok!")
    else:
        produk_pilih = st.selectbox("Pilih Barang", st.session_state.inventory['Produk'].unique())
        qty = st.number_input("Jumlah Terjual", min_value=1)
        
        if st.button("Proses & Hitung Laba"):
            idx = st.session_state.inventory[st.session_state.inventory['Produk'] == produk_pilih].index[0]
            
            # Update Stok
            st.session_state.inventory.at[idx, 'Stok'] -= qty
            sisa = st.session_state.inventory.at[idx, 'Stok']
            
            # Hitung Laba
            laba = (st.session_state.inventory.at[idx, 'Harga Jual'] - st.session_state.inventory.at[idx, 'Harga Modal']) * qty
            new_sale = pd.DataFrame([[datetime.now(), produk_pilih, laba]], columns=st.session_state.sales_history.columns)
            st.session_state.sales_history = pd.concat([st.session_state.sales_history, new_sale], ignore_index=True)
            
            st.balloons()
            st.success(f"Berhasil! Laba: Rp {laba:,.0f}")
            
            # FITUR WA: Jika stok di bawah 5
            if sisa <= 5:
                st.error(f"STOK KRITIS: Sisa {sisa}!")
                wa_link = kirim_wa(produk_pilih, sisa)
                st.link_button("📲 Kirim Notifikasi WA ke Owner", wa_link)