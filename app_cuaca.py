import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Ops Cuaca Sentani ENS", layout="wide")

# 2. Fungsi Pendukung
def get_weather_desc(code):
    if code is None or np.isnan(code): return "N/A"
    mapping = {
        0: "☀️ Cerah", 1: "🌤️ Cerah Berawan", 2: "⛅ Berawan", 3: "☁️ Mendung",
        45: "🌫️ Kabut", 51: "🌦️ Gerimis Rgn", 61: "🌧️ Hujan Ringan", 63: "🌧️ Hujan Sedang", 
        65: "🌧️ Hujan Lebat", 95: "⛈️ Badai Petir"
    }
    return mapping.get(int(code), f"Kode {int(code)}")

# 3. Header
st.title("🛰️ Dashboard ECMWF Ensemble (51 Members) - Sentani")
st.info("Menganalisis probabilitas cuaca berdasarkan 51 anggota simulasi model Eropa.")

# 4. Parameter API (Menggunakan Endpoint Ensemble)
lat, lon = -2.5757, 140.5185
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)

params = {
    "latitude": lat, "longitude": lon,
    "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "weather_code", "wind_speed_10m"],
    "models": "ecmwf_ifs025_ensemble",
    "timezone": "Asia/Jayapura",
    "forecast_days": 3
}

try:
    # Perhatikan: Endpoint ensemble berbeda dengan forecast biasa
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    res = requests.get(url, params=params).json()
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # --- LOGIKA PENGOLAHAN ENSEMBLE ---
    # Kita cari semua kolom yang mengandung kata 'member'
    temp_members = [c for c in df.columns if "temperature_2m_member" in c]
    prec_members = [c for c in df.columns if "precipitation_member" in c]
    code_members = [c for c in df.columns if "weather_code_member" in c]

    # Hitung Statistik untuk Tabel
    df['temp_mean'] = df[temp_members].mean(axis=1)
    df['temp_min'] = df[temp_members].min(axis=1)
    df['temp_max'] = df[temp_members].max(axis=1)
    df['prec_mean'] = df[prec_members].mean(axis=1)
    df['prec_max'] = df[prec_members].max(axis=1)
    # Probabilitas hujan: berapa persen member yang memprediksi hujan > 0.1mm
    df['rain_prob'] = (df[prec_members] > 0.1).sum(axis=1) / 51 * 100

    # 5. Grafik Ketidakpastian (Visualisasi Khas Ensemble)
    st.subheader("📊 Ensemble Spread (Rentang Ketidakpastian)")
    df_chart = df.set_index('time').head(48)
    st.line_chart(df_chart[['temp_min', 'temp_mean', 'temp_max']])
    st.caption("Garis atas/bawah menunjukkan rentang variasi dari 51 simulasi ECMWF.")

    # 6. Tabel Operasional per Periode
    pilihan_rentang = []
    urutan_waktu = [(0, 6, "DINI HARI"), (6, 12, "PAGI"), (12, 18, "SIANG"), (18, 24, "MALAM")]
    for i in range(2):
        date_target = (now_wit + timedelta(days=i)).date()
        for start_h, end_h, label in urutan_waktu:
            if date_target == now_wit.date() and now_wit.hour >= end_h: continue
            pilihan_rentang.append((start_h, end_h, label, date_target))

    for start_h, end_h, label, t_date in pilihan_rentang:
        df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
        if df_kat.empty: continue
        
        with st.expander(f"📅 {label} | {t_date.strftime('%d %b %Y')}", expanded=True):
            # Mengambil konsensus (mode) atau nilai terburuk
            worst_code = df_kat[code_members].max().max()
            
            summary_data = {
                "Parameter": ["Suhu (°C)", "Peluang Hujan (%)", "Estimasi Curah (mm)", "Kondisi Dominan"],
                "Nilai Rata-rata (Mean)": [
                    f"{df_kat['temp_mean'].mean():.1f}", 
                    f"{df_kat['rain_prob'].mean():.0f}%", 
                    f"{df_kat['prec_mean'].sum():.1f}", 
                    get_weather_desc(df_kat[code_members].mode().iloc[0].mode()[0])
                ],
                "Skenario Terburuk (Extreme)": [
                    f"Max: {df_kat['temp_max'].max():.1f}", 
                    f"Max Prob: {df_kat['rain_prob'].max():.0f}%", 
                    f"Max Total: {df_kat['prec_max'].sum():.1f}", 
                    get_weather_desc(worst_code)
                ]
            }
            st.table(pd.DataFrame(summary_data))

except Exception as e:
    st.error(f"Eror saat memproses Ensemble: {e}")
