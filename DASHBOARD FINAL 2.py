
import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="Dashboard Kepatuhan Pajak", layout="wide")
st.markdown("## 📊 Dashboard Kepatuhan Pajak (Versi SAFE++)")

# ===================================
# Fungsi bantu: Normalisasi kolom
# ===================================
def normalize_columns(df):
    df.columns = [str(col).strip().upper().replace("\n", " ") for col in df.columns]
    return df

# ===================================
# Fungsi: Hitung kepatuhan
# ===================================
def hitung_kepatuhan(df, tahun_pajak):
    df = normalize_columns(df)

    # Cek kolom wajib
    required_cols = ["TMT", "NAMA OP", "STATUS"]
    if not all(col in df.columns for col in required_cols):
        st.error("❌ Kolom wajib hilang: TMT, NAMA OP, STATUS. Harap periksa file Anda.")
        return None, None

    # Format tanggal
    df["TMT"] = pd.to_datetime(df["TMT"], errors="coerce")
    df["TAHUN TMT"] = df["TMT"].dt.year

    # Identifikasi kolom pembayaran berdasarkan tahun
    payment_cols = [col for col in df.columns if str(tahun_pajak) in col and df[col].dtype != "O"]
    if not payment_cols:
        st.warning("⚠️ Tidak ditemukan kolom pembayaran murni yang valid.")
        return df, []

    # Hitung indikator
    df["TOTAL PEMBAYARAN"] = df[payment_cols].sum(axis=1)
    df["BULAN PEMBAYARAN"] = (df[payment_cols] > 0).sum(axis=1)
    df["BULAN AKTIF"] = 12  # Default 12
    df["RATA-RATA PEMBAYARAN"] = df["TOTAL PEMBAYARAN"] / df["BULAN PEMBAYARAN"].replace(0, 1)
    df["KEPATUHAN (%)"] = (df["BULAN PEMBAYARAN"] / df["BULAN AKTIF"]) * 100

    def klasifikasi(kepatuhan):
        if kepatuhan <= 33.333:
            return "Kurang Patuh"
        elif kepatuhan <= 66.666:
            return "Cukup Patuh"
        else:
            return "Patuh"

    df["KLASIFIKASI KEPATUHAN"] = df["KEPATUHAN (%)"].apply(klasifikasi)
    return df, payment_cols

# ===================================
# Sidebar Input
# ===================================
st.sidebar.header("🗂️ Input Data")
tahun_pajak = st.sidebar.selectbox("📅 Pilih Tahun Pajak", options=[2023, 2024, 2025], index=1)
uploaded_file = st.sidebar.file_uploader("📤 Upload File Excel", type=["xlsx"])

# ===================================
# Main
# ===================================
if uploaded_file:
    sheet_names = pd.ExcelFile(uploaded_file).sheet_names
    selected_sheet = st.selectbox("📑 Pilih Nama Sheet", sheet_names)
    df_input = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
    df_output, payment_cols = hitung_kepatuhan(df_input.copy(), tahun_pajak)

    if df_output is not None:
        st.success("✅ Data berhasil diproses dan difilter!")
        st.dataframe(df_output)

        # Download Excel
        with io.BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_output.to_excel(writer, sheet_name="Hasil", index=False)
            st.download_button("📥 Download Hasil Excel", data=buffer.getvalue(),
                               file_name="hasil_dashboard_kepatuhan.xlsx")

        # Charts
        st.markdown("### 📈 Tren Pembayaran Pajak per Bulan")
        if payment_cols:
            bulanan = df_output[payment_cols].sum().reset_index()
            bulanan.columns = ["Bulan", "Total Pembayaran"]
            bulanan["Bulan"] = pd.to_datetime(bulanan["Bulan"], errors="coerce")
            bulanan = bulanan.sort_values("Bulan")
            fig = px.line(bulanan, x="Bulan", y="Total Pembayaran", markers=True)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🥧 Pie Chart Kepatuhan Wajib Pajak")
        pie_df = df_output["KLASIFIKASI KEPATUHAN"].value_counts().reset_index()
        pie_df.columns = ["Kategori", "Jumlah"]
        fig_pie = px.pie(pie_df, names="Kategori", values="Jumlah",
                         title="Distribusi Klasifikasi Kepatuhan",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("### 🏅 Top 20 Pembayar Tertinggi")
        top_df = df_output.sort_values("TOTAL PEMBAYARAN", ascending=False).head(20)
        st.dataframe(top_df[["NAMA OP", "STATUS", "TOTAL PEMBAYARAN", "KEPATUHAN (%)", "KLASIFIKASI KEPATUHAN"]])

else:
    st.info("💡 Silakan upload file Excel berisi data setoran masa pajak.")
    with open("CONTOH_FORMAT_SETORAN MASA.xlsx", "rb") as f:
        st.download_button("📎 Download Contoh Format Excel", data=f.read(),
                           file_name="CONTOH_FORMAT_SETORAN MASA.xlsx")


        # Ringkasan Statistik
        st.markdown("### 📌 Ringkasan Statistik")
        col1, col2, col3 = st.columns(3)
        col1.metric("📌 Total WP", df_output.shape[0])
        col2.metric("💸 Total Pembayaran", f"Rp {df_output['TOTAL PEMBAYARAN'].sum():,.0f}")
        col3.metric("📈 Rata-rata Pembayaran", f"Rp {df_output['TOTAL PEMBAYARAN'].mean():,.0f}")

        # Bar Chart Jumlah WP per Klasifikasi
        st.markdown("### 📊 Jumlah WP per Klasifikasi")
        fig_bar = px.bar(pie_df, x="Kategori", y="Jumlah", color="Kategori",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_bar, use_container_width=True)

        # Boxplot Total Pembayaran per Klasifikasi
        st.markdown("### 📦 Sebaran Total Pembayaran per Klasifikasi")
        fig_box = px.box(df_output, x="KLASIFIKASI KEPATUHAN", y="TOTAL PEMBAYARAN",
                         color="KLASIFIKASI KEPATUHAN", points="all",
                         color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig_box, use_container_width=True)
