import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

# --- GOOGLE BAĞLANTI ---
def get_client():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scopes))
    except:
        return None

# --- TÜRKÇE SAYI DÖNÜŞTÜRME ---
def tr_to_float(x):
    try:
        if pd.isna(x):
            return 0.0
        x = str(x).strip()
        if x == "":
            return 0.0
        x = x.replace(".", "")
        x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

def tr_format(val):
    try:
        return "{:,.2f}".format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)

# --- SAYFA ---
st.set_page_config(page_title="Borsa Takip v19", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #000000 !important; }

div[data-testid="stMetricValue"] {
    color: #00ff00 !important;
    font-size: 50px !important;
    font-weight: bold !important;
}

div[data-testid="stMetricDelta"] {
    color: #ff3131 !important;
}

div[data-testid="stMetric"] {
    background-color: #111111 !important;
    border: 1px solid #333333 !important;
    border-radius: 10px !important;
    padding: 20px !important;
}

h1, h2, h3, p, label, span { color: white !important; }
</style>
""", unsafe_allow_html=True)

st.title("📟 Borsa Takip Terminali")

client = get_client()
if not client:
    st.stop()

# --- VERİ ÇEK ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()

    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    if "Tur" not in df.columns:
        df["Tur"] = "Halka Arz"

    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = df[col].apply(tr_to_float)

    # KAR HER ZAMAN YENİDEN HESAPLANIR
    df["Kar"] = (df["Satis"] - df["Alis"]) * df["Lot"] * df["Hesap"]

except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- YAN MENÜ ---
with st.sidebar:
    st.header("➕ İşlem Ekle")

    h_tur = st.radio("Tür", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=2)
    h_satis = st.number_input("Güncel/Satış", value=0.0, format="%.2f")

    if h_tur == "Normal Borsa" and h_adi:
        if st.button("🔍 Canlı Fiyat"):
            try:
                p = yf.Ticker(f"{h_adi}.IS").fast_info['last_price']
                st.success(f"Canlı: {p:.2f} TL")
            except:
                st.error("Fiyat alınamadı")

    if st.button("✅ Kaydet"):
        kar = (h_satis - h_alis) * h_lot * h_hesap

        yeni = {
            "Hisse": h_adi,
            "Alis": h_alis,
            "Satis": h_satis,
            "Lot": h_lot,
            "Hesap": h_hesap,
            "Kar": kar,
            "Tur": h_tur
        }

        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)

        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()

# --- KAR HESAPLAMA ---
ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

c1, c2 = st.columns(2)

with c1:
    st.metric("🎁 HALKA ARZ KAR", f"{tr_format(ha_kar)} TL")

with c2:
    st.metric(
        "📊 BORSA KAR",
        f"{tr_format(nb_kar)} TL",
        delta=f"{tr_format(nb_kar)} TL",
        delta_color="inverse" if nb_kar < 0 else "normal"
    )

tab1, tab2 = st.tabs(["🎁 Halka Arz", "💹 Borsa"])

with tab1:
    st.dataframe(df[df["Tur"] == "Halka Arz"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]],
                 use_container_width=True, hide_index=True)

with tab2:
    st.dataframe(df[df["Tur"] == "Normal Borsa"][["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]],
                 use_container_width=True, hide_index=True)

# --- SİLME ---
st.write("---")

h_liste = df["Hisse"].tolist()

if h_liste:
    secilen = st.selectbox("Silinecek Hisse:", h_liste)

    if st.button("❌ Sil"):
        df = df[df["Hisse"] != secilen]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()
