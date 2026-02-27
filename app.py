import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# --- GOOGLE BAĞLANTI ---
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

# --- AGRESİF SİYAH TEMA VE RENK AYARI ---
st.set_page_config(page_title="Borsa Portföy v16", layout="wide")

st.markdown("""
    <style>
    /* Tüm sayfa siyah */
    .stApp { background-color: #000000 !important; color: #ffffff !important; }
    
    /* Metrik değerlerini ZORLA yeşil yapma (Beyaz yazıya son) */
    [data-testid="stMetricValue"] {
        color: #00ff00 !important;
        font-size: 55px !important;
        font-weight: 800 !important;
    }
    
    /* Kutuların tasarımı */
    [data-testid="stMetric"] {
        background-color: #111111 !important;
        border: 2px solid #333333 !important;
        border-radius: 15px !important;
        padding: 25px !important;
    }

    /* Tablo ve diğer yazıların rengi */
    h1, h2, h3, p, label, .stMarkdown { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📟 Borsa Takip Terminali v16")

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME VE 83 BİN HATASI TEMİZLİĞİ ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"

    # Sayıları temizleme (Kritik nokta)
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        # Önce noktaları kaldırıp virgülü noktaya çevirerek saf sayıya ulaşıyoruz
        df[col] = df[col].astype(str).str.replace(".", "").str.replace(",", ".")
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # Eğer toplam Kar hala 50 bin üzerindeyse, 100 katı hatasını otomatik onar
    if df[df["Tur"] == "Halka Arz"]["Kar"].sum() > 50000:
        df.loc[df["Tur"] == "Halka Arz", "Kar"] /= 100

except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- ÜST METRİKLER ---
c1, c2 = st.columns(2)
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

with c1:
    st.metric("🎁 HALKA ARZ NET KAR", f"{tr_format(ha_kar)} TL")

with c2:
    st.metric("📊 NORMAL BORSA DURUM", f"{tr_format(nb_kar)} TL")

# --- TABLOLAR ---
t1, t2 = st.tabs(["📁 Halka Arz Portföyü", "📈 Normal Borsa Takip"])
with t1:
    st.dataframe(df[df["Tur"] == "Halka Arz"], use_container_width=True, hide_index=True)
with t2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"], use_container_width=True, hide_index=True)

# --- YAN MENÜ: İŞLEMLER ---
with st.sidebar:
    st.header("➕ Yeni İşlem")
    h_tur = st.radio("Tür", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot Sayısı", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    h_satis = st.number_input("Güncel/Satış", value=0.0, format="%.2f")

    if st.button("💾 Kaydet"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()

# --- SİLME BÖLGESİ ---
st.write("---")
h_liste = df["Hisse"].tolist()
if h_liste:
    secilen = st.selectbox("Silmek istediğiniz hisse:", h_liste)
    if st.button("❌ Seçilen Kaydı Sil"):
        df = df[df["Hisse"] != secilen]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()
