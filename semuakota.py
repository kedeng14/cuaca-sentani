import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from collections import Counter
import folium
from streamlit_folium import st_folium

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Cuaca Smart System", layout="wide")

# --- FUNGSI PENDUKUNG ---
def get_coordinates(city_name):
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
    simplified_conds = []
    for c in conditions_list:
        if c == "N/A": continue
        if "Hujan" in c or "Gerimis" in c or "Badai" in c:
            simplified_conds.append("Hujan/Badai")
        elif "Mendung" in c or "Berawan" in c:
            simplified_conds.append("Berawan")
        else:
            simplified_conds.append("Cerah")
    
    if not simplified_conds: return "⚠️ Data tidak cukup", "warning"
    
    counts = Counter(simplified_conds)
    most_common, num = counts.most_common(1)[0]
    percentage = (num / len(simplified_conds)) * 100
    
    if percentage >= 70:
        return f"🟢 **Tinggi ({percentage:.0f}%)** - Model sangat kompak memprediksi {most_common}.", "success"
    elif percentage >= 40:
        return f"🟡 **Sedang ({percentage:.0f}%)** - Model cukup setuju pada kondisi {most_common}.", "info"
    else:
        return f"🔴 **Rendah ({percentage:.0f}%)** - Model berbeda pendapat. Wajib cek Satelit!", "warning"

# --- INISIALISASI SESSION STATE ---
if 'lat' not in st.session_state:
    st.session_state.lat = -2.5757
if 'lon' not in st.session_state:
    st.session_state.lon = 140.5185
if 'found_name' not in st.session_state:
    st.session_state.found_name = "Sentani (Stamet)"
if 'tz_pilihan' not in st.session_state:
    st.session_state.tz_pilihan = "Asia/Jayapura"

# --- SIDEBAR ---
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
        lat_res, lon_res, name_res, tz_res = get_coordinates(input_kota)
        if lat_res:
            if st.session_state.lat != lat_res or st.session_state.lon != lon_res:
                st.session_state.lat, st.session_state.lon = lat_res, lon_res
                st.session_state.found_name, st.session_state.tz_pilihan = name_res, tz_res
                st.rerun()
else:
    lat_fav, lon_fav, tz_fav = lokasi_favorit[pilihan]
    if st.session_state.lat != lat_fav or st.session_state.lon != lon_fav:
        st.session_state.lat, st.session_state.lon = lat_fav, lon_fav
        st.session_state.found_name, st.session_state.tz_pilihan = pilihan, tz_fav
        st.rerun()

lat, lon = st.session_state.lat, st.session_state.lon
found_name = st.session_state.found_name
tz_pilihan = st.session_state.tz_pilihan

tz_local = pytz.timezone(tz_pilihan)
now_local = datetime.now(tz_local)

st.sidebar.info(f"🕒 **Waktu Lokal:**\n{now_local.strftime('%d %b %Y %H:%M:%S')} {tz_pilihan}")

st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Referensi Forecaster")
st.sidebar.link_button("🌐 MJO, Gel. Ekuator (OLR)", "https://ncics.org/pub/mjo/v2/map/olr.cfs.all.indonesia.1.png")
st.sidebar.link_button("🛰️ Streamline BMKG", "https://www.bmkg.go.id/#cuaca-iklim-5")
st.sidebar.link_button("🌀 Animasi Satelit (Live)", "http://202.90.198.22/IMAGE/ANIMASI/H08_EH_Region5_m18.gif")

st.sidebar.markdown("---")
st.sidebar.warning("""**📢 DISCLAIMER:** Data ini adalah luaran model numerik. Keputusan akhir berada pada Analisis Forecaster.""")

# --- KONFIGURASI MODEL ---
model_info = {
    "ecmwf_ifs": "Eropa", "gfs_seamless": "Amerika S.", "jma_seamless": "Jepang",
    "icon_seamless": "Jerman", "gem_seamless": "Kanada", "meteofrance_seamless": "Prancis",
    "ukmo_seamless": "Inggris"
}

# --- HEADER & PETA (OPTIMASI KLIK) ---
st.title("🛰️ Dashboard Cuaca Smart Consensus System")
st.markdown(f"Analisis Multi-Model Global untuk **{found_name}**")

# Hitung warna pin dari konsensus real-time (singkat saja)
pin_color = "green"
try:
    res_p = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=weather_code&models=ecmwf_ifs&timezone={tz_pilihan}&forecast_days=1").json()
    code_p = res_p["hourly"]["weather_code_ecmwf_ifs"][0]
    if code_p >= 95: pin_color = "red"
    elif code_p >= 51: pin_color = "blue"
    elif code_p >= 1: pin_color = "orange"
except: pass

m = folium.Map(location=[lat, lon], zoom_start=12)
folium.Marker([lat, lon], icon=folium.Icon(color=pin_color, icon='info-sign')).add_to(m)

# Tampilkan peta (returned_objects kosong untuk performa, gunakan event klik saja)
map_output = st_folium(m, width="100%", height=350, key="main_map")

# Logika Klik yang Efisien
if map_output.get("last_clicked"):
    c_lat = map_output["last_clicked"]["lat"]
    c_lon = map_output["last_clicked"]["lng"]
    # Hanya rerun jika jarak klik signifikan (mencegah loop halus)
    if abs(c_lat - st.session_state.lat) > 0.001 or abs(c_lon - st.session_state.lon) > 0.001:
        st.session_state.lat = c_lat
        st.session_state.lon = c_lon
        st.session_state.found_name = f"Koordinat ({c_lat:.3f}, {c_lon:.3f})"
        st.rerun()

st.markdown("---")

# --- PENGAMBILAN DATA UTAMA ---
try:
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m", "weather_code", "precipitation_probability", "precipitation"],
        "models": list(model_info.keys()),
        "timezone": tz_pilihan, "forecast_days": 3
    }
    res = requests.get("https://api.open-meteo.com/v1/forecast", params=params).json()
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # --- GRAFIK ---
    st.subheader(f"📊 Tren Cuaca 48 Jam Ke Depan")
    col1, col2 = st.columns(2)
    with col1:
        temp_data = df[['time']].copy()
        temp_data['Suhu (°C)'] = df[[f"temperature_2m_{m}" for m in model_info.keys()]].mean(axis=1)
        st.line_chart(temp_data.set_index('time').head(48))
    with col2:
        prob_data = df[['time']].copy()
        prob_data['Peluang Hujan (%)'] = df[[f"precipitation_probability_{m}" for m in model_info.keys()]].max(axis=1)
        st.area_chart(prob_data.set_index('time').head(48))

    st.markdown("---")

    # --- TABEL ---
    urutan_waktu = [(0, 6, "DINI HARI"), (6, 12, "PAGI"), (12, 18, "SIANG"), (18, 24, "MALAM")]
    pilihan_rentang = []
    for i in range(2): 
        d = (now_local + timedelta(days=i)).date()
        for s, e, l in urutan_waktu:
            if d == now_local.date() and now_local.hour >= e: continue
            pilihan_rentang.append((s, e, l, d))

    for idx, (sh, eh, lb, td) in enumerate(pilihan_rentang):
        df_k = df[(df['time'].dt.date == td) & (df['time'].dt.hour >= sh) & (df['time'].dt.hour < eh)]
        if df_k.empty: continue
        with st.expander(f"📅 {lb} | {td.strftime('%d %b')}", expanded=(idx==0)):
            data_t = []
            cond_list = []
            for m, neg in model_info.items():
                rc = df_k[f"weather_code_{m}"].max()
                rp = df_k[f"precipitation_probability_{m}"].max()
                desc = get_weather_desc(rc if not np.isnan(rc) else None)
                cond_list.append(desc)
                data_t.append({
                    "Model": m.split('_')[0].upper(), "Asal": neg, "Kondisi": desc,
                    "Suhu": f"{df_k[f'temperature_2m_{m}'].min():.1f}-{df_k[f'temperature_2m_{m}'].max():.1f}",
                    "Prob": f"{int(np.nan_to_num(rp))}%",
                    "Curah": round(df_k[f"precipitation_{m}"].sum(), 1),
                    "Angin": f"{df_k[f'wind_speed_10m_{m}'].mean():.1f} {degrees_to_direction(df_k[f'wind_direction_10m_{m}'].mean())}"
                })
            st.table(pd.DataFrame(data_t))
            c_msg, c_type = analyze_consensus(cond_list)
            st.info(f"🤝 **Kepastian:** {c_msg}")

except Exception as e:
    st.error(f"⚠️ Error Data: {e}")

st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Copyright © 2026 Kedeng V | Stamet Sentani</div>", unsafe_allow_html=True)
