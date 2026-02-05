import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Cuaca Multi-Lokasi", layout="wide")

# --- FUNGSI PENDUKUNG ---
def get_coordinates(city_name):
    """Mencari koordinat dan timezone otomatis berdasarkan nama kota"""
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=id&format=json"
        res = requests.get(url).json()
        if "results" in res:
            data = res["results"][0]
            return data["latitude"], data["longitude"], data["name"], data.get("timezone", "Asia/Jayapura")
        return None, None, None, None
    except:
        return None, None, None, None

def safe_int(val):
    try:
        if val is None or np.isnan(val): return 0
        return int(val)
    except: return 0

def get_weather_desc(code):
    if code is None or np.isnan(code): return "N/A"
    mapping = {
        0: "☀️ Cerah", 1: "🌤️ Cerah Berawan", 2: "⛅ Berawan", 3: "☁️ Mendung",
        45: "🌫️ Kabut", 51: "🌦️ Gerimis Rgn", 53: "🌦️ Gerimis Sdng", 55: "🌧️ Gerimis Pdt",
        61: "🌧️ Hujan Ringan", 63: "🌧️ Hujan Sedang", 65: "🌧️ Hujan Lebat",
        80: "🌦️ Hujan Lokal", 81: "🌧️ Hujan Lokal S", 82: "⛈️ Hujan Lokal L", 
        95: "⛈️ Badai Petir", 96: "⛈️ Badai Petir + Es", 99: "⛈️ Badai Petir Berat"
    }
    return mapping.get(int(code), f"Kode {int(code)}")

def degrees_to_direction(deg):
    if deg is None or np.isnan(deg): return "-"
    directions = ['U', 'TL', 'T', 'TG', 'S', 'BD', 'B', 'BL']
    idx = int((deg + 22.5) / 45) % 8
    return directions[idx]

# --- SIDEBAR: LOGO & PENCARIAN LOKASI ---
try:
    col_logo1, col_logo2, col_logo3 = st.sidebar.columns([1, 2, 1])
    with col_logo2:
        st.image("bmkg.png", width=100)
except:
    st.sidebar.warning("File bmkg.png tidak ditemukan")

st.sidebar.markdown("---")
st.sidebar.subheader("🌍 Penentuan Lokasi")

# Opsi Lokasi
lokasi_favorit = {
    "Sentani (Stamet)": [-2.5757, 140.5185, "Asia/Jayapura"],
    "Madiun (Kota)": [-7.6257, 111.5302, "Asia/Jakarta"],
    "Cari Lokasi Lain...": [None, None, None]
}

pilihan = st.sidebar.selectbox("Pilih Lokasi:", list(lokasi_favorit.keys()))

if pilihan == "Cari Lokasi Lain...":
    input_kota = st.sidebar.text_input("Ketik Nama Kota/Kecamatan:", placeholder="Contoh: Wamena atau Surabaya")
    if input_kota:
        lat, lon, found_name, tz_pilihan = get_coordinates(input_kota)
        if lat:
            st.sidebar.success(f"📍 Ditemukan: {found_name}")
        else:
            st.sidebar.error("❌ Lokasi tidak ditemukan")
            lat, lon, tz_pilihan = -2.5757, 140.5185, "Asia/Jayapura"
    else:
        lat, lon, tz_pilihan = -2.5757, 140.5185, "Asia/Jayapura"
else:
    lat, lon, tz_pilihan = lokasi_favorit[pilihan]

# Update Zona Waktu Dinamis
tz_local = pytz.timezone(tz_pilihan)
now_local = datetime.now(tz_local)

st.sidebar.info(f"🕒 **Waktu Lokal:**\n{now_local.strftime('%d %b %Y %H:%M:%S')} {tz_pilihan}")

st.sidebar.markdown("---")
st.sidebar.warning("""
**📢 DISCLAIMER:**
Keputusan akhir berada pada **Analisis Forecaster** dengan mempertimbangkan parameter:
* Streamline & Isobar
* Indeks Global (MJO, IOD, ENSO)
* Kondisi Lokal & Satelit
""")

# --- HEADER DASHBOARD ---
st.title("🛰️ Dashboard Operasional Cuaca Smart System")
st.markdown(f"Analisis Komparasi Model Global untuk **{pilihan if pilihan != 'Cari Lokasi Lain...' else input_kota}**")

# --- PETA LOKASI ---
st.subheader("📍 Lokasi Titik Analisis")
map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
st.map(map_data, zoom=12)
st.caption(f"Koordinat Terpilih: {lat}, {lon} | Zona Waktu: {tz_pilihan}")
st.markdown("---")

# --- KONFIGURASI MODEL & DATA ---
model_info = {
    "ecmwf_ifs": "Eropa", "gfs_seamless": "Amerika S.", "jma_seamless": "Jepang",
    "icon_seamless": "Jerman", "gem_seamless": "Kanada", "meteofrance_seamless": "Prancis",
    "ukmo_seamless": "Inggris"
}

params = {
    "latitude": lat, "longitude": lon,
    "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", 
               "wind_direction_10m", "weather_code", "precipitation_probability", "precipitation"],
    "models": list(model_info.keys()),
    "timezone": tz_pilihan, # Mengikuti Timezone Lokasi Terpilih
    "forecast_days": 3
}

try:
    res = requests.get("https://api.open-meteo.com/v1/forecast", params=params).json()
    df = pd.DataFrame(res["hourly"])
    # Membersihkan timezone untuk plotting agar tidak bentrok
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # --- GRAFIK TREN ---
    st.subheader(f"📊 Tren Cuaca 48 Jam Ke Depan ({tz_pilihan})")
    col_chart1, col_chart2 = st.columns(2)
    
    temp_cols = [f"temperature_2m_{m}" for m in model_info.keys()]
    df_temp_chart = df[['time']].copy()
    df_temp_chart['Suhu (°C)'] = df[temp_cols].mean(axis=1)
    
    prob_cols = [f"precipitation_probability_{m}" for m in model_info.keys()]
    df_prob_chart = df[['time']].copy()
    df_prob_chart['Peluang Hujan (%)'] = df[prob_cols].max(axis=1)

    with col_chart1:
        st.write("**Rata-rata Suhu Antar Model**")
        st.line_chart(df_temp_chart.set_index('time').head(48))

    with col_chart2:
        st.write("**Peluang Hujan Maksimum**")
        st.area_chart(df_prob_chart.set_index('time').head(48))
    
    st.markdown("---")
    
    # --- LOGIKA TABEL PERIODE ---
    pilihan_rentang = []
    urutan_waktu = [(0, 6, "DINI HARI"), (6, 12, "PAGI"), (12, 18, "SIANG"), (18, 24, "MALAM")]

    for i in range(2): 
        date_target = (now_local + timedelta(days=i)).date()
        for start_h, end_h, label in urutan_waktu:
            if date_target == now_local.date():
                if now_local.hour < end_h:
                    pilihan_rentang.append((start_h, end_h, label, date_target))
            else:
                pilihan_rentang.append((start_h, end_h, label, date_target))

    for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
        df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
        if df_kat.empty: continue
        
        with st.expander(f"📅 {label} ({start_h:02d}-{end_h:02d}) | {t_date.strftime('%d %B %Y')}", expanded=(idx < 4)):
            data_tabel = []
            all_codes = []
            for m, negara in model_info.items():
                code = df_kat[f"weather_code_{m}"].max()
                t_min, t_max = df_kat[f"temperature_2m_{m}"].min(), df_kat[f"temperature_2m_{m}"].max()
                h_min, h_max = df_kat[f"relative_humidity_2m_{m}"].min(), df_kat[f"relative_humidity_2m_{m}"].max()
                prob = df_kat[f"precipitation_probability_{m}"].max()
                prec = df_kat[f"precipitation_{m}"].sum()
                w_spd = df_kat[f"wind_speed_10m_{m}"].mean()
                w_dir = df_kat[f"wind_direction_10m_{m}"].mean()

                if not np.isnan(code): all_codes.append(code)
                data_tabel.append({
                    "Model": m.split('_')[0].upper(), 
                    "Asal": negara, 
                    "Kondisi": get_weather_desc(code),
                    "Suhu (°C)": f"{t_min:.1f}-{t_max:.1f}", 
                    "RH (%)": f"{safe_int(h_min)}-{safe_int(h_max)}",
                    "Prob. Hujan": f"{safe_int(prob)}%", 
                    "Curah (mm)": round(np.nan_to_num(prec), 1),
                    "Angin (km/jam)": f"{w_spd:.1f} {degrees_to_direction(w_dir)}"
                })
            
            st.table(pd.DataFrame(data_tabel))
            if all_codes:
                st.warning(f"⚠️ **KESIMPULAN SKENARIO TERBURUK:** {get_weather_desc(max(all_codes))}")

except Exception as e:
    st.error(f"⚠️ Gangguan data atau lokasi tidak dikenal: {e}")

# 8. Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Copyright © 2026 Kedeng V | Data sourced from Open-Meteo Global Models</div>", unsafe_allow_html=True)
