import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client
import json

# --- GOOGLE SHEETS AYARLARI ---
# Secrets içindeki [gcp_service_account] başlığını okur
try:
    creds_info = st.secrets["gcp_service_account"]
    # TOML yapısını Python sözlüğüne çeviriyoruz
    creds_dict = {k: v for k, v in creds_info.items()}
except Exception as e:
    st.error("Secrets (Anahtar) hatası: Lütfen Streamlit ayarlarındaki Secrets kısmını kontrol et.")
    st.stop()

# Senin Google Tablo ID'n
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_spread():
    # Kimlik bilgileriyle tabloya bağlanır
    return Spread(SHEET_ID, creds=creds_dict)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Otomatik Kayıt Sistemi v4", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00c853 !important; font-size: 48px !important; font-weight: bold !important; }
    [data-testid="stMetric"] { background-color: #f0fff4; border: 2px solid #00c853; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Tam Otomatik Halka Arz Takip")

# Verileri Google Sheets'ten Çek
try:
    spread = get_spread()
    # İlk sayfadaki verileri DataFrame olarak al (Başlıklar: Hisse, Alis, Satis, Lot, Hesap, Kar)
    df = spread.sheet_to_df(index=None)
except Exception as e:
    st.error(f"Google Sheets'e bağlanılamadı. Hata: {e}")
    st.stop()

# Eğer tablo tamamen boşsa hata almamak için sütunları tanımlayalım
if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])

# --- YAN MENÜ: Veri Girişi ---
with st.sidebar:
    st.header("➕ Satış Ekle / Güncelle")
    h_adi = st.text_input("Hisse Kodu (Örn: NETCD)").upper()
    h_alis = st.number_input("Halka Arz Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("Hesap Başı Lot", min_value=0)
    h_hesap = st.selectbox("Kaç Hesap Sattın?", [1, 2, 3], index=2)
    
    if st.button("Google Tabloya Kaydet"):
        if h_adi and h_lot > 0:
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
            
            # Eğer bu hisse tabloda zaten varsa (Akıllı Birleştirme)
            if h_adi in df["Hisse"].values:
                idx = df[df["Hisse"] == h_adi].index[0]
                # Verileri sayıya çevirerek ekleme yapalım (Hata önleme)
                df.at[idx, 'Hesap'] = int(df.at[idx, 'Hesap']) + h_hesap
                df.at[idx, 'Kar'] = float(df.at[idx, 'Kar']) + yeni_kar
                df.at[idx, 'Satis'] = h_satis # En son satış fiyatını günceller
            else:
                # Yeni kayıt oluştur
                yeni_satir = pd.DataFrame([{"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar}])
                df = pd.concat([df, yeni_satir], ignore_index=True)
            
            # Google Sheets'e veriyi GÖNDER (Kalıcı kayıt burası!)
            spread.df_to_sheet(df, index=False, replace=True)
            st.success(f"{h_adi} başarıyla Google Tabloya işlendi!")
            st.rerun()
        else:
            st.warning("Lütfen Hisse Kodu ve Lot bilgilerini doldur.")

# --- ANA PANEL ---
# Kar sütununu sayıya çevirip toplamını alalım
df["Kar"] = pd.to_numeric(df["Kar"], errors='coerce').fillna(0)
toplam_net_kar = df["Kar"].sum()

st.metric(label="🚀 CEBE GİREN TOPLAM NET KAZANÇ (GÜNCEL)", value=f"{toplam_net_kar:,.2f} TL")

st.write("---")
st.subheader("📋 Google Tablodaki Güncel Veriler")
st.dataframe(df, use_container_width=True, hide_index=True)

# Kayıt Silme Bölümü
with st.expander("🗑️ Google'dan Kayıt Sil"):
    liste = df["Hisse"].tolist()
    if liste:
        secilen = st.selectbox("Silinecek Hisseyi Seç:", liste)
        if st.button("Seçiliyi Kalıcı Olarak Sil"):
            df = df[df["Hisse"] != secilen]
            spread.df_to_sheet(df, index=False, replace=True)
            st.rerun()
