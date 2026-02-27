import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# --- GOOGLE BAĞLANTI (v9'daki Sağlam Yapı) ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_client():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scopes))
    except Exception as e:
        return None

def tr_format(val):
    try:
        return "{:,.2f}".format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")
    except: return str(val)

# --- SAYFA VE SİYAH TEMA AYARLARI ---
st.set_page_config(page_title="Borsa Portföy v15", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0d11; color: white; }
    [data-testid='stMetricValue'] { font-size: 50px !important; font-weight: bold !important; }
    .stMetric { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 12px; padding: 20px; }
    
    /* Kar Yeşil, Zarar Kırmızı */
    [data-testid='stMetricValue'] { color: #00c853 !important; }
    [data-testid='stMetricDelta'] > div { color: #ff1744 !important; }
    
    h1, h2, h3, span, label, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📟 Borsa Takip Terminali")

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME VE TEMİZLİK ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"

    # SAYI DÜZELTME MOTORU (83 bin hatasını engeller)
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        # Önce tüm noktaları silip virgülü noktaya çevirerek Google'ın hatasını temizliyoruz
        df[col] = df[col].astype(str).str.replace(".", "").str.replace(",", ".")
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # Otomatik 100 katı küçültme (Eski bozuk verileri anında düzeltir)
    df.loc[(df["Tur"] == "Halka Arz") & (df["Kar"] > 50000), "Kar"] /= 100

except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- YAN MENÜ ---
with st.sidebar:
    st.header("➕ İşlem Ekle")
    h_tur = st.radio("Tür", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    
    # Canlı Fiyat
    h_satis = st.number_input("Güncel/Satış", value=0.0, format="%.2f")
    if h_tur == "Normal Borsa" and h_adi:
        if st.button("🔍 Canlı Fiyat Çek"):
            try:
                p = yf.Ticker(f"{h_adi}.IS").fast_info['last_price']
                st.success(f"Güncel: {p:.2f} TL")
            except: st.error("Fiyat bulunamadı.")

    if st.button("✅ Kaydet"):
        yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni_satir = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni_satir])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()

# --- ÜST METRİKLER ---
c1, c2 = st.columns(2)
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

with c1:
    st.metric("🎁 HALKA ARZ KAR", f"{tr_format(ha_kar)} TL")

with c2:
    st.metric("📊 NORMAL BORSA", f"{tr_format(nb_kar)} TL", delta=f"{tr_format(nb_kar)} TL" if nb_kar < 0 else None)

# --- TABLOLAR ---
t1, t2 = st.tabs(["📁 Halka Arz", "📈 Borsa"])
with t1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
with t2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

# --- SİLME BÖLGESİ ---
st.write("---")
h_liste = df["Hisse"].tolist()
if h_liste:
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        secilen = st.selectbox("Silinecek Hisse:", h_liste)
    with col_s2:
        if st.button("❌ Seçileni Sil"):
            df = df[df["Hisse"] != secilen]
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.rerun()
