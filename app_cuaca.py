import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Ops Cuaca Sentani", layout="wide")

# LOGO SIDEBAR
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

st.title("🛰️ Dashboard Operasional Cuaca Sentani")
st.markdown("---")

tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)

# GUNAKAN KOORDINAT DARI KODE ANDA YANG BERHASIL
lat, lon = -2.5771, 140.5057

model_info = {
    "ecmwf_ifs": "Eropa", "gfs_seamless": "Amerika S.", "jma_seamless": "Jepang",
    "icon_seamless": "Jerman", "gem_seamless": "Kanada", "meteofrance_seamless": "Prancis",
    "ukmo_seamless": "Inggris"
}

# 3. Pengambilan Data
try:
    # Trik: Menggunakan Header browser agar tidak diblokir server
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Memanggil model satu per satu dalam string agar lebih stabil
    models_param = ",".join(model_info.keys())
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code,precipitation_probability,precipitation&models={models_param}&timezone=Asia%2FJayapura&forecast_days=3"
    
    res = requests.get(url, headers=headers).json()

    if "hourly" in res:
        df = pd.DataFrame(res["hourly"])
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

        st.sidebar.info(f"🕒 **Update:** {now_wit.strftime('%H:%M:%S')} WIT")

        # Logika Urutan Waktu
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
            
            # Buka 4 tabel pertama otomatis
            with st.expander(f"📅 {label} ({start_h:02d}-{end_h:02d}) | {t_date.strftime('%d %B %Y')}", expanded=(idx < 4)):
                data_tabel = []
                all_codes = []
                for m, negara in model_info.items():
                    # Validasi apakah kolom model ada
                    col_name = f"weather_code_{m}"
                    if col_name not in df.columns: continue
                    
                    code = df_kat[col_name].max()
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
                        "Suhu (°C)": f"{t_min:.1f}-{t_max:.1f}", 
                        "Lembap (%)": f"{safe_int(h_max)}%",
                        "Peluang Hujan": f"{safe_int(prob)}%", 
                        "Curah (mm)": round(np.nan_to_num(prec), 1),
                        "Angin (km/jam)": f"{w_spd:.1f} {degrees_to_direction(w_dir)}"
                    })
                
                st.table(pd.DataFrame(data_tabel))
                if all_codes:
                    st.warning(f"⚠️ **KESIMPULAN SKENARIO TERBURUK:** {get_weather_desc(max(all_codes))}")
    else:
        st.error("⚠️ Server API Open-Meteo menolak permintaan. Silakan tunggu 1 menit (Rate Limit) lalu refresh.")

except Exception as e:
    st.error(f"Gagal memproses data: {e}")

st.markdown("---")
st.caption("Copyright © 2026 Kedeng V | Stamet Sentani")
