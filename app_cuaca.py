import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Ops Cuaca Sentani Multi-ENS", layout="wide")

# --- AUTO REFRESH SETIAP 1 MENIT ---
st_autorefresh(interval=60000, key="fokus_periode_update")

# 2. Fungsi Pendukung & CACHE DATA
@st.cache_data(ttl=3600)
def fetch_multi_ensemble(lat, lon, params):
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    res = requests.get(url, params=params).json()
    return res

def get_weather_desc(code):
    if code is None or np.isnan(code): return "N/A"
    mapping = {
        0: "☀️ Cerah", 1: "🌤️ Cerah Berawan", 2: "⛅ Berawan", 3: "☁️ Mendung",
        45: "🌫️ Kabut", 51: "🌦️ Gerimis Rgn", 61: "🌧️ Hujan Ringan", 
        63: "🌧️ Hujan Sedang", 65: "🌧️ Hujan Lebat", 95: "⛈️ Badai Petir"
    }
    return mapping.get(int(code), f"Kode {int(code)}")

# 3. Parameter & Zona Waktu
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)
lat, lon = -2.5756744335142865, 140.5185071099937

# 4. Sidebar: Logo, Status, & Disclaimer
try:
    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2:
        st.image("bmkg.png", width=150)
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"🕒 **Update Terakhir:**\n{now_wit.strftime('%d %b %Y')}\n{now_wit.strftime('%H:%M:%S')} WIT")
    
    server_placeholder = st.sidebar.empty()

    st.sidebar.markdown("---")
    st.sidebar.warning("""
    **📢 DISCLAIMER**
    Data ini adalah luaran Multi-Model Ensemble (ECMWF & BOM). 
    Keputusan akhir berada pada **Analisis Forecaster** (MJO, Streamline, Satelit, dll).
    """)
except:
    st.sidebar.warning("Logo tidak ditemukan")

# 5. Header Dashboard
st.title("🛰️ Dashboard Multi-Model Ensemble (ECMWF & BOM)")
st.markdown(f"**Analisis Perbandingan Model Eropa vs Australia** | Sentani, Jayapura")

# Parameter memanggil dua model ensemble sekaligus
params = {
    "latitude": lat, "longitude": lon,
    "hourly": ["temperature_2m", "precipitation", "weather_code"],
    "models": ["ecmwf_ifs025_ensemble", "bom_access_global_ensemble"],
    "timezone": "Asia/Jayapura", "forecast_days": 3
}

# 6. Pengambilan Data
try:
    res = fetch_multi_ensemble(lat, lon, params)
    server_placeholder.success("🟢 **Server:** AKTIF")
    
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # Pisahkan kolom member masing-masing model
    ec_members = [c for c in df.columns if "ecmwf_ifs025_ensemble_precipitation_member" in c]
    bom_members = [c for c in df.columns if "bom_access_global_ensemble_precipitation_member" in c]
    
    # 7. Logika Urutan Waktu (H+5 Menit)
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

    # 8. Tampilkan Tabel Komparasi
    for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
        df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
        if df_kat.empty: continue
        
        with st.expander(f"📅 {label} ({start_h:02d}-{end_h:02d}) | {t_date.strftime('%d %B %Y')}", expanded=(idx < 4)):
            
            # Analisis ECMWF (51 Members)
            prob_ec = (df_kat[ec_members] > 0.1).sum(axis=1).mean() / 51 * 100
            max_ec = df_kat[ec_members].max().sum()
            
            # Analisis BOM (18 Members)
            prob_bom = (df_kat[bom_members] > 0.1).sum(axis=1).mean() / 18 * 100
            max_bom = df_kat[bom_members].max().sum()

            comp_data = {
                "Model Ensemble": ["ECMWF (Eropa)", "BOM (Australia)"],
                "Peluang Hujan": [f"💧 {prob_ec:.0f}%", f"💧 {prob_bom:.0f}%"],
                "Skenario Terburuk": [f"⚠️ {max_ec:.1f} mm", f"⚠️ {max_bom:.1f} mm"],
                "Status Konsensus": ["Cek bawah" if prob_ec > 50 else "Aman", "Cek bawah" if prob_bom > 50 else "Aman"]
            }
            st.table(pd.DataFrame(comp_data))
            
            # Panel Peringatan Gabungan
            total_max = max(max_ec, max_bom)
            if total_max >= 5.0:
                st.warning(f"⚠️ **PERINGATAN DINI:** Salah satu model mendeteksi potensi hujan hingga {total_max:.1f} mm. Mohon kroscek dengan data satelit!")
            else:
                st.success(f"✅ **STATUS:** Kedua model ensemble menunjukkan kondisi cenderung aman ({total_max:.1f} mm).")

except Exception as e:
    server_placeholder.error("🔴 **Server:** DISCONNECT")
    st.error(f"Gagal memuat data Multi-Model: {e}")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Multi-Model Consensus System | Stamet Sentani 2026</div>", unsafe_allow_html=True)
