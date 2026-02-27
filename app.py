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

# --- TASARIM: SİYAH ARKA PLAN VE GERÇEK YEŞİL/KIRMIZI ---
st.set_page_config(page_title="Borsa Portföy v17", layout="wide")

st.markdown("""
    <style>
    /* Tüm sayfa siyah */
    .stApp { background-color: #000000 !important; }
    
    /* Metrik Değerlerini ZORLA YEŞİL Yap (Beyaz Yazıya Son) */
    div[data-testid="stMetricValue"] > div {
        color: #00ff00 !important;
        font-size: 50px !important;
        font-weight: bold !important;
    }
    
    /* Metrik Kutuları Siyah */
    div[data-testid="stMetric"] {
        background-color: #111111 !important;
        border: 1px solid #333333 !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }

    /* Yazıları Beyaz Yap */
    h1, h2, h3, p, label, .stMarkdown { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📟 Borsa Takip Terminali")

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME (v9 Mantığı - Sayılara dokunma) ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    # Eğer 'Tur' sütunu yoksa ekle
    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"

    # Sayıları sayıya çevir (Noktayı silme hatası kaldırıldı)
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors='coerce').fillna(0)
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
    
    # Canlı fiyat desteği
    h_satis = st.number_input("Güncel/Satış", value=0.0, format="%.2f")
    if h_tur == "Normal Borsa" and h_adi:
        if st.button("🔍 Canlı Fiyat Çek"):
            try:
                p = yf.Ticker(f"{h_adi}.IS").fast_info['last_price']
                st.info(f"Anlık: {p:.2f} TL")
            except: st.error("Bulunamadı.")

    if st.button("💾 Kaydet"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()

# --- ANA PANEL ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

c1, c2 = st.columns(2)
with c1:
    st.metric("🎁 HALKA ARZ TOPLAM KAR", f"{tr_format(ha_kar)} TL")
with c2:
    # Zarar durumunda delta kullanarak kırmızı gösterme
    label = "📉 BORSA ZARAR" if nb_kar < 0 else "📊 BORSA KAR"
    st.metric(label, f"{tr_format(nb_kar)} TL", delta=f"{tr_format(nb_kar)} TL" if nb_kar < 0 else None, delta_color="inverse")

tab1, tab2 = st.tabs(["🎁 Halka Arz", "💹 Borsa"])
with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"], use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"], use_container_width=True, hide_index=True)

# --- SİLME ---
st.write("---")
sil_liste = df["Hisse"].tolist()
if sil_liste:
    secilen = st.selectbox("Silinecek Hisse:", sil_liste)
    if st.button("❌ Sil"):
        df = df[df["Hisse"] != secilen]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()
