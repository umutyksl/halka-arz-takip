import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import time  # Kota hatalarını önlemek için eklendi

# --- GOOGLE BAĞLANTI AYARLARI ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

# --- E-POSTA ADRESİNİ BULMA KODU (GEÇİCİ) ---
import streamlit as st
if "gcp_service_account" in st.secrets:
    mail = st.secrets["gcp_service_account"]["client_email"]
    st.error(f"Kopyalaman gereken e-posta: {mail}")
else:
    st.warning("Secrets içinde 'gcp_service_account' bulunamadı!")
# -------------------------------------------

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

# --- VERİ YAZMA FONKSİYONU (HATA ÖNLEYİCİ) ---
def update_google_sheet(sheet, dataframe):
    """Veriyi Google Sheets'e güvenli bir şekilde yazar."""
    try:
        # Sayısal değerleri string'e çevirerek API hatalarını önle
        df_to_upload = dataframe.copy()
        for col in df_to_upload.columns:
            df_to_upload[col] = df_to_upload[col].astype(str)
            
        data_list = [df_to_upload.columns.values.tolist()] + df_to_upload.values.tolist()
        
        sheet.clear()
        time.sleep(0.5) # API'nin nefes alması için kısa bir bekleme
        # Yeni gspread versiyonları için doğru kullanım:
        sheet.update(range_name='A1', values=data_list, value_input_option='RAW')
        return True
    except Exception as e:
        st.error(f"Google Sheets Güncelleme Hatası: {e}")
        return False

# --- TASARIM (DEĞİŞTİRİLMEDİ) ---
st.set_page_config(page_title="Borsa Takip v34", layout="wide")

st.markdown("""
    <style>
    div[data-testid="stMetric"] { background-color: rgba(255, 255, 255, 0.05) !important; border-radius: 15px !important; padding: 20px !important; transition: all 0.3s ease; }
    div[data-testid="stMetric"]:has(div[data-testid="stMetricValue"]:contains("-")) { border: 2px solid #ff4b4b !important; }
    div[data-testid="stMetric"]:has(div[data-testid="stMetricValue"]:contains("-")) div[data-testid="stMetricValue"] > div { color: #ff4b4b !important; }
    div[data-testid="stMetric"]:not(:has(div[data-testid="stMetricValue"]:contains("-"))) { border: 2px solid #09ab3b !important; }
    div[data-testid="stMetric"]:not(:has(div[data-testid="stMetricValue"]:contains("-"))) div[data-testid="stMetricValue"] > div { color: #09ab3b !important; }
    div[data-testid="stMetricValue"] > div { font-size: 38px !important; font-weight: 800 !important; }
    div[data-testid="stMetricLabel"] > div > p { color: #cccccc !important; font-size: 14px !important; font-weight: bold !important; }
    h1, h2, h3, p, label, span { color: #ffffff !important; }
    .stDataFrame { background-color: #111111; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Portföy Yönetim Terminali")

client = get_client()
# --- ŞU SATIRI EKLE ---
st.info(f"Lütfen bu adresi Google Sheet'ten 'Düzenleyici' olarak ekle: {dict(st.secrets['gcp_service_account']).get('client_email')}")
# ----------------------
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
        # Verileri temizle ve sayıya çevir
        df[col] = df[col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
except Exception as e:
    st.error(f"Veri yükleme hatası: {e}")
    df = pd.DataFrame(columns=expected_cols)

# --- ÜST PANEL ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="🎁 TOPLAM HALKA ARZ KAR", value=f"{tr_format(ha_kar)} TL")
with col2:
    st.metric(label="📊 BORSA TOPLAM DURUM", value=f"{tr_format(nb_kar)} TL")

# --- TABLOLAR VE API GÜNCELLEME ---
st.write("---")
if st.button("🔄 Tüm Fiyatları API'den Güncelle"):
    with st.spinner("Güncelleniyor..."):
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
        if update_google_sheet(sheet, df):
            st.success("Tüm fiyatlar güncellendi!")
            st.rerun()

tab1, tab2 = st.tabs(["💎 Halka Arzlarım", "📈 Borsa Takibi"])
with tab1: st.dataframe(df[df["Tur"] == "Halka Arz"], use_container_width=True, hide_index=True)
with tab2: st.dataframe(df[df["Tur"] == "Normal Borsa"], use_container_width=True, hide_index=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ İşlem Merkezi")
    h_tur = st.radio("Kategori", ["Halka Arz", "Normal Borsa"])
    h_durum = st.selectbox("İşlem Durumu", ["Aktif", "Satıldı"])
    h_adi_raw = st.text_input("Hisse Kodu (Örn: THYAO.IS)").upper().strip()
    
    h_adi_clean = h_adi_raw.replace("#", "")
    anlik_fiyat = 0.0
    if h_adi_clean.endswith(".IS") and h_durum == "Aktif":
        try:
            h_data = yf.Ticker(h_adi_clean).history(period="1d")
            if not h_data.empty:
                anlik_fiyat = h_data['Close'].iloc[-1]
                st.success(f"Anlık: {anlik_fiyat:.2f}")
        except: pass

    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4, 5, 10], index=0)
    h_satis = st.number_input("Güncel / Satış Fiyatı", value=anlik_fiyat if anlik_fiyat > 0 else 0.0, format="%.2f")

    if st.button("🚀 Kaydet ve Yedekle"):
        if h_adi_raw != "":
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
            yeni_veri = {"Hisse": h_adi_raw, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar, "Tur": h_tur, "Durum": h_durum}
            
            # Eski kaydı varsa sil, yenisini ekle
            df = pd.concat([df[df["Hisse"] != h_adi_raw], pd.DataFrame([yeni_veri])], ignore_index=True)
            
            if update_google_sheet(sheet, df):
                st.rerun()

# --- SİLME ---
st.write("---")
sil_liste = df["Hisse"].tolist()
if sil_liste:
    s_sec = st.selectbox("Hisse Sil:", ["Seçiniz..."] + sil_liste)
    if s_sec != "Seçiniz..." and st.button("❌ Kaydı Sil"):
        df = df[df["Hisse"] != s_sec]
        if update_google_sheet(sheet, df):
            st.rerun()
