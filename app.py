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
    except: 
        return None

def tr_format(val):
    try:
        return "{:,.2f}".format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")
    except: 
        return str(val)

# --- TASARIM ---
st.set_page_config(page_title="Borsa Takip v25", layout="wide")

st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid #444444 !important;
        border-radius: 15px !important;
        padding: 20px !important;
    }
    div[data-testid="stMetricValue"] > div { color: #ffffff !important; font-size: 38px !important; font-weight: 800 !important; }
    div[data-testid="stMetricLabel"] > div > p { color: #cccccc !important; font-size: 14px !important; font-weight: bold !important; }
    h1, h2, h3, p, label, span { color: #ffffff !important; }
    .stDataFrame { background-color: #111111; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Portföy Yönetim Terminali")

client = get_client()
if not client: 
    st.error("Bağlantı Hatası!")
    st.stop()

# --- VERİ ÇEKME ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors='coerce').fillna(0)
except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- ÜST PANEL ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="🎁 TOPLAM HALKA ARZ KAR", value=f"{tr_format(ha_kar)} TL")
with col2:
    st.metric(label="📊 BORSA TOPLAM DURUM", value=f"{tr_format(nb_kar)} TL", 
              delta=f"{tr_format(nb_kar)} TL" if nb_kar != 0 else None)

# --- TABLOLAR VE GÜNCELLEME ---
st.write("---")
col_t1, col_t2 = st.columns([5, 1])
with col_t2:
    if st.button("🔄 Borsa Fiyatlarını Güncelle"):
        with st.spinner("Sadece .IS uzantılılar güncelleniyor..."):
            for index, row in df.iterrows():
                # Sadece sonunda .IS olanları API'den çeker
                if str(row['Hisse']).endswith(".IS"):
                    try:
                        ticker = row['Hisse']
                        data = yf.Ticker(ticker).history(period="1d")
                        if not data.empty:
                            yeni_fiyat = data['Close'].iloc[-1]
                            df.at[index, 'Satis'] = yeni_fiyat
                            df.at[index, 'Kar'] = (yeni_fiyat - row['Alis']) * row['Lot'] * row['Hesap']
                    except: continue
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.rerun()

tab1, tab2 = st.tabs(["💎 Halka Arzlarım", "📈 Borsa Takibi"])
with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ İşlem Merkezi")
    h_tur = st.radio("Kategori", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu (Örn: GENTS.IS veya BINHO)").upper().strip()
    
    anlik_fiyat = 0.0
    # Sadece .IS ile bitiyorsa otomatik fiyat getir
    if h_adi.endswith(".IS"):
        try:
            with st.spinner("API fiyatı alınıyor..."):
                hisse_data = yf.Ticker(h_adi).history(period="1d")
                if not hisse_data.empty:
                    anlik_fiyat = hisse_data['Close'].iloc[-1]
                    st.success(f"Güncel: {anlik_fiyat:.2f} TL")
        except:
            st.error("Fiyat çekilemedi.")

    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    
    # API'den fiyat geldiyse onu koy, gelmediyse (veya halka arzsa) manuel girişe bırak
    h_satis = st.number_input("Güncel/Satış Fiyatı", value=anlik_fiyat if anlik_fiyat > 0 else 0.0, format="%.2f")

    if st.button("🚀 Kaydet ve Yedekle"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("İşlem Başarılı!")
        st.rerun()

# --- SİLME ---
st.write("---")
sil_liste = df["Hisse"].tolist()
if sil_liste:
    s_sec = st.selectbox("Hisse Sil:", ["Seçiniz..."] + sil_liste)
    if s_sec != "Seçiniz..." and st.button("❌ Seçilen Kaydı Sil"):
        df = df[df["Hisse"] != s_sec]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()
