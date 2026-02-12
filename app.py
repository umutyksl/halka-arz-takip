import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client
from google.oauth2.service_account import Credentials

# --- GOOGLE SHEETS AYARLARI ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_spread():
    try:
        # Secrets'tan TOML formatındaki veriyi al
        creds_info = st.secrets["gcp_service_account"]
        
        # Bu kısım hatayı çözen kritik nokta:
        # TOML'dan gelen veriyi temiz bir Python sözlüğüne (dict) çeviriyoruz
        creds_dict = {key: value for key, value in creds_info.items()}
        
        # private_key içindeki \n karakterlerini düzelt (Eğer bozulduysa)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        return Spread(SHEET_ID, creds=creds_dict)
    except Exception as e:
        st.error(f"Kimlik doğrulama hatası: {e}")
        return None

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Halka Arz Takip v4", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00c853 !important; font-size: 48px !important; font-weight: bold !important; }
    [data-testid="stMetric"] { background-color: #f0fff4; border: 2px solid #00c853; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Tam Otomatik Halka Arz Takip")

# Verileri Google Sheets'ten Çek
spread = get_spread()
if spread:
    try:
        df = spread.sheet_to_df(index=None)
    except Exception as e:
        st.error(f"Tablo okuma hatası: {e}")
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])
else:
    st.stop()

# Eğer tablo boşsa sütunları oluştur
if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])

# --- YAN MENÜ: Veri Girişi ---
with st.sidebar:
    st.header("➕ Satış Ekle / Güncelle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", min_value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3], index=2)
    
    if st.button("Google Tabloya Kaydet"):
        if h_adi and h_lot > 0:
            # Kar hesaplama (Satis - Alis) * Lot * Hesap
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
            
            if h_adi in df["Hisse"].values:
                idx = df[df["Hisse"] == h_adi].index[0]
                df.at[idx, 'Hesap'] = int(df.at[idx, 'Hesap']) + h_hesap
                df.at[idx, 'Kar'] = float(df.at[idx, 'Kar']) + yeni_kar
                df.at[idx, 'Satis'] = h_satis
            else:
                yeni_satir = pd.DataFrame([{"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar}])
                df = pd.concat([df, yeni_satir], ignore_index=True)
            
            # Kaydet ve Yenile
            spread.df_to_sheet(df, index=False, replace=True)
            st.success("Kaydedildi!")
            st.rerun()

# --- ANA PANEL ---
# Kar sütununu sayıya çevir (Hata önleyici)
df["Kar"] = pd.to_numeric(df["Kar"], errors='coerce').fillna(0)
toplam_net_kar = df["Kar"].sum()

st.metric(label="🚀 CEBE GİREN TOPLAM NET KAZANÇ", value=f"{toplam_net_kar:,.2f} TL")
st.dataframe(df, use_container_width=True, hide_index=True)

with st.expander("🗑️ Kayıt Sil"):
    liste = df["Hisse"].tolist()
    if liste:
        secilen = st.selectbox("Silinecek Hisse:", liste)
        if st.button("Kalıcı Olarak Sil"):
            df = df[df["Hisse"] != secilen]
            spread.df_to_sheet(df, index=False, replace=True)
            st.rerun()
