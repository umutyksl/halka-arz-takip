import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client
import json

# --- GOOGLE SHEETS AYARLARI ---
# Streamlit Secrets'tan kimlik bilgilerini alıyoruz
creds_dict = dict(st.secrets["gcp_service_account"])
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_spread():
    return Spread(SHEET_ID, creds=creds_dict)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Otomatik Kayıt Sistemi", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00c853 !important; font-size: 48px !important; font-weight: bold !important; }
    [data-testid="stMetric"] { background-color: #f0fff4; border: 2px solid #00c853; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Tam Otomatik Halka Arz Takip")

# Verileri Google Sheets'ten Çek
spread = get_spread()
df = spread.sheet_to_df(index=None)

# Eğer tablo boşsa sütunları oluştur
if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])

# --- YAN MENÜ: Veri Girişi ---
with st.sidebar:
    st.header("➕ Satış Ekle / Güncelle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0)
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0)
    h_lot = st.number_input("Lot", min_value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3], index=2)
    
    if st.button("Google Tabloya Kaydet"):
        yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
        
        # Hisse varsa üzerine ekle
        if h_adi in df["Hisse"].values:
            idx = df[df["Hisse"] == h_adi].index[0]
            df.at[idx, 'Hesap'] = int(df.at[idx, 'Hesap']) + h_hesap
            df.at[idx, 'Kar'] = float(df.at[idx, 'Kar']) + yeni_kar
        else:
            yeni_satir = pd.DataFrame([{"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar}])
            df = pd.concat([df, yeni_satir], ignore_index=True)
        
        # Google Sheets'e Yaz
        spread.df_to_sheet(df, index=False, replace=True)
        st.success("Google Tablo Güncellendi!")
        st.rerun()

# --- ANA PANEL ---
toplam_net_kar = pd.to_numeric(df["Kar"]).sum()
st.metric(label="🚀 CEBE GİREN TOPLAM NET KAZANÇ", value=f"{toplam_net_kar:,.2f} TL")

st.subheader("📋 Google Sheets Verileri")
st.dataframe(df, use_container_width=True, hide_index=True)

# Kayıt Silme
with st.expander("🗑️ Kayıt Sil"):
    liste = df["Hisse"].tolist()
    if liste:
        secilen = st.selectbox("Silinecek Hisse:", liste)
        if st.button("Seçiliyi Google'dan Sil"):
            df = df[df["Hisse"] != secilen]
            spread.df_to_sheet(df, index=False, replace=True)
            st.rerun()
