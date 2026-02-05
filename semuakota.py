import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from collections import Counter

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Cuaca Smart System", layout="wide")

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

def analyze_consensus(conditions_list):
    """Menganalisis kekompakan model"""
    simplified_conds = []
    for c in conditions_list:
        if c == "N/A": continue
        if "Hujan" in c or "Gerimis" in c or "Badai" in c:
            simplified_conds.append("Hujan/Badai")
        elif "Mendung" in c or "Berawan" in c:
            simplified_conds.append("Berawan")
        else:
            simplified_conds.append("Cerah")
    
    if not simplified_conds: return "⚠️ Data tidak cukup untuk analisis", "warning"
    
    counts = Counter(simplified_conds)
    most_common, num = counts.most_common(1)[0]
    percentage = (num / len(simplified_conds)) * 100
    
    if percentage >= 70:
        return f"🟢 **Tinggi ({percentage:.0f}%)** - Model sangat kompak memprediksi {most_common}.", "success"
    elif percentage >= 40:
        return f"🟡 **Sedang ({percentage:.0f}%)** - Model cukup setuju pada kondisi {most_common}.", "info"
    else:
        return f"🔴 **Rendah ({percentage:.0f}%)** - Model berbeda pendapat. Cek Satelit & Radar!", "warning"

# --- SIDEBAR: LOGO, LOKASI & DISCLAIMER ---
try:
    col_logo1, col_logo2, col_logo3 = st.sidebar.columns([1, 2, 1])
    with col_logo2: st.image("bmkg.png", width=100)
except:
    st.sidebar.warning("Logo tidak ditemukan")

st.sidebar.markdown("---")
st.sidebar.subheader("🌍 Penentuan Lokasi")

lokasi_favorit = {
    "Sentani (Stamet)": [-2.5757, 140.5185, "Asia/Jayapura"],
    "Madiun (Kota)": [-7.6257, 111.5302, "Asia/Jakarta"],
    "Cari Lokasi Lain...": [None, None, None]
}

pilihan = st.sidebar.selectbox("Pilih Lokasi:", list(lokasi_favorit.keys()))

if pilihan == "Cari Lokasi Lain...":
    input_kota = st.sidebar.text_input("Ketik Nama Kota/Kecamatan:", placeholder="Contoh: Wamena")
    if input_kota:
        lat, lon, found_name, tz_pilihan = get_coordinates(input_kota)
        if lat: st.sidebar.success(f"📍 Ditemukan: {found_name}")
        else:
            st.sidebar.error("❌ Lokasi tidak ditemukan")
            lat, lon, tz_pilihan = -2.5757, 140.5185, "Asia/Jayapura"
    else:
        lat, lon, tz_pilihan = -2.5757, 140.5185, "Asia/Jayapura"
else:
    lat, lon, tz_pilihan = lokasi_favorit[pilihan]

tz_local = pytz.timezone(tz_pilihan)
now_local = datetime.now(tz_local)

st.sidebar.info(f"🕒 **Waktu Lokal:**\n{now_local.strftime('%d %b %Y %H:%M:%S')} {tz_pilihan}")

# --- REFERENSI FORECASTER ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Referensi Forecaster")
st.sidebar.link_button("🌐 MJO, Gel. Ekuator (OLR)", "https://ncics.org/pub/mjo/v2/map/olr.cfs.all.indonesia.1.png")
st.sidebar.link_button("🛰️ Streamline BMKG", "https://www.bmkg.go.id/#cuaca-iklim-5")
st.sidebar.link_button("🌀 Animasi Satelit (Live)", "http://202.90.198.22/IMAGE/ANIMASI/H08_EH_Region5_m18.gif")

# --- DISCLAIMER (SUDAH DIKEMBALIKAN) ---
st.sidebar.markdown("---")
st.sidebar.warning("""
**📢 DISCLAIMER:**
Data ini adalah luaran model numerik sebagai alat bantu diagnosa. 
    
Keputusan akhir berada pada **Analisis Forecaster** dengan mempertimbangkan parameter:
* Streamline & Isobar
* Indeks Global (MJO, IOD, ENSO)
* Kondisi Lokal & Satelit
""")

# --- HEADER DASHBOARD ---
st.title("🛰️ Dashboard Cuaca Smart Consensus System")
st.markdown(f"Analisis Multi-Model Global untuk **{pilihan if pilihan != 'Cari Lokasi Lain...' else found_name if 'found_name' in locals() else 'Sentani'}**")

# --- PETA ---
st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=12)
st.markdown("---")

# --- KONFIGURASI DATA ---
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
    "timezone": tz_pilihan,
    "forecast_days": 3
}

try:
    res = requests.get("https://api.open-meteo.com/v1/forecast", params=params).json()
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # --- TABEL PERIODE ---
    pilihan_rentang = []
    urutan_waktu = [(0, 6, "DINI HARI"), (6, 12, "PAGI"), (12, 18, "SIANG"), (18, 24, "MALAM")]

    for i in range(2): 
        date_target = (now_local + timedelta(days=i)).date()
        for start_h, end_h, label in urutan_waktu:
            if date_target == now_local.date():
                if now_local.hour < end_h: pilihan_rentang.append((start_h, end_h, label, date_target))
            else: pilihan_rentang.append((start_h, end_h, label, date_target))

    for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
        df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
        if df_kat.empty: continue
        
        with st.expander(f"📅 {label} ({start_h:02d}-{end_h:02d}) | {t_date.strftime('%d %B %Y')}", expanded=(idx < 4)):
            data_tabel = []
            conditions_for_analysis = []
            
            for m, negara in model_info.items():
                raw_code = df_kat[f"weather_code_{m}"].max()
                raw_prob = df_kat[f"precipitation_probability_{m}"].max()
                
                code_val = raw_code if not np.isnan(raw_code) else None
                prob_val = raw_prob if not np.isnan(raw_prob) else 0
                
                desc = get_weather_desc(code_val)
                conditions_for_analysis.append(desc)
                
                t_min = df_kat[f"temperature_2m_{m}"].min()
                t_max = df_kat[f"temperature_2m_{m}"].max()
                prec = df_kat[f"precipitation_{m}"].sum()
                w_spd = df_kat[f"wind_speed_10m_{m}"].mean()
                w_dir = df_kat[f"wind_direction_10m_{m}"].mean()

                data_tabel.append({
                    "Model": m.split('_')[0].upper(), 
                    "Asal": negara, 
                    "Kondisi": desc,
                    "Suhu (°C)": f"{t_min:.1f}-{t_max:.1f}" if not np.isnan(t_min) else "N/A", 
                    "Prob. Hujan": f"{int(prob_val)}%", 
                    "Curah (mm)": round(np.nan_to_num(prec), 1),
                    "Angin (km/jam)": f"{w_spd:.1f} {degrees_to_direction(w_dir)}" if not np.isnan(w_spd) else "N/A"
                })
            
            st.table(pd.DataFrame(data_tabel))
            
            consensus_msg, msg_type = analyze_consensus(conditions_for_analysis)
            if msg_type == "success": st.success(f"🤝 **Tingkat Kepastian:** {consensus_msg}")
            elif msg_type == "info": st.info(f"🤝 **Tingkat Kepastian:** {consensus_msg}")
            else: st.warning(f"🤝 **Tingkat Kepastian:** {consensus_msg}")

except Exception as e:
    st.error(f"⚠️ Terjadi gangguan data: {e}")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>© 2026 Kedeng V | Smart Weather Consensus System</div>", unsafe_allow_html=True)
