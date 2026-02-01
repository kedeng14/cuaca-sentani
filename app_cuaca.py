import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Ops Cuaca Sentani ENS", layout="wide")

# --- AUTO REFRESH SETIAP 1 MENIT (Hanya untuk update jam/tabel H+5) ---
st_autorefresh(interval=60000, key="fokus_periode_update")

# 2. Fungsi Pendukung & CACHE DATA (Tarik data setiap 1 jam agar aman)
@st.cache_data(ttl=3600)
def fetch_ensemble_data(lat, lon, params):
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    res = requests.get(url, params=params).json()
    return res

def get_weather_desc(code):
    if code is None or np.isnan(code): return "N/A"
    mapping = {
        0: "☀️ Cerah", 1: "🌤️ Cerah Berawan", 2: "⛅ Berawan", 3: "☁️ Mendung",
        45: "🌫️ Kabut", 51: "🌦️ Gerimis Rgn", 53: "🌦️ Gerimis Sdng", 55: "🌧️ Gerimis Pdt",
        61: "🌧️ Hujan Ringan", 63: "🌧️ Hujan Sedang", 65: "🌧️ Hujan Lebat",
        80: "🌦️ Hujan Lokal", 81: "🌧️ Hujan Lokal S", 82: "⛈️ Hujan Lokal L", 95: "⛈️ Badai Petir"
    }
    return mapping.get(int(code), f"Kode {int(code)}")

# 3. Sidebar dengan Logo BMKG
try:
    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2:
        st.image("bmkg.png", width=150)
except:
    st.sidebar.warning("File bmkg.png tidak ditemukan")

# 4. Zona Waktu & Parameter
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)
lat, lon = -2.5756744335142865, 140.5185071099937

st.title("🛰️ Dashboard ECMWF Ensemble (51 Members)")
st.markdown(f"**Lokasi:** Stamet Sentani | **Update:** {now_wit.strftime('%H:%M:%S')} WIT")

params = {
    "latitude": lat, "longitude": lon,
    "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "weather_code", "wind_speed_10m"],
    "models": "ecmwf_ifs025_ensemble",
    "timezone": "Asia/Jayapura", "forecast_days": 3
}

# 5. Pengambilan Data
try:
    res = fetch_ensemble_data(lat, lon, params)
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # Identifikasi kolom member
    prec_members = [c for c in df.columns if "precipitation_member" in c]
    code_members = [c for c in df.columns if "weather_code_member" in c]
    temp_members = [c for c in df.columns if "temperature_2m_member" in c]

    # --- GRAFIK SPREAD ENSEMBLE ---
    st.subheader("📊 Analisis Ketidakpastian Suhu (Spread)")
    df_chart = df.copy()
    df_chart['Mean'] = df[temp_members].mean(axis=1)
    df_chart['Min'] = df[temp_members].min(axis=1)
    df_chart['Max'] = df[temp_members].max(axis=1)
    st.line_chart(df_chart.set_index('time')[['Min', 'Mean', 'Max']].head(48))

    st.markdown("---")

    # 6. Logika Urutan Waktu (H+5 Menit)
    pilihan_rentang = []
    urutan_waktu = [(0, 6, "DINI HARI"), (6, 12, "PAGI"), (12, 18, "SIANG"), (18, 24, "MALAM")]

    for i in range(2): 
        date_target = (now_wit + timedelta(days=i)).date()
        for start_h, end_h, label in urutan_waktu:
            if date_target == now_wit.date():
                if now_wit.hour < end_h or (now_wit.hour == end_h and now_wit.minute < 5):
                    pilihan_rentang.append((start_h, end_h, label, date_target))
            else:
                pilihan_rentang.append((start_h, end_h, label, date_target))

    # 7. Tampilkan Tabel Operasional
    for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
        df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
        if df_kat.empty: continue
        
        is_expanded = idx < 4
        with st.expander(f"📅 {label} ({start_h:02d}-{end_h:02d}) | {t_date.strftime('%d %B %Y')}", expanded=is_expanded):
            
            # Hitung Statistik Ensemble untuk Tabel
            mean_temp = df_kat[temp_members].mean().mean()
            # Hitung modus kondisi (paling banyak muncul di antara 51 member)
            kondisi_dominan_code = df_kat[code_members].mode(axis=1).iloc[0].mode()[0]
            # Tingkat Kepercayaan: Persentase member yang setuju dengan kondisi dominan
            count_setuju = (df_kat[code_members] == kondisi_dominan_code).sum(axis=1).mean()
            confidence = (count_setuju / 51) * 100
            
            # Probabilitas Hujan (Member yang memprediksi hujan > 0.1mm)
            prob_hujan = (df_kat[prec_members] > 0.1).sum(axis=1).mean() / 51 * 100
            max_prec = df_kat[prec_members].max().sum() # Skenario terburuk akumulasi

            data_tabel = {
                "Parameter": ["Kondisi Dominan", "Tingkat Kepercayaan (Confidence)", "Peluang Hujan", "Suhu Rata-rata", "Skenario Terburuk (Curah)"],
                "Nilai Analisis": [
                    get_weather_desc(kondisi_dominan_code),
                    f"🎯 {confidence:.0f}%",
                    f"💧 {prob_hujan:.0f}%",
                    f"🌡️ {mean_temp:.1f} °C",
                    f"⚠️ {max_prec:.1f} mm"
                ]
            }
            
            st.table(pd.DataFrame(data_tabel))
            
            # Warning Skenario Terburuk
            worst_code = df_kat[code_members].max().max()
            if worst_code >= 61: # Jika ada simulasi hujan/badai
                st.warning(f"⚠️ **PERINGATAN DINI:** Simulasi terburuk mendeteksi potensi {get_weather_desc(worst_code)}")

except Exception as e:
    st.error(f"⚠️ Gangguan Data: {e}")

# 8. Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Copyright © 2026 Kedeng V | Ensemble ECMWF 0.25° (51 Members)</div>", unsafe_allow_html=True)
