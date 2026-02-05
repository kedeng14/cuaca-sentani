import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
from collections import Counter

# 1. Konfigurasi Halaman & CSS
st.set_page_config(page_title="Prakiraan Cuaca Sentani", layout="wide")

st.markdown("""
    <style>
            .block-container {
                 padding-top: 2.5rem; 
                 padding-bottom: 0rem;
                 padding-left: 5rem;
                 padding-right: 5rem;
             }
            .update-box {
                background-color: #1e3a5f;
                border-radius: 8px;
                padding: 10px;
                border-left: 4px solid #3b82f6;
                color: white;
                margin-bottom: 10px;
            }
            .update-title {
                font-weight: bold;
                color: #60a5fa;
                font-size: 0.85em;
                margin-bottom: 2px;
            }
            .update-time {
                font-size: 1.0em;
                font-weight: bold;
                color: #ffffff;
            }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=60000, key="fokus_periode_update")

# 2. Fungsi Fetch Data & Helper
@st.cache_data(ttl=3600)
def fetch_grand_ensemble(lat, lon, params):
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    res = requests.get(url, params=params).json()
    return res

def get_weather_desc(code, rain_val=0):
    if code is not None and not np.isnan(code):
        mapping = {
            0: "☀️ Cerah", 1: "🌤️ Cerah Berawan", 2: "⛅ Berawan", 3: "☁️ Mendung",
            45: "🌫️ Kabut", 48: "🌫️ Kabut Berembun",
            51: "🌦️ Gerimis Ringan", 53: "🌦️ Gerimis Sedang", 55: "🌧️ Gerimis Padat",
            61: "🌧️ Hujan Ringan", 63: "🌧️ Hujan Sedang", 65: "🌧️ Hujan Lebat",
            80: "🌦️ Hujan Lokal Rgn", 81: "🌧️ Hujan Lokal Sdng", 82: "⛈️ Hujan Lokal Lbt",
            95: "⛈️ Badai Petir"
        }
        return mapping.get(int(code), f"Kode {int(code)}")
    return "🌧️ Hujan" if rain_val > 0.1 else "☁️ Mendung"

def get_confidence(std_val):
    if std_val < 1.0: return "🟢 Tinggi"
    elif std_val < 2.5: return "🟡 Sedang"
    else: return "🔴 Rendah"

def get_consensus_level(conditions_list):
    keywords = []
    for desc in conditions_list:
        if "Hujan" in desc or "Gerimis" in desc: keywords.append("Hujan")
        elif "Badai" in desc: keywords.append("Badai")
        elif "Mendung" in desc or "Berawan" in desc: keywords.append("Berawan")
        else: keywords.append("Cerah")
    
    counts = Counter(keywords)
    max_agreement = counts.most_common(1)[0][1]
    
    if max_agreement >= 4: return "✅ KUAT (Model Kompak)", "blue"
    elif max_agreement == 3: return "⚠️ SEDANG (Cukup Setuju)", "orange"
    else: return "🚨 LEMAH (Berbeda Pendapat)", "red"

def degrees_to_direction(deg):
    if deg is None or np.isnan(deg): return "-"
    directions = ['U', 'TL', 'T', 'TG', 'S', 'BD', 'B', 'BL']
    idx = int((deg + 22.5) / 45) % 8
    return directions[idx]

# 3. Parameter & Sidebar
tz_wit = pytz.timezone('Asia/Jayapura')
now_wit = datetime.now(tz_wit)
lat, lon = -2.5756744335142865, 140.5185071099937

try:
    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2: st.image("bmkg.png", width=100)
    st.sidebar.markdown("---")
    
    server_placeholder = st.sidebar.empty()
    server_placeholder.success("🟢 **Server:** AKTIF")
    
    st.sidebar.markdown(f"""
        <div class="update-box">
            <div class="update-title">🕒 Update Terakhir: {now_wit.strftime('%d %b %Y')}</div>
            <div class="update-time">{now_wit.strftime('%H:%M:%S')} WIT</div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 Referensi Forecaster")
    st.sidebar.link_button("🌐 MJO, Gel. Ekuator (OLR)", "https://ncics.org/pub/mjo/v2/map/olr.cfs.all.indonesia.1.png")
    st.sidebar.link_button("🛰️ Streamline BMKG", "https://www.bmkg.go.id/#cuaca-iklim-5")
    st.sidebar.link_button("🌀 Animasi Satelit (Live)", "http://202.90.198.22/IMAGE/ANIMASI/H08_EH_Region5_m18.gif")

    st.sidebar.markdown("---")
    st.sidebar.warning("""
    **📢 DISCLAIMER:**
    Data ini adalah luaran model numerik sebagai alat bantu diagnosa. 
    
    Keputusan akhir berada pada **Analisis Forecaster** dengan mempertimbangkan parameter:
    * Streamline & Isobar
    * Indeks Global (MJO, IOD, ENSO)
    * Kondisi Lokal & Satelit
    """)
except:
    st.sidebar.warning("Logo tidak ditemukan")

# 4. Header Utama
st.markdown("<h1 style='text-align: center;'>🛰️ Dashboard Prakiraan Cuaca Stamet Sentani</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Multi-Model Ensemble Consensus System</h3>", unsafe_allow_html=True)

st.subheader("📍 Lokasi Titik Analisis")
map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
st.map(map_data, zoom=13)
st.caption(f"Titik Koordinat: {lat}, {lon}")
st.markdown("---")

# 5. Konfigurasi 5 Model Ensemble
model_info = {
    "ecmwf_ifs025_ensemble": "Uni Eropa",
    "ncep_gefs025": "Amerika Serikat",
    "ukmo_global_ensemble_20km": "Inggris Raya",
    "icon_global_eps": "Jerman",
    "gem_global_ensemble": "Kanada"
}
models_list = list(model_info.keys())

params = {
    "latitude": lat, "longitude": lon,
    "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m"],
    "models": models_list,
    "timezone": "Asia/Jayapura", "forecast_days": 3
}

try:
    res = fetch_grand_ensemble(lat, lon, params)
    df = pd.DataFrame(res["hourly"])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)

    # 6. Logika Periode Waktu
    pilihan_rentang = []
    urutan_waktu = [(0, 6, "DINI HARI"), (6, 12, "PAGI"), (12, 18, "SIANG"), (18, 24, "MALAM")]
    
    for i in range(2): 
        dt = (now_wit + timedelta(days=i)).date()
        for s, e, lbl in urutan_waktu:
            if dt == now_wit.date():
                if now_wit.hour < e or (now_wit.hour == e and now_wit.minute < 5):
                    pilihan_rentang.append((s, e, lbl, dt))
            else:
                pilihan_rentang.append((s, e, lbl, dt))

    # 7. Tampilkan Tabel
    for idx, (start_h, end_h, label, t_date) in enumerate(pilihan_rentang):
        df_kat = df[(df['time'].dt.date == t_date) & (df['time'].dt.hour >= start_h) & (df['time'].dt.hour < end_h)]
        if df_kat.empty: continue
        
        with st.expander(f"📅 {label} ({start_h:02d}:00-{end_h:02d}:00) | {t_date.strftime('%d %b %Y')}", expanded=(idx<4)):
            results = []
            all_max_prec = []
            
            for m in models_list:
                m_prec = [c for c in df.columns if m in c and "precipitation" in c]
                m_temp = [c for c in df.columns if m in c and "temperature_2m" in c]
                m_rh   = [c for c in df.columns if m in c and "relative_humidity_2m" in c]
                m_ws   = [c for c in df.columns if m in c and "wind_speed_10m" in c]
                m_wd   = [c for c in df.columns if m in c and "wind_direction_10m" in c]
                m_code = [c for c in df.columns if m in c and "weather_code" in c]
                
                # Confidence Internal (Internal Spread)
                std_temp = df_kat[m_temp].std(axis=1).mean()
                confidence = get_confidence(std_temp)

                # Probabilitas & Curah Maks (Anggota Terbasah)
                prob = (df_kat[m_prec] > 0.5).sum(axis=1).mean() / len(m_prec) * 100
                max_p = df_kat[m_prec].sum().max()
                all_max_prec.append(max_p)
                
                t_min, t_max = df_kat[m_temp].min().min(), df_kat[m_temp].max().max()
                rh_min, rh_max = df_kat[m_rh].min().min(), df_kat[m_rh].max().max()
                ws_mean = df_kat[m_ws].mean().mean()
                wd_mean = df_kat[m_wd].mean().mean()

                if m_code:
                    code_val = df_kat[m_code].mode(axis=1).iloc[0].mode()[0]
                    desc = get_weather_desc(code_val)
                else:
                    desc = get_weather_desc(None, max_p)
                
                results.append({
                    "Model": m.split('_')[0].upper(),
                    "Kondisi": desc,
                    "Kepastian": confidence,
                    "Suhu (°C)": f"{t_min:.1f}-{t_max:.1f}",
                    "RH (%)": f"{int(rh_min)}-{int(rh_max)}",
                    "Angin": f"{ws_mean:.1f} {degrees_to_direction(wd_mean)}",
                    "Prob. Hujan": f"{prob:.0f}%",
                    "Hujan (mm)": round(max_p, 1)
                })
            
            st.table(pd.DataFrame(results))
            
            # --- ANALISIS KONSENSUS ANTAR MODEL ---
            all_conds = [r["Kondisi"] for r in results]
            consensus_msg, consensus_clr = get_consensus_level(all_conds)
            st.markdown(f"**Analisis Konsensus Dunia:** :{consensus_clr}[{consensus_msg}]")
            
            total_max = max(all_max_prec)
            if total_max >= 5.0:
                st.warning(f"⚠️ **PERINGATAN DINI:** Potensi hujan terdeteksi. Estimasi maks: {total_max:.1f} mm.")
            else:
                st.success(f"✅ **AMAN:** Kondisi cenderung stabil. (Maks: {total_max:.1f} mm)")

except Exception as e:
    st.error(f"⚠️ Terjadi gangguan data: {e}")

# 8. Copyright & Footer
st.markdown("---")
st.markdown(f"""
    <div style='text-align: center; color: #888; font-size: 0.85em;'>
        <p>© 2026 <b>Kedeng V</b> | Stasiun Meteorologi Sentani</p>
        <p>Data Source: ECMWF, NCEP, UKMO, DWD, ECCC via Open-Meteo Ensemble API</p>
    </div>
""", unsafe_allow_html=True)
