import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# --- GOOGLE BAĞLANTI (v9'daki çalışan yapı) ---
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

# --- TASARIM: BEYAZ KUTU & YEŞİL YAZI SİSTEMİ ---
st.set_page_config(page_title="Halka Arz Takip v21", layout="wide")

st.markdown("""
    <style>
    /* Genel sayfa arka planı hafif gri (beyaz kutular öne çıksın diye) */
    .stApp { background-color: #f0f2f6; }
    
    /* SADECE KAZANÇ KUTULARI: Beyaz Arka Plan */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 2px solid #00c853 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    }
    
    /* KUTU İÇİNDEKİ RAKAMLAR: Saf Yeşil (Parlamasız) */
    div[data-testid="stMetricValue"] > div {
        color: #00c853 !important;
        font-size: 48px !important;
        font-weight: bold !important;
    }
    
    /* KUTU BAŞLIKLARI: Koyu Gri/Siyah */
    div[data-testid="stMetricLabel"] > div > p {
        color: #333333 !important;
        font-weight: bold !important;
    }

    /* Tablolar ve başlıklar için siyah yazı */
    h1, h2, h3, p, label { color: #222222 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Portföy Takip Terminali")

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"

    # Sayı Dönüştürme
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors='coerce').fillna(0)
except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- ÜST PANEL (METRİKLER) ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

col1, col2 = st.columns(2)
with col1:
    st.metric("🎁 HALKA ARZ TOPLAM KAR", f"{tr_format(ha_kar)} TL")


with col2:
    nb_label = "📉 BORSA ZARAR" if nb_kar < 0 else "📊 BORSA KAR"
    st.metric(nb_label, f"{tr_format(nb_kar)} TL")

# --- TABLOLAR VE GİRİŞ ---
st.write("---")
tab1, tab2 = st.tabs(["🎁 Halka Arz", "💹 Borsa"])
with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.header("➕ Yeni İşlem")
    h_tur = st.radio("Tür", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    h_satis = st.number_input("Güncel/Satış", value=0.0, format="%.2f")

    if st.button("💾 Kaydet"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()

    st.write("---")
    if st.button("🚨 TÜM VERİLERİ SIFIRLA"):
        sheet.clear()
        sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
        st.rerun()

# --- SİLME ---
st.write("---")
sil_liste = df["Hisse"].tolist()
if sil_liste:
    s_sec = st.selectbox("Hisse Sil:", ["Seçiniz..."] + sil_liste)
    if s_sec != "Seçiniz..." and st.button("❌ Sil"):
        df = df[df["Hisse"] != s_sec]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()
