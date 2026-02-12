import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client
import json

# --- GOOGLE SHEETS AYARLARI ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_spread():
    try:
        # Streamlit secrets'tan veriyi dict olarak çek
        # st.secrets bir AttrDict'tir, bunu gerçek bir dict'e zorluyoruz
        creds = dict(st.secrets["gcp_service_account"])
        
        # Private key içindeki gerçek yeni satır karakterlerini (varsa) işle
        if "private_key" in creds:
            creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        
        return Spread(SHEET_ID, creds=creds)
    except Exception as e:
        st.error(f"Kimlik doğrulama hatası: {e}")
        return None

# --- GERİ KALAN KODLAR ---
st.set_page_config(page_title="Halka Arz Takip v4", layout="wide")

# Görsel Stil
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00c853 !important; font-size: 48px !important; font-weight: bold !important; }
    [data-testid="stMetric"] { background-color: #f0fff4; border: 2px solid #00c853; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Tam Otomatik Halka Arz Takip")

spread = get_spread()
if spread:
    try:
        df = spread.sheet_to_df(index=None)
    except Exception as e:
        st.error(f"Tablo okuma hatası: {e}")
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])
else:
    st.stop()

if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])

# Veri Girişi
with st.sidebar:
    st.header("➕ Satış Ekle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", min_value=0)
    h_hesap = st.selectbox("Hesap", [1, 2, 3], index=2)
    
    if st.button("Kaydet"):
        if h_adi and h_lot > 0:
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
            if h_adi in df["Hisse"].values:
                idx = df[df["Hisse"] == h_adi].index[0]
                df.at[idx, 'Hesap'] = int(df.at[idx, 'Hesap']) + h_hesap
                df.at[idx, 'Kar'] = float(df.at[idx, 'Kar']) + yeni_kar
            else:
                yeni_satir = pd.DataFrame([{"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar}])
                df = pd.concat([df, yeni_satir], ignore_index=True)
            
            spread.df_to_sheet(df, index=False, replace=True)
            st.success("Başarıyla Google Sheets'e kaydedildi!")
            st.rerun()

# Ana Panel
df["Kar"] = pd.to_numeric(df["Kar"], errors='coerce').fillna(0)
st.metric(label="🚀 TOPLAM NET KAZANÇ", value=f"{df['Kar'].sum():,.2f} TL")
st.dataframe(df, use_container_width=True, hide_index=True)
