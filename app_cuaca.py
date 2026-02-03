import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. Konfigurasi Halaman & CSS untuk Menarik Judul ke Atas
st.set_page_config(page_title="Prakiraan Cuaca Sentani", layout="wide")

# CSS untuk menghilangkan padding atas
st.markdown("""
    <style>
           .block-container {
                padding-top: 1rem;
                padding-bottom: 0rem;
                padding-left: 5rem;
                padding-right: 5rem;
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
    with col2: st.image("bmkg.png", width=120)
    st.sidebar.markdown("---")
    st.sidebar.write(f"🕒 **Update:** {now_wit.strftime('%H:%M:%S')} WIT")
    server_placeholder = st.sidebar.empty()
    
    st.sidebar.markdown("---")
    st.sidebar.warning("""
    **📢 DISCLAIMER:**
    Data ini adalah luaran model numerik (Ensemble) sebagai alat bantu diagnosa. 
    
    Keputusan akhir berada pada **Analisis Forecaster** dengan mempertimbangkan parameter:
    * Streamline & Divergensi
    * Indeks Global (MJO, IOD, ENSO)
    * Kondisi Lokal & Satelit
    """)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 Referensi Forecaster")
    st.sidebar.link_button("🌐 Monitoring MJO (OLR)", "https://ncics.org/pub/mjo/v2/map/olr.cfs.all.indonesia.1.png")
    st.sidebar.link_button("🛰️ Streamline BMKG", "https://www.bmkg.go.id/#cuaca-iklim-5")
    st.sidebar.link_button("🌀 Animasi Satelit (Live)", "http://202.90.198.22/IMAGE/ANIMASI/H08_EH_Region5_m18.gif")

except:
    st.sidebar.warning("Logo tidak ditemukan")

# 4. Header Utama (Sekarang Lebih Tinggi)
st.markdown("<h1 style='text-align: center; margin-top: -50px;'>Dashboard Prakiraan Cuaca Stamet Sentani</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555; margin-bottom: 20px;'>Multi-Model Ensemble Consensus System</h3>", unsafe_allow_html=True)

st.subheader("📍 Lokasi Titik Analisis Presisi")
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
    server_placeholder.success("🟢 **Server:** AKTIF")
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
                
                n_members = len(m_prec)
                prob = (df_kat[m_prec] > 0.5).sum(axis=1).mean() / n_members * 100
                
                # LOGIKA REALISTIS (ANGGOTA TERBASAH)
                total_hujan_per_member = df_kat[m_prec].sum() 
                max_p = total_hujan_per_member.max()
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
                    "Negara": model_info[m],
                    "Kondisi": desc,
                    "Suhu (°C)": f"{t_min:.1f}-{t_max:.1f}",
                    "RH (%)": f"{int(rh_min)}-{int(rh_max)}",
                    "Angin (km/jam)": f"{ws_mean:.1f} {degrees_to_direction(wd_mean)}",
                    "Prob. Hujan": f"{prob:.0f}%",
                    "Skenario Ekstrem (mm)": round(max_p, 1)
                })
            
            st.table(pd.DataFrame(results))
            
            total_max = max(all_max_prec)
            if total_max >= 5.0:
                st.warning(f"⚠️ **PERINGATAN DINI:** Potensi hujan terdeteksi. Skenario ekstrem: {total_max:.1f} mm.")
            else:
                st.success(f"✅ **AMAN:** Kondisi cenderung stabil. (Ekstrem Max: {total_max:.1f} mm)")

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
