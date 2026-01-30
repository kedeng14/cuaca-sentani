import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Ops Cuaca Sentani", layout="wide")

# TAMBAHAN LOGO DI SIDEBAR
try:
    # Menggunakan kolom di sidebar agar posisi logo lebih ke tengah
    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2:
        st.image("bmkg.png", width=150)
except:
    st.sidebar.warning("File bmkg.png tidak ditemukan di GitHub")

# 2. Fungsi Pendukung
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
        80: "🌦️ Hujan Lokal", 81: "🌧️ Hujan Lokal S", 82: "⛈️ Hujan Lokal L", 95: "⛈️ Badai Petir"
    }
    return mapping.get(int(code), f"Kode {int(code)}")

def degrees_to_direction(deg):
    if deg is None or np.isnan(deg): return "-"
    directions = ['U', 'TL', 'T', 'TG', 'S', 'BD', 'B', 'BL']
    idx = int((deg + 22.5) / 45) % 8
    return directions[idx]

# 3. Header Dashboard
st.title("🛰️ Dashboard Operasional Cuaca Stamet Sentani")
st.markdown("Analisis Komparasi 7 Model Global Real-Time")

# 4. Zona Waktu & Parameter Presisi
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)
lat, lon = -2.5756744335142865, 140.5185071099937

# 5. Bagian Peta Interaktif
st.subheader("📍 Lokasi Titik Analisis Presisi")
map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
st.map(map_data, zoom=13)
st.caption(f"Titik Koordinat: {lat}, {lon}")
st.markdown("---")

# 6. Konfigurasi Model
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
    "timezone": "Asia/Jayapura", "forecast_days": 3
}

# 7. Pengambilan Data & Visualisasi
try:
    res = requests.get("https://api.open-meteo.com/v1/forecast", params=params).json()
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # --- GRAFIK TREN CUACA DIHAPUS SESUAI PERINTAH ---
    
    st.sidebar.success(f"✅ Koneksi Server Stabil")
    st.sidebar.info(f"🕒 **Update Terakhir:**\n{now_wit.strftime('%d %b %Y')}\n{now_wit.strftime('%H:%M:%S')} WIT")
    
    # LOGIKA URUTAN WAKTU
    pilihan_rentang = []
    urutan_waktu = [
        (0, 6, "DINI HARI"),
        (6, 12, "PAGI"),
        (12, 18, "SIANG"),
        (18, 24, "MALAM")
    ]

    for i in range(2): 
        date_target = (now_wit + timedelta(days=i)).date()
        for start_h, end_h, label in urutan_waktu:
            if date_target == now_wit.date():
                if now_wit.hour < end_h:
                    pilihan_rentang.append((start_h, end_h, label, date_target))
            else:
                pilihan_rentang.append((start_h, end_h, label, date_target))

    # TAMPILKAN TABEL DENGAN 4 BLOK PERTAMA TERBUKA OTOMATIS
    for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
        df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
        if df_kat.empty: continue
        
        # Penentu expander: 4 tabel pertama (indeks 0, 1, 2, 3) akan terbuka otomatis
        is_expanded = idx < 4
        
        with st.expander(f"📅 {label} ({start_h:02d}-{end_h:02d}) | {t_date.strftime('%d %B %Y')}", expanded=is_expanded):
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
                    "Suhu (°C)": f"{t_min:.1f}-{t_max:.1f}" if not np.isnan(t_min) else "N/A", 
                    "Kelembaban (%)": f"{safe_int(h_min)}-{safe_int(h_max)}",
                    "Peluang Hujan": f"{safe_int(prob)}%", 
                    "Curah (mm)": round(np.nan_to_num(prec), 1),
                    "Angin (km/jam)": f"{w_spd:.1f} {degrees_to_direction(w_dir)}" if not np.isnan(w_spd) else "N/A"
                })
            
            st.table(pd.DataFrame(data_tabel))
            if all_codes:
                st.warning(f"⚠️ **KESIMPULAN SKENARIO TERBURUK:** {get_weather_desc(max(all_codes))}")

except Exception as e:
    st.error(f"⚠️ Terjadi gangguan koneksi data: {e}")

# 8. Footer Copyright
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
        Copyright © 2026 Kedeng V | Data sourced from Open-Meteo (ECMWF, GFS, JMA, ICON, GEM, METEOFRANCE, UKMO)
    </div>
    """, 
    unsafe_allow_html=True
)
