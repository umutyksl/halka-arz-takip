import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# --- BAĞLANTI AYARLARI ---
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

# --- YENİ TASARIM SİSTEMİ (Profesyonel Görünüm) ---
st.set_page_config(page_title="Borsa Portföy v23", layout="wide")

st.markdown("""
    <style>
    /* Genel Arka Plan: Açık ve Ferah Gri */
    .stApp { background-color: #f1f3f6 !important; }
    
    /* Üst Kazanç Kutuları: Beyaz Arka Plan, Belirgin Kenarlık */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 2px solid #2e7d32 !important; /* Koyu Yeşil Kenarlık */
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    }
    
    /* Kazanç Rakamları: Saf Yeşil ve Okunaklı */
    div[data-testid="stMetricValue"] > div {
        color: #2e7d32 !important;
        font-size: 44px !important;
        font-weight: 800 !important;
    }
    
    /* Kutu Başlıkları: Koyu Gri (Görünür olması için) */
    div[data-testid="stMetricLabel"] > div > p {
        color: #1b1f23 !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }

    /* Tablo ve Diğer Metinler */
    h1, h2, h3, label { color: #1b1f23 !important; font-weight: bold !important; }
    p { color: #1b1f23 !important; }
    
    /* Kenar Menüsü (Sidebar) */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Portföy Yönetim Terminali")

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME VE AKILLI KONTROL ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"

    # Sayıları işle
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors='coerce').fillna(0)
    
    # Otomatik Düzeltme: Eğer bir halka arz karı anormal yüksekse (100 kat hatası varsa) düzelt
    df.loc[(df["Tur"] == "Halka Arz") & (df["Kar"] > 50000), "Kar"] /= 100
except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- ÜST PANEL ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

c1, c2 = st.columns(2)
with c1:
    st.metric("🎁 TOPLAM HALKA ARZ KAZANCI", f"{tr_format(ha_kar)} TL")


with c2:
    nb_label = "📈 BORSA KAZANCI" if nb_kar >= 0 else "📉 BORSA DURUMU (ZARAR)"
    st.metric(nb_label, f"{tr_format(nb_kar)} TL")

# --- TABLOLAR ---
st.write("---")
tab1, tab2 = st.tabs(["💎 Halka Arz Listesi", "📊 Borsa Portföyü"])
with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

# --- YAN MENÜ: GİRİŞ ---
with st.sidebar:
    st.header("⚙️ İşlem Menüsü")
    h_tur = st.radio("Kategori", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot Miktarı", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    h_satis = st.number_input("Satış / Güncel Fiyat", value=0.0, format="%.2f")

    if st.button("🚀 Portföyü Güncelle"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("İşlem Başarılı!")
        st.rerun()

    st.write("---")
    if st.button("🗑️ TÜM VERİLERİ SIFIRLA"):
        sheet.clear()
        sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
        st.rerun()

# --- SİLME YÖNETİMİ ---
st.write("---")
st.subheader("🗑️ Kayıt Düzenleme")
sil_liste = df["Hisse"].tolist()
if sil_liste:
    col_d1, col_d2 = st.columns([3, 1])
    with col_d1:
        s_hisse = st.selectbox("Silmek istediğiniz hisse:", ["Seçiniz..."] + sil_liste)
    with col_d2:
        if s_hisse != "Seçiniz..." and st.button("❌ Kaydı Sil"):
            df = df[df["Hisse"] != s_hisse]
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.rerun()
