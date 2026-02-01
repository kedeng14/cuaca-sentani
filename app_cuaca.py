import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Grand Multi-Ensemble Sentani", layout="wide")
st_autorefresh(interval=60000, key="fokus_periode_update")

# 2. Fungsi Fetch Data (Cache 1 jam)
@st.cache_data(ttl=3600)
def fetch_grand_ensemble(lat, lon, params):
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    res = requests.get(url, params=params).json()
    return res

def get_weather_desc(code, rain_val=0):
    if code is not None and not np.isnan(code):
        mapping = {
            0: "☀️ Cerah", 1: "🌤️ Cerah Berawan", 2: "⛅ Berawan", 3: "☁️ Mendung",
            45: "🌫️ Kabut", 51: "🌦️ Gerimis Rgn", 61: "🌧️ Hujan Ringan", 
            63: "🌧️ Hujan Sedang", 65: "🌧️ Hujan Lebat", 95: "⛈️ Badai Petir"
        }
        return mapping.get(int(code), f"Kode {int(code)}")
    return "🌧️ Hujan" if rain_val > 0.1 else "☁️ Mendung"

# 3. Parameter & Sidebar
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)
lat, lon = -2.575674, 140.518507

try:
    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2: st.image("bmkg.png", width=120)
    st.sidebar.markdown("---")
    st.sidebar.write(f"🕒 **Update:** {now_wit.strftime('%H:%M:%S')} WIT")
    server_placeholder = st.sidebar.empty()
    st.sidebar.info("**🔍 METODE ANALISIS:**\nMulti-Model Ensemble Consensus (5 Global Models)")
except:
    st.sidebar.warning("Logo BMKG tidak ditemukan")

# 4. Request API (5 Model Ensemble)
models_list = [
    "ecmwf_ifs025_ensemble", 
    "ncep_gefs025", 
    "ukmo_global_ensemble_20km", 
    "icon_global_eps", 
    "gem_global_ensemble"
]

params = {
    "latitude": lat, "longitude": lon,
    "hourly": ["precipitation", "weather_code"],
    "models": models_list,
    "timezone": "Asia/Jayapura", "forecast_days": 3
}

try:
    res = fetch_grand_ensemble(lat, lon, params)
    server_placeholder.success("🟢 **Server:** AKTIF")
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    st.title("🛰️ Grand Multi-Model Ensemble Dashboard")
    st.markdown(f"**Lokasi:** Stamet Sentani | Konsensus 5 Model Global")

    # 5. Logika Periode Waktu (H+5 Menit)
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
        
        with st.expander(f"📅 {label} | {t_date.strftime('%d %b %Y')}", expanded=(idx<4)):
            
            results = []
            all_max_prec = []
            
            for m in models_list:
                # Cari kolom untuk model ini
                m_prec_cols = [c for c in df.columns if m in c and "precipitation" in c]
                m_code_cols = [c for c in df.columns if m in c and "weather_code" in c]
                
                # Hitung Probabilitas (Threshold 0.5mm agar tidak overestimate)
                n_members = len(m_prec_cols)
                prob = (df_kat[m_prec_cols] > 0.5).sum(axis=1).mean() / n_members * 100
                max_p = df_kat[m_prec_cols].max().sum()
                all_max_prec.append(max_p)
                
                # Ambil Kode Cuaca (Jika ada)
                if m_code_cols:
                    code_val = df_kat[m_code_cols].mode(axis=1).iloc[0].mode()[0]
                    desc = get_weather_desc(code_val)
                else:
                    desc = get_weather_desc(None, max_p)
                
                results.append({
                    "Model": m.split('_')[0].upper(),
                    "Kondisi": desc,
                    "Prob. Hujan": f"{prob:.0f}%",
                    "Worst Case (mm)": round(max_p, 1)
                })
            
            st.table(pd.DataFrame(results))
            
            # --- ANALISIS KONSENSUS ---
            avg_max = sum(all_max_prec) / len(all_max_prec)
            if max(all_max_prec) >= 5.0:
                st.warning(f"⚠️ **WARNING:** Potensi hujan signifikan terdeteksi. Skenario terburuk rata-rata model: {avg_max:.1f} mm.")
            else:
                st.success(f"✅ **AMAN:** Konsensus model menunjukkan kondisi stabil.")

except Exception as e:
    st.error(f"Gagal memproses Grand Ensemble. Error: {e}")

st.sidebar.markdown("---")
st.sidebar.warning("**📢 DISCLAIMER**\nOutput model ini hanyalah panduan. Analisis streamline, MJO, dan data radar tetap menjadi prioritas utama forecaster.")
