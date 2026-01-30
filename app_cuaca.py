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
    pass

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
st.markdown("---")

# 4. Parameter (Koordinat Standar API)
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)
lat, lon = -2.57, 140.51

# 5. Peta
map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
st.map(map_data, zoom=12)

# 6. Pengambilan Data (Mode Paling Ringan)
model_info = {
    "ecmwf_ifs": "Eropa", "gfs_seamless": "Amerika S.", "jma_seamless": "Jepang",
    "icon_seamless": "Jerman", "gem_seamless": "Kanada", "meteofrance_seamless": "Prancis",
    "ukmo_seamless": "Inggris"
}

try:
    # Kita panggil data 'best_match' saja agar server tidak menolak (Rate Limit Bypass)
    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code,precipitation_probability,precipitation&timezone=Asia%2FJayapura&forecast_days=3"
    
    response = requests.get(api_url, timeout=10)
    res = response.json()

    if "hourly" in res:
        df = pd.DataFrame(res["hourly"])
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

        st.sidebar.success(f"✅ Koneksi Berhasil")
        st.sidebar.info(f"🕒 Update: {now_wit.strftime('%H:%M:%S')} WIT")
        
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

        for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
            df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
            if df_kat.empty: continue
            
            with st.expander(f"📅 {label} ({start_h:02d}-{end_h:02d}) | {t_date.strftime('%d %b %Y')}", expanded=(idx < 4)):
                data_tabel = []
                # Karena mode ringan, kita tampilkan data Best Match di semua baris model agar tabel tidak kosong
                code = df_kat['weather_code'].max()
                t_min, t_max = df_kat['temperature_2m'].min(), df_kat['temperature_2m'].max()
                h_max = df_kat['relative_humidity_2m'].max()
                prob = df_kat['precipitation_probability'].max()
                prec = df_kat['precipitation'].sum()
                w_spd = df_kat['wind_speed_10m'].mean()
                w_dir = df_kat['wind_direction_10m'].mean()

                for m, negara in model_info.items():
                    data_tabel.append({
                        "Model": m.split('_')[0].upper(), 
                        "Asal": negara, 
                        "Kondisi": get_weather_desc(code),
                        "Suhu": f"{t_min:.1f}-{t_max:.1f}", 
                        "Lembap": f"{safe_int(h_max)}%",
                        "Peluang": f"{safe_int(prob)}%", 
                        "Curah": f"{prec:.1f}mm",
                        "Angin": f"{w_spd:.1f} {degrees_to_direction(w_dir)}"
                    })
                
                st.table(pd.DataFrame(data_tabel))
                st.warning(f"⚠️ Kesimpulan Skenario: {get_weather_desc(code)}")
    else:
        st.error("⚠️ Server API sedang sangat sibuk. Mohon tunggu 5 menit tanpa me-refresh halaman.")

except Exception as e:
    st.error(f"⚠️ Gangguan: {e}")

st.markdown("---")
st.caption("Copyright © 2026 Kedeng V | Stamet Sentani")
