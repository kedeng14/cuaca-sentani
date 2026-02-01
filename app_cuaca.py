import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Ops Cuaca Sentani Multi-ENS", layout="wide")
st_autorefresh(interval=60000, key="fokus_periode_update")

# 2. Fungsi Fetch Data
@st.cache_data(ttl=3600)
def fetch_multi_ensemble(lat, lon, params):
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    res = requests.get(url, params=params).json()
    return res

def get_weather_desc(code):
    if code is None or np.isnan(code): return "N/A"
    mapping = {
        0: "☀️ Cerah", 1: "🌤️ Cerah Berawan", 2: "⛅ Berawan", 3: "☁️ Mendung",
        45: "🌫️ Kabut", 51: "🌦️ Gerimis Rgn", 61: "🌧️ Hujan Ringan", 
        63: "🌧️ Hujan Sedang", 65: "🌧️ Hujan Lebat", 95: "⛈️ Badai Petir"
    }
    return mapping.get(int(code), f"Kode {int(code)}")

# 3. Parameter & Sidebar
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)
lat, lon = -2.5756744335142865, 140.5185071099937

try:
    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2: st.image("bmkg.png", width=150)
    st.sidebar.markdown("---")
    st.sidebar.write(f"🕒 **Update:** {now_wit.strftime('%H:%M:%S')} WIT")
    server_placeholder = st.sidebar.empty()
    st.sidebar.warning("**📢 DISCLAIMER**\nData ini alat bantu model. Analisis akhir tetap pada Forecaster (MJO, Streamline, dll).")
except:
    st.sidebar.warning("Logo tidak ditemukan")

# 4. Request API
params = {
    "latitude": lat, "longitude": lon,
    "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "weather_code"],
    "models": ["ecmwf_ifs025_ensemble", "bom_access_global_ensemble"],
    "timezone": "Asia/Jayapura", "forecast_days": 3
}

try:
    res = fetch_multi_ensemble(lat, lon, params)
    server_placeholder.success("🟢 **Server:** AKTIF")
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # --- LOGIKA IDENTIFIKASI KOLOM YANG LEBIH AKURAT ---
    # Mencari kolom berdasarkan model dan parameter
    ec_prec = [c for c in df.columns if "precipitation" in c and "ecmwf" in c]
    ec_temp = [c for c in df.columns if "temperature_2m" in c and "ecmwf" in c]
    ec_rh   = [c for c in df.columns if "relative_humidity_2m" in c and "ecmwf" in c]
    ec_code = [c for c in df.columns if "weather_code" in c and "ecmwf" in c]

    bom_prec = [c for c in df.columns if "precipitation" in c and "bom" in c]
    bom_temp = [c for c in df.columns if "temperature_2m" in c and "bom" in c]
    bom_rh   = [c for c in df.columns if "relative_humidity_2m" in c and "bom" in c]
    bom_code = [c for c in df.columns if "weather_code" in c and "bom" in c]

    st.title("🛰️ Dashboard Multi-Model Ensemble")
    st.markdown(f"**Komparasi Eropa (ECMWF) & Australia (BOM)** | Sentani")

    # 5. Logika Periode Waktu
    pilihan_rentang = []
    urutan_waktu = [(0, 6, "DINI HARI"), (6, 12, "PAGI"), (12, 18, "SIANG"), (18, 24, "MALAM")]
    for i in range(2): 
        dt = (now_wit + timedelta(days=i)).date()
        for s, e, lbl in urutan_waktu:
            if dt == now_wit.date() and now_wit.hour >= e and now_wit.minute >= 5: continue
            pilihan_rentang.append((s, e, lbl, dt))

    # 6. Tampilkan Tabel
    for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
        df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
        if df_kat.empty: continue
        
        with st.expander(f"📅 {label} | {t_date.strftime('%d %B %Y')}", expanded=(idx<4)):
            # Statistik ECMWF (51 Members)
            prob_ec = (df_kat[ec_prec] > 0.1).sum(axis=1).mean() / 51 * 100
            max_ec = df_kat[ec_prec].max().sum()
            mean_temp_ec = df_kat[ec_temp].mean().mean()
            mean_rh_ec = df_kat[ec_rh].mean().mean()
            code_ec = df_kat[ec_code].mode(axis=1).iloc[0].mode()[0]

            # Statistik BOM (18 Members)
            prob_bom = (df_kat[bom_prec] > 0.1).sum(axis=1).mean() / 18 * 100
            max_bom = df_kat[bom_prec].max().sum()
            mean_temp_bom = df_kat[bom_temp].mean().mean()
            mean_rh_bom = df_kat[bom_rh].mean().mean()
            code_bom = df_kat[bom_code].mode(axis=1).iloc[0].mode()[0]

            data_tabel = {
                "Model": ["ECMWF (Eropa)", "BOM (Australia)"],
                "Kondisi": [get_weather_desc(code_ec), get_weather_desc(code_bom)],
                "Peluang Hujan": [f"{prob_ec:.0f}%", f"{prob_bom:.0f}%"],
                "Suhu / RH": [f"{mean_temp_ec:.1f}°C / {mean_rh_ec:.0f}%", f"{mean_temp_bom:.1f}°C / {mean_rh_bom:.0f}%"],
                "Skenario Terburuk": [f"{max_ec:.1f} mm", f"{max_bom:.1f} mm"]
            }
            st.table(pd.DataFrame(data_tabel))
            
            # Panel Peringatan Terpadu
            total_max = max(max_ec, max_bom)
            if total_max >= 5.0:
                st.warning(f"⚠️ **PERINGATAN DINI:** Salah satu model mendeteksi potensi hujan hingga {total_max:.1f} mm.")
            else:
                st.success(f"✅ **STATUS:** Kondisi cenderung aman. Skenario terburuk: {total_max:.1f} mm.")

except Exception as e:
    st.error(f"Gagal memuat data Multi-Model. Pastikan koneksi internet stabil. Error: {e}")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Multi-Model Consensus System | Stamet Sentani</div>", unsafe_allow_html=True)
