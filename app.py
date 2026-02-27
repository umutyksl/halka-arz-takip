import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# --- GOOGLE SHEETS AYARLARI ---
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
    except: return str(val)

# --- TASARIM ---
st.set_page_config(page_title="Borsa Pro Terminal v12", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid='stMetricValue'] { color: #00ff41 !important; font-size: 50px !important; text-shadow: 0 0 10px #00ff41; }
    .stMetric { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 10px; padding: 20px; }
    h1, h2, h3, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME VE SÜTUN KONTROLÜ (KRİTİK BÖLGE) ---
sheet = client.open_by_key(SHEET_ID).sheet1
all_data = sheet.get_all_records()
df = pd.DataFrame(all_data)

# Eğer tablo boşsa veya "Tur" sütunu yoksa güvenli hale getir
if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
elif "Tur" not in df.columns:
    # ESKİ VERİLERİ KURTARMA: Eğer sütun yoksa ekle ve hepsini Halka Arz yap
    df["Tur"] = "Halka Arz"

# Sayısal alanları temizle
for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# --- CANLI FİYAT FONKSİYONU ---
def get_live_price(symbol, tur):
    if tur == "Normal Borsa" and symbol:
        try:
            ticker = symbol if "." in symbol else f"{symbol}.IS"
            info = yf.Ticker(ticker).fast_info
            return round(info['last_price'], 2)
        except: return None
    return None

# --- YAN MENÜ ---
with st.sidebar:
    st.header("🏢 İşlem Merkezi")
    h_tur = st.radio("Tür", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu (Örn: THYAO)").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot (Adet)", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    
    live_p = get_live_price(h_adi, h_tur)
    h_satis = st.number_input("Satış/Güncel Fiyat", value=live_p if live_p else 0.0, format="%.2f")
    
    if st.button("💾 Portföye Ekle"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("Kaydedildi!")
        st.rerun()

# --- ANA EKRAN ---
st.title("📟 Finansal Takip Terminali")

c1, c2 = st.columns(2)
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

with c1:
    st.metric("🎁 HALKA ARZ TOPLAM", f"{tr_format(ha_kar)} TL")
with c2:
    st.metric("📊 BORSA KAR/ZARAR", f"{tr_format(nb_kar)} TL", delta=f"{tr_format(nb_kar)} TL")

tab1, tab2 = st.tabs(["📁 Halka Arz Portföyü", "📈 Canlı Takip (Borsa)"])

with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

with tab2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

# --- SİLME BÖLGESİ ---
st.write("---")
st.subheader("🗑️ Kayıt Yönetimi")
sil_secenek = df["Hisse"].tolist()
if sil_secenek:
    col_d1, col_d2 = st.columns([3, 1])
    with col_d1:
        h_sil = st.selectbox("Silinecek Hisse:", sil_secenek)
    with col_d2:
        if st.button("❌ Seçileni Sil"):
            df = df[df["Hisse"] != h_sil]
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.rerun()
