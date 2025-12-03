import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone

# =========================
# FUNGSI WAKTU WIB (UTC+7)
# =========================
def now_wib():
    return datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(
        timezone(timedelta(hours=7))
    )

# =========================
# LOAD ENV (username & password rahasia)
# =========================
load_dotenv()
USERNAME = os.getenv("LOGIN_USERNAME")
PASSWORD = os.getenv("LOGIN_PASSWORD")

LOGIN_URL = "http://103.176.44.189:3006/Auth/login"
REPORT_URL = "http://103.176.44.189:3006/Report"


# =========================
# LOGIN + FETCH HTML
# =========================
def fetch_report_html():
    if not USERNAME or not PASSWORD:
        raise RuntimeError(
            "USERNAME/PASSWORD tidak ditemukan di environment "
            "(LOGIN_USERNAME & LOGIN_PASSWORD)."
        )

    session = requests.Session()

    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
    }

    login_response = session.post(LOGIN_URL, data=login_data)
    if login_response.status_code != 200 or "login" in login_response.url.lower():
        raise RuntimeError("Login gagal ke server report.")

    report_response = session.get(REPORT_URL)
    if report_response.status_code != 200:
        raise RuntimeError("Gagal mengambil halaman report.")

    return report_response.text


# =========================
# PARSE HTML → DATAFRAME
# =========================
def parse_report_to_df(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        raise RuntimeError("Tidak ada tabel di halaman report.")

    table = tables[0]

    thead = table.find("thead")
    if thead is None:
        raise RuntimeError("thead tidak ditemukan pada tabel.")
    headers = [th.text.strip() for th in thead.find_all("th")]

    tbody = table.find("tbody")
    if tbody is None:
        raise RuntimeError("tbody tidak ditemukan pada tabel.")
    rows = [
        [td.text.strip() for td in tr.find_all("td")]
        for tr in tbody.find_all("tr")
    ]

    df = pd.DataFrame(rows, columns=headers)

    if "#" in df.columns:
        df = df.drop(columns=["#"])

    return df


# =========================
# FILTER STATUS
# =========================
def filter_by_status(df: pd.DataFrame, status: str | None) -> pd.DataFrame:
    if status is None:
        return df
    if "Status" not in df.columns:
        return df
    return df[df["Status"] == status].copy()


# =========================
# DOWNLOAD EXCEL (dengan key unik)
# =========================
def download_excel(df: pd.DataFrame, filename: str, label: str, key: str):
    buf = BytesIO()
    df.to_excel(buf, index=False)
    st.download_button(
        label=label,
        data=buf.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
    )


# =========================
# STREAMLIT APP
# =========================
st.set_page_config(page_title="Report Tower Online/Offline", layout="wide")
st.title("📊 Report Tower Online / Offline")
st.caption("Data diambil langsung dari web report dengan login otomatis (WIB).")

# Container untuk banner supaya bisa diisi setelah tombol diproses
banner_container = st.container()

# --- Sidebar: pilihan kategori data
with st.sidebar:
    st.header("Pengaturan")
    pilihan = st.radio(
        "Pilih kategori data:",
        ["Semua data", "Offline saja", "Online saja"],
    )

    if pilihan == "Semua data":
        status_filter = None
    elif pilihan == "Offline saja":
        status_filter = "Offline"
    else:
        status_filter = "Online"

# =========================
# TOMBOL REFRESH / AMBIL DATA
# =========================
refresh_clicked = st.button("🔄 Refresh / Ambil Data dari Web", type="primary")

if refresh_clicked:
    try:
        with st.spinner("Sedang login & mengambil report..."):
            html = fetch_report_html()
            df_report = parse_report_to_df(html)

        st.session_state["df"] = df_report
        st.session_state["last_update"] = now_wib()

        st.success("Data berhasil diambil dari server.")
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")

# =========================
# BANNER MERAH – DIISI SETELAH TOMBOL DIPROSES
# =========================
with banner_container:
    last_update = st.session_state.get("last_update")
    if last_update:
        info_waktu = last_update.strftime("%Y-%m-%d %H:%M:%S")
    else:
        info_waktu = "-"

    nama_user = "USER"  # bisa diganti nama kamu

    # PERHATIKAN: tidak ada indent 4 spasi di depan <div> agar tidak jadi code block
    banner_html = f"""
<div style="
    background: linear-gradient(90deg,#c62828,#ef5350);
    padding: 20px 26px;
    border-radius: 20px;
    color: white;
    margin-top: 10px;
    margin-bottom: 18px;
    display: flex;
    align-items: flex-start;
    gap: 16px;
">
  <div style="
      background: white;
      color: #c62828;
      width: 40px;
      height: 40px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: bold;
  ">
    💬
  </div>

  <div style="flex: 1;">
    <div style="font-size: 18px; font-weight: 700; margin-bottom: 4px;">
      Selamat Pagi, {nama_user}!
    </div>
    <div style="font-size: 14px; font-weight: 600; margin-bottom: 4px;">
      Data Maintenance Order terakhir diupdate pada: {info_waktu}
    </div>
    <div style="font-size: 12px; opacity: 0.9;">
      Tekan tombol <b>Refresh / Ambil Data dari Web</b> untuk mengambil update terbaru.
    </div>
  </div>
</div>
"""
    st.markdown(banner_html, unsafe_allow_html=True)

# --- Jika sudah ada data di session_state
if "df" in st.session_state:
    df = st.session_state["df"]
    df_filtered = filter_by_status(df, status_filter)

    # =========================
    # TIMESTAMP UNTUK NAMA FILE (WIB)
    # =========================
    last_update = st.session_state.get("last_update")
    if last_update:
        timestamp = last_update.strftime("%Y-%m-%d_%H-%M-%S")
    else:
        timestamp = now_wib().strftime("%Y-%m-%d_%H-%M-%S")

    # =========================
    # 💾 EXPORT PALING ATAS (DINAMIS + TGL/JAM WIB)
    # =========================
    st.markdown("### 💾 Export / Download")
    col1, col2 = st.columns(2)

    with col1:
        download_excel(
            df,
            f"report_semua_{timestamp}.xlsx",
            "Download Semua Data",
            key="dl_all",
        )

    if status_filter is None:
        export_label = "Download Semua Data"
        export_filename = f"report_semua_{timestamp}.xlsx"
    elif status_filter == "Offline":
        export_label = "Download Data Offline"
        export_filename = f"report_offline_{timestamp}.xlsx"
    else:
        export_label = "Download Data Online"
        export_filename = f"report_online_{timestamp}.xlsx"

    with col2:
        download_excel(
            df_filtered,
            export_filename,
            export_label,
            key="dl_filtered",
        )

    st.write("---")

    # =========================
    # TABEL SEMUA DATA
    # =========================
    st.subheader("📄 Data Tower (Semua)")
    st.dataframe(df, use_container_width=True, height=350)

    # =========================
    # TABEL FILTER SESUAI PILIHAN
    # =========================
    if status_filter is None:
        title = "Data Tower Offline & Online (Semua)"
    elif status_filter == "Offline":
        title = "Data Tower OFFLINE"
    else:
        title = "Data Tower ONLINE"

    st.subheader(f"🔍 {title}")
    st.dataframe(df_filtered, use_container_width=True, height=350)

    # =========================
    # GRAFIK JUMLAH SITE PER STATUS
    # =========================
    st.subheader("📈 Grafik Jumlah Site Berdasarkan Status")

    if "Status" in df.columns:
        counts = df["Status"].value_counts().reset_index()
        counts.columns = ["Status", "Jumlah Site"]

        st.dataframe(counts, use_container_width=True)
        st.bar_chart(counts.set_index("Status")["Jumlah Site"])
    else:
        st.info("Kolom 'Status' tidak ditemukan, grafik tidak bisa dibuat.")
else:
    st.info("Belum ada data. Klik tombol **🔄 Refresh / Ambil Data dari Web** terlebih dahulu.")
