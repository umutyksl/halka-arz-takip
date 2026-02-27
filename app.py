import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf # Canlı fiyat için gerekli

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

# --- TASARIM (Siyah Arkaplan & Yeşil Kazanç) ---
st.set_page_config(page_title="Borsa Pro Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid='stMetricValue'] { color: #00ff41 !important; font-size: 50px !important; text-shadow: 0 0 10px #00ff41; }
    .stMetric { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 10px; padding: 20px; }
    .stDataFrame { background-color: #161b22; }
    h1, h2, h3, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

client = get_client()
if not client: st.stop()

# --- VERİ İŞLEME ---
sheet = client.open_by_key(SHEET_ID).sheet1
all_data = sheet.get_all_records()
df = pd.DataFrame(all_data)

if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- CANLI FİYAT GÜNCELLEME SİSTEMİ ---
def get_live_price(symbol, tur):
    if tur == "Normal Borsa":
        try:
            # Hisse kodu sonuna .IS eklenmemişse ekle (BIST için)
            ticker = symbol if "." in symbol else f"{symbol}.IS"
            price = yf.Ticker(ticker).fast_info['last_price']
            return round(price, 2)
        except:
            return None
    return None

# --- YAN MENÜ ---
with st.sidebar:
    st.header("🏢 İşlem Merkezi")
    h_tur = st.radio("Tür", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu (Örn: THYAO)").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot (Adet)", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    
    # Canlı Fiyat Kontrolü
    live_p = get_live_price(h_adi, h_tur)
    h_satis = st.number_input("Satış/Güncel Fiyat", value=live_p if live_p else 0.0, format="%.2f")
    
    if st.button("💾 Portföye Ekle"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()

# --- ANA EKRAN ---
st.title("📟 Finansal Takip Terminali")

c1, c2 = st.columns(2)
ha_kar = pd.to_numeric(df[df["Tur"] == "Halka Arz"]["Kar"]).sum()
nb_kar = pd.to_numeric(df[df["Tur"] == "Normal Borsa"]["Kar"]).sum()

with c1:
    st.metric("🎁 HALKA ARZ TOPLAM", f"{tr_format(ha_kar)} TL")
with c2:
    st.metric("📊 BORSA KAR/ZARAR", f"{tr_format(nb_kar)} TL", delta=f"{tr_format(nb_kar)} TL")

tab1, tab2 = st.tabs(["📁 Halka Arz Portföyü", "📈 Canlı Takip (Borsa)"])

with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"], use_container_width=True, hide_index=True)

with tab2:
    st.write("Not: Normal borsa hisselerinde kâr durumu anlık fiyata göre hesaplanır.")
    st.dataframe(df[df["Tur"] == "Normal Borsa"], use_container_width=True, hide_index=True)

# --- SİLME BÖLGESİ (GERİ GELDİ) ---
st.write("---")
st.subheader("🗑️ Kayıt Yönetimi")
col_del1, col_del2 = st.columns([3, 1])
with col_del1:
    sil_secenek = df["Hisse"].tolist()
    if sil_secenek:
        hisse_to_delete = st.selectbox("Silmek istediğiniz hisseyi seçin:", sil_secenek)
with col_del2:
    if st.button("❌ Seçileni Sil"):
        df = df[df["Hisse"] != hisse_to_delete]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("Silindi!")
        st.rerun()

if st.button("🚨 Verileri Tamamen Temizle"):
    sheet.clear()
    sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
    st.rerun()
