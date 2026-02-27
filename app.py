import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# --- GOOGLE BAĞLANTI AYARLARI ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_client():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scopes))
    except: return None

def tr_format(val):
    try:
        return "{:,.2f}".format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")
    except: return str(val)

# --- TASARIM (CSS GÜNCELLEMESİ) ---
st.set_page_config(page_title="Borsa Takip v32", layout="wide")

st.markdown("""
    <style>
    /* 1. KAZANÇ KUTULARI GENEL YAPISI */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 15px !important;
        padding: 20px !important;
        border: 1px solid #444444 !important; /* Varsayılan çerçeve */
        transition: all 0.3s ease;
    }

    /* 2. EĞER ZARAR VARSA (KIRMIZI YAP) */
    div[data-testid="stMetric"]:has(div[data-testid="stMetricDelta"] > div[data-trend="down"]) {
        border: 2px solid #ff4b4b !important;
    }
    div[data-testid="stMetric"]:has(div[data-testid="stMetricDelta"] > div[data-trend="down"]) div[data-testid="stMetricValue"] > div {
        color: #ff4b4b !important;
    }

    /* 3. EĞER KAR VARSA (YEŞİL YAP) */
    div[data-testid="stMetric"]:has(div[data-testid="stMetricDelta"] > div[data-trend="up"]) {
        border: 2px solid #09ab3b !important;
    }
    div[data-testid="stMetric"]:has(div[data-testid="stMetricDelta"] > div[data-trend="up"]) div[data-testid="stMetricValue"] > div {
        color: #09ab3b !important;
    }

    /* 4. RAKAMLAR VE ETİKETLER */
    div[data-testid="stMetricValue"] > div { font-size: 38px !important; font-weight: 800 !important; }
    div[data-testid="stMetricLabel"] > div > p { color: #cccccc !important; font-size: 14px !important; font-weight: bold !important; }
    
    h1, h2, h3, p, label, span { color: #ffffff !important; }
    .stDataFrame { background-color: #111111; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Portföy Yönetim Terminali")

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    expected_cols = ["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur", "Durum"]
    
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        for col in expected_cols:
            if col not in df.columns: df[col] = ""
        df = df[expected_cols]
    else:
        df = pd.DataFrame(columns=expected_cols)

    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(".", "").str.replace(",", "."), errors='coerce').fillna(0)
except Exception as e:
    st.error(f"Veri yükleme hatası: {e}")
    df = pd.DataFrame(columns=expected_cols)

# --- ÜST PANEL (METRİKLER) ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

col1, col2 = st.columns(2)
with col1:
    # Halka arz karı için delta ekledik (Renk tetiklenmesi için)
    st.metric(
        label="🎁 TOPLAM HALKA ARZ KAR", 
        value=f"{tr_format(ha_kar)} TL",
        delta=f"{tr_format(ha_kar)} TL" if ha_kar != 0 else None
    )
with col2:
    # Borsa durumu için delta zaten vardı
    st.metric(
        label="📊 BORSA TOPLAM DURUM", 
        value=f"{tr_format(nb_kar)} TL", 
        delta=f"{tr_format(nb_kar)} TL" if nb_kar != 0 else None
    )

# --- TABLOLAR VE GÜNCELLEME ---
st.write("---")
if st.button("🔄 Tüm Fiyatları API'den Güncelle"):
    with st.spinner("Borsa verileri tazeleniyor..."):
        for index, row in df.iterrows():
            clean_name = str(row['Hisse']).replace("#", "").strip()
            if str(row['Durum']) == "Aktif" and clean_name.endswith(".IS"):
                try:
                    data = yf.Ticker(clean_name).history(period="1d")
                    if not data.empty:
                        yeni_fiyat = data['Close'].iloc[-1]
                        df.at[index, 'Satis'] = yeni_fiyat
                        df.at[index, 'Kar'] = (yeni_fiyat - row['Alis']) * row['Lot'] * row['Hesap']
                except: continue
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("Fiyatlar Güncellendi!")
        st.rerun()

tab1, tab2 = st.tabs(["💎 Halka Arzlarım", "📈 Borsa Takibi"])
with tab1: st.dataframe(df[df["Tur"] == "Halka Arz"], use_container_width=True, hide_index=True)
with tab2: st.dataframe(df[df["Tur"] == "Normal Borsa"], use_container_width=True, hide_index=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ İşlem Merkezi")
    h_tur = st.radio("Kategori", ["Halka Arz", "Normal Borsa"])
    h_durum = st.selectbox("İşlem Durumu", ["Aktif", "Satıldı"])
    h_adi_raw = st.text_input("Hisse Kodu (Örn: GENTS.IS)").upper().strip()
    
    h_adi_clean = h_adi_raw.replace("#", "")
    anlik_fiyat = 0.0
    if h_adi_clean.endswith(".IS") and h_durum == "Aktif":
        try:
            h_data = yf.Ticker(h_adi_clean).history(period="1d")
            if not h_data.empty:
                anlik_fiyat = h_data['Close'].iloc[-1]
                st.success(f"Piyasa: {anlik_fiyat:.2f} TL")
        except: pass

    h_alis = st.number_input("Alış Fiyatı (Maliyet)", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    h_satis = st.number_input("Güncel / Satış Fiyatı", value=anlik_fiyat if anlik_fiyat > 0 else 0.0, format="%.2f")

    if st.button("🚀 Kaydet ve Yedekle"):
        if h_adi_raw == "":
            st.error("Hisse kodu boş olamaz!")
        else:
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
            yeni_veri = {
                "Hisse": h_adi_raw, "Alis": h_alis, "Satis": h_satis, 
                "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar, 
                "Tur": h_tur, "Durum": h_durum
            }
            df = pd.concat([df[df["Hisse"] != h_adi_raw], pd.DataFrame([yeni_veri])], ignore_index=True)
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.success("Başarıyla Senkronize Edildi!")
            st.rerun()

# --- SİLME ---
st.write("---")
sil_liste = df["Hisse"].tolist()
if sil_liste:
    s_sec = st.selectbox("Kayıt Sil:", ["Seçiniz..."] + sil_liste)
    if s_sec != "Seçiniz..." and st.button("❌ Sil"):
        df = df[df["Hisse"] != s_sec]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()
