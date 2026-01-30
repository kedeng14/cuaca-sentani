import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Ops Cuaca Sentani", layout="wide")

# LOGO DI SIDEBAR
try:
    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2:
        st.image("bmkg.png", width=150)
except:
    st.sidebar.warning("Logo tidak ditemukan")

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

# 3. Header
st.title("🛰️ Dashboard Operasional Cuaca Stamet Sentani")
st.markdown("Analisis Komparasi 7 Model Global Real-Time")

# 4. Parameter (Koordinat Sentani)
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)
lat, lon = -2.57, 140.51 # Koordinat disederhanakan agar API lebih cepat merespon

# 5. Peta
st.subheader("📍 Lokasi Titik Analisis")
map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
st.map(map_data, zoom=12)
st.markdown("---")

# 6. Konfigurasi Model (Update ke mode Best Match/Seamless)
model_info = {
    "ecmwf_ifs": "Eropa", "gfs_seamless": "Amerika", "jma_seamless": "Jepang",
    "icon_seamless": "Jerman", "gem_seamless": "Kanada", "meteofrance_seamless": "Prancis",
    "ukmo_seamless": "Inggris"
}

params = {
    "latitude": lat, "longitude": lon,
    "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", 
               "wind_direction_10m", "weather_code", "precipitation_probability", "precipitation"],
    "models": ",".join(model_info.keys()), # Memperbaiki format pemanggilan API
    "timezone": "Asia/Jayapura",
    "forecast_days": 3
}

# 7. Pengambilan Data
try:
    # Menambahkan timeout agar tidak loading selamanya
    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
    res = response.json()

    if "hourly" in res:
        df = pd.DataFrame(res["hourly"])
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

        # --- GRAFIK ---
        st.subheader("📊 Grafik Tren Cuaca (48 Jam Ke Depan)")
        col_chart1, col_chart2 = st.columns(2)
        
        temp_cols = [f"temperature_2m_{m}" for m in model_info.keys() if f"temperature_2m_{m}" in df.columns]
        if temp_cols:
            df_temp = df[['time']].copy()
            df_temp['Suhu'] = df[temp_cols].mean(axis=1)
            with col_chart1:
                st.write("**Suhu (°C)**")
                st.line_chart(df_temp.set_index('time').head(48))

        prob_cols = [f"precipitation_probability_{m}" for m in model_info.keys() if f"precipitation_probability_{m}" in df.columns]
        if prob_cols:
            df_prob = df[['time']].copy()
            df_prob['Hujan'] = df[prob_cols].max(axis=1)
            with col_chart2:
                st.write("**Peluang Hujan (%)**")
                st.area_chart(df_prob.set_index('time').head(48))
        
        st.markdown("---")

        # Sidebar Status
        st.sidebar.success("✅ Server Terhubung")
        st.sidebar.info(f"🕒 WIT: {now_wit.strftime('%H:%M:%S')}")
        
        # Logika Tabel
        pilihan_rentang = []
        urutan_waktu = [(0, 6, "DINI HARI"), (6, 12, "PAGI"), (12, 18, "SIANG"), (18, 24, "MALAM")]

        for i in range(2): 
            date_target = (now_wit + timedelta(days=i)).date()
            for start_h, end_h, label in urutan_waktu:
                if date_target == now_wit.date():
                    if now_wit.hour < end_h:
                        pilihan_rentang.append((start_h, end_h, label, date_target))
                else:
                    pilihan_rentang.append((start_h, end_h, label, date_target))

        # Tampilkan 4 tabel pertama terbuka
        for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
            df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
            if df_kat.empty: continue
            
            with st.expander(f"📅 {label} ({start_h:02d}-{end_h:02d}) | {t_date.strftime('%d %b %Y')}", expanded=(idx < 4)):
                data_tabel = []
                all_codes = []
                for m, negara in model_info.items():
                    col_code = f"weather_code_{m}"
                    if col_code not in df.columns: continue
                    
                    code = df_kat[col_code].max()
                    t_min = df_kat[f"temperature_2m_{m}"].min()
                    t_max = df_kat[f"temperature_2m_{m}"].max()
                    h_max = df_kat[f"relative_humidity_2m_{m}"].max()
                    prob = df_kat[f"precipitation_probability_{m}"].max()
                    prec = df_kat[f"precipitation_{m}"].sum()
                    w_spd = df_kat[f"wind_speed_10m_{m}"].mean()
                    w_dir = df_kat[f"wind_direction_10m_{m}"].mean()

                    if not np.isnan(code): all_codes.append(code)
                    data_tabel.append({
                        "Model": m.split('_')[0].upper(), 
                        "Asal": negara, 
                        "Kondisi": get_weather_desc(code),
                        "Suhu": f"{t_min:.1f}-{t_max:.1f}", 
                        "Lembap": f"{safe_int(h_max)}%",
                        "Hujan": f"{safe_int(prob)}%", 
                        "Curah": f"{prec:.1f}mm",
                        "Angin": f"{w_spd:.1f} {degrees_to_direction(w_dir)}"
                    })
                
                if data_tabel:
                    st.table(pd.DataFrame(data_tabel))
                    if all_codes:
                        st.warning(f"⚠️ Kesimpulan: {get_weather_desc(max(all_codes))}")
    else:
        st.error("⚠️ Data belum tersedia. Server sedang proses update data global (biasanya 1-2 menit).")
        st.button("Coba Update Sekarang")

except Exception as e:
    st.error(f"⚠️ Gangguan: {e}")

st.markdown("---")
st.caption("Copyright © 2026 Kedeng V | Stamet Sentani")
