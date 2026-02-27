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

# --- TASARIM (SADE YEŞİL/KIRMIZI & SİYAH TEMA) ---
st.set_page_config(page_title="Borsa Portföy v13", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0d11; color: #e1e1e1; }
    /* Metrik kutuları ve renkleri */
    [data-testid='stMetricValue'] { font-size: 45px !important; font-weight: bold !important; }
    .stMetric { background-color: #1a1d23 !important; border: 1px solid #2d3139 !important; border-radius: 12px; padding: 20px; }
    
    /* Pozitif Kar (Yeşil) - Parlama yok */
    [data-testid='stMetricValue'] { color: #00c853 !important; }
    
    /* Negatif Zarar Durumu için alt yazı rengi */
    [data-testid='stMetricDelta'] > div { color: #ff1744 !important; }
    
    h1, h2, h3, p, span { color: white !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0b0d11; }
    </style>
    """, unsafe_allow_html=True)

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME VE AKILLI TEMİZLİK ---
sheet = client.open_by_key(SHEET_ID).sheet1
all_data = sheet.get_all_records()
df = pd.DataFrame(all_data)

if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
else:
    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"
    
    # Sayısal alanları temizle
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = df[col].astype(str).str.replace(".", "").str.replace(",", ".")
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # ⚠️ 760 BİN TL HATASINI DÜZELTEN MEKANİZMA
    # Halka arzlarda tek hissede 50.000 TL kar imkansızdır, varsa 100'e böl.
    mask = (df["Tur"] == "Halka Arz") & (df["Kar"] > 50000)
    if mask.any():
        df.loc[mask, "Kar"] = df.loc[mask, "Kar"] / 100
        # Tabloyu Google'da da düzelt
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')

# --- CANLI FİYAT ---
def get_live_price(symbol, tur):
    if tur == "Normal Borsa" and symbol:
        try:
            ticker = symbol if "." in symbol else f"{symbol}.IS"
            price = yf.Ticker(ticker).fast_info['last_price']
            return round(price, 2)
        except: return None
    return None

# --- YAN MENÜ ---
with st.sidebar:
    st.header("🛒 Yeni İşlem Ekle")
    h_tur = st.radio("Kategori", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot Sayısı", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    
    live_p = get_live_price(h_adi, h_tur)
    h_satis = st.number_input("Satış / Güncel Fiyat", value=live_p if live_p else 0.0, format="%.2f")
    
    if st.button("➕ Portföye Kaydet"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("Kaydedildi!")
        st.rerun()

# --- ANA EKRAN ---
st.title("📟 Borsa Takip Terminali")

c1, c2 = st.columns(2)
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

with c1:
    st.metric("🎁 HALKA ARZ KAR", f"{tr_format(ha_kar)} TL")
with c2:
    # Zarar durumunda kırmızı gösterir
    nb_label = "📉 BORSA ZARAR" if nb_kar < 0 else "📊 BORSA KAR"
    st.metric(nb_label, f"{tr_format(nb_kar)} TL")

tab1, tab2 = st.tabs(["💎 Halka Arzlarım", "💹 Normal Hisselerim"])

with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

with tab2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

# --- SİLME VE SIFIRLAMA ---
st.write("---")
st.subheader("⚙️ Veri Yönetimi")
col_s1, col_s2 = st.columns([2, 1])
with col_s1:
    h_sil = st.selectbox("Silinecek Hisse:", ["Seçiniz..."] + df["Hisse"].tolist())
    if h_sil != "Seçiniz..." and st.button("❌ Seçilen Hisseyi Sil"):
        df = df[df["Hisse"] != h_sil]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()
with col_s2:
    if st.button("🚨 TÜM VERİLERİ SIFIRLA"):
        sheet.clear()
        sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
        st.rerun()
