import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# --- GOOGLE BAĞLANTI (Senin en güvendiğin v9 yapısı) ---
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

# --- TASARIM: SİYAH ARKA PLAN VE NET RENKLER (CSS GÜNCELLENDİ) ---
st.set_page_config(page_title="Borsa Portföy v19", layout="wide")

st.markdown("""
    <style>
    /* Sayfa Arkaplanı */
    .stApp { background-color: #000000 !important; }
    
    /* Metrik Değerlerini Zorla Yeşil Yap */
    div[data-testid="stMetricValue"] > div {
        color: #00ff00 !important;
        font-size: 50px !important;
        font-weight: bold !important;
    }
    
    /* Metrik Kutusu Siyah */
    div[data-testid="stMetric"] {
        background-color: #111111 !important;
        border: 1px solid #333333 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }

    /* Tüm Yazılar Beyaz */
    h1, h2, h3, p, label, span, .stMarkdown { color: #ffffff !important; }
    
    /* Tablo Tasarımı */
    .stDataFrame { background-color: #111111 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📟 Borsa Takip Terminali")

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME (v9 Mantığı - Sayılara asla dokunma) ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"

    # Sayı Dönüşümü (Sadece virgül-nokta değişimi, bölme/çarpma yok)
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors='coerce').fillna(0)
except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- ÜST ÖZET ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

col1, col2 = st.columns(2)
with col1:
    st.metric("🎁 HALKA ARZ KAR", f"{tr_format(ha_kar)} TL")
with col2:
    # Zarar varsa başlık değişsin
    nb_label = "📉 BORSA ZARAR" if nb_kar < 0 else "📊 BORSA KAR"
    st.metric(nb_label, f"{tr_format(nb_kar)} TL", delta=f"{tr_format(nb_kar)} TL" if nb_kar < 0 else None, delta_color="inverse")

# --- TABLOLAR ---
t1, t2 = st.tabs(["📁 Halka Arzlarım", "💹 Normal Hisse/Borsa"])
with t1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
with t2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

# --- YAN MENÜ: GİRİŞ ---
with st.sidebar:
    st.header("➕ Yeni İşlem")
    h_tur = st.radio("Tür", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    
    # Canlı Fiyat
    h_satis = st.number_input("Güncel/Satış Fiyatı", value=0.0, format="%.2f")
    if h_tur == "Normal Borsa" and h_adi:
        if st.button("🔍 Canlı Fiyat Çek"):
            try:
                p = yf.Ticker(f"{h_adi}.IS").fast_info['last_price']
                st.info(f"Anlık: {p:.2f} TL")
            except: st.error("Fiyat gelmedi")

    if st.button("💾 Google Sheets'e Kaydet"):
        yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni_satir = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar, "Tur": h_tur}
        # Eskisini sil, yenisini ekle
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni_satir])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("Başarıyla Yedeklendi!")
        st.rerun()

# --- YÖNETİM ---
st.write("---")
st.subheader("🗑️ Kayıt Yönetimi")
sil_liste = df["Hisse"].tolist()
if sil_liste:
    c_s1, c_s2 = st.columns([3, 1])
    with c_s1:
        s_sec = st.selectbox("Silinecek Hisse:", sil_liste)
    with c_s2:
        if st.button("❌ Seçileni Sil"):
            df = df[df["Hisse"] != s_sec]
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.rerun()

if st.button("🚨 TÜM VERİLERİ SIFIRLA"):
    sheet.clear()
    sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
    st.rerun()
