import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# --- GOOGLE BAĞLANTI (En sağlam yapı) ---
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

# --- TASARIM: BEYAZ KUTU & YEŞİL YAZI ---
st.set_page_config(page_title="Halka Arz Takip v20", layout="wide")

st.markdown("""
    <style>
    /* Sayfa Arkaplanı Açık Gri (Kutular belli olsun diye) */
    .stApp { background-color: #f8f9fa; }
    
    /* KUTU AYARI: Arkaplan BEYAZ, Kenarlık YEŞİL */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 2px solid #00c853 !important;
        border-radius: 15px !important;
        padding: 20px !important;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    
    /* YAZI AYARI: Rakamlar YEŞİL */
    div[data-testid="stMetricValue"] > div {
        color: #00c853 !important;
        font-size: 45px !important;
        font-weight: bold !important;
    }
    
    /* Başlık ve Diğer Yazılar Siyah/Koyu Gri */
    h1, h2, h3, p, label { color: #333333 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Halka Arz & Borsa Takip Paneli")

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

    # Sayı Dönüşümü (Sadece virgül-nokta düzeltme)
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors='coerce').fillna(0)
except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- ÜST ÖZET ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

col1, col2 = st.columns(2)
with col1:
    st.metric("🚀 HALKA ARZ TOPLAM KAR", f"{tr_format(ha_kar)} TL")
with col2:
    label = "📉 BORSA ZARAR" if nb_kar < 0 else "📈 BORSA KAR"
    # Zararda delta kırmızı görünür
    st.metric(label, f"{tr_format(nb_kar)} TL", delta=f"{tr_format(nb_kar)} TL" if nb_kar < 0 else None, delta_color="inverse")

# --- TABLOLAR ---
st.write("---")
tab1, tab2 = st.tabs(["🎁 Halka Arz Portföyü", "📊 Normal Borsa Portföyü"])
with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

# --- YAN MENÜ: GİRİŞ ---
with st.sidebar:
    st.header("➕ Yeni İşlem Ekle")
    st.info("Kuruşlar için NOKTA kullanın (Örn: 1.68)")
    h_tur = st.radio("Kategori", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    h_satis = st.number_input("Güncel/Satış Fiyatı", value=0.0, format="%.2f")

    if st.button("💾 Google Tabloya Kaydet"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("Kaydedildi!")
        st.rerun()

    st.write("---")
    if st.button("🚨 TÜM VERİLERİ SIFIRLA"):
        sheet.clear()
        sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
        st.rerun()

# --- SİLME BÖLGESİ ---
st.write("---")
st.subheader("🗑️ Kayıt Yönetimi")
sil_liste = df["Hisse"].tolist()
if sil_liste:
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        s_sec = st.selectbox("Silmek İstediğiniz Hisse:", ["Seçiniz..."] + sil_liste)
    with col_s2:
        if s_sec != "Seçiniz..." and st.button("❌ Seçileni Sil"):
            df = df[df["Hisse"] != s_sec]
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.rerun()
