import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- TÜRKÇE SAYI FORMATI FONKSİYONU ---
def tr_format(val):
    try:
        # Sayıyı 1,669.44 formatına getir, sonra virgül ve noktayı takas et
        s = "{:,.2f}".format(float(val))
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)

# --- GOOGLE SHEETS AYARLARI ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_gspread_client():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

st.set_page_config(page_title="Halka Arz Takip v6", layout="wide")

# Görsel Stil (Yeşil Kutular)
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00c853 !important; font-size: 50px !important; font-weight: bold !important; }
    [data-testid="stMetric"] { background-color: #f0fff4; border: 2px solid #00c853; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Halka Arz Kar Takip (Ziraat Ekstresi Uyumlu)")

client = get_gspread_client()
if client:
    sheet = client.open_by_key(SHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
else:
    st.stop()

if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])

# --- YAN MENÜ: VERİ GİRİŞİ ---
with st.sidebar:
    st.header("➕ Yeni Satış Ekle")
    st.info("⚠️ ÖNEMLİ: Kuruşları girerken NOKTA (.) kullanın. Örn: 31.34")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f", step=0.01)
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f", step=0.01)
    h_lot = st.number_input("Lot (1 Hesap)", min_value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3], index=2)
    
    if st.button("Google Tabloya Kaydet"):
        if h_adi and h_lot > 0:
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
            if h_adi in df["Hisse"].values:
                idx = df[df["Hisse"] == h_adi].index[0]
                df.at[idx, 'Hesap'] = int(df.at[idx, 'Hesap']) + h_hesap
                df.at[idx, 'Kar'] = float(df.at[idx, 'Kar']) + yeni_kar
            else:
                yeni_satir = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar}
                df = pd.concat([df, pd.DataFrame([yeni_satir])], ignore_index=True)
            
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            st.success("Kayıt Başarılı!")
            st.rerun()

# --- ANA PANEL ---
df["Kar"] = pd.to_numeric(df["Kar"], errors='coerce').fillna(0)
toplam_kar = df["Kar"].sum()

# Toplam Karı Türkçe Formatla Gösteriyoruz
st.metric(label="🚀 CEBE GİREN TOPLAM NET KAZANÇ", value=f"{tr_format(toplam_kar)} TL")

st.write("---")
st.subheader("📋 İşlem Özeti")

# Tablodaki sayıları da Türkçe formatta gösterelim
df_display = df.copy()
df_display["Kar"] = df_display["Kar"].apply(tr_format)
st.dataframe(df_display, use_container_width=True, hide_index=True)

with st.expander("🗑️ Kayıt Sil"):
    liste = df["Hisse"].tolist()
    if liste:
        secilen = st.selectbox("Hisse Seç:", liste)
        if st.button("Kalıcı Olarak Sil"):
            df = df[df["Hisse"] != secilen]
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            st.rerun()
