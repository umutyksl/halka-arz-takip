import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- GOOGLE SHEETS AYARLARI ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_gspread_client():
    try:
        # Secrets'tan veriyi al ve gerçek bir sözlüğe çevir
        creds_info = dict(st.secrets["gcp_service_account"])
        
        # Private key içindeki \n karakterlerini düzelt
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            
        # Yetkilendirme kapsamlarını belirle
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Kimlik doğrulama hatası: {e}")
        return None


# ... (Üst kısımdaki get_gspread_client fonksiyonu aynı kalsın)

# Verileri Çek
client = get_gspread_client()
if client:
    try:
        sheet = client.open_by_key(SHEET_ID).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # EĞER TABLO BOŞSA VEYA ZİRAAT VERİLERİ YOKSA EKLE
        if df.empty:
            # Buraya bahsettiğin Ziraat Yatırım dökümanındaki kârı temsil eden veriyi giriyoruz
            ziraat_verisi = {
                "Hisse": "ZIRAAT_OZET", 
                "Alis": 0.0, 
                "Satis": 0.0, 
                "Lot": 1, 
                "Hesap": 1, 
                "Kar": 11450.00  # Bahsettiğin 11 bin küsür TL kâr
            }
            df = pd.DataFrame([ziraat_verisi])
            # Sayfayı bu başlangıç verisiyle güncelle
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            
    except Exception as e:
        st.error(f"Veri işleme hatası: {e}")
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])
else:
    st.stop()

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Halka Arz Takip v5", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00c853 !important; font-size: 48px !important; font-weight: bold !important; }
    [data-testid="stMetric"] { background-color: #f0fff4; border: 2px solid #00c853; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Tam Otomatik Halka Arz Takip")

# Verileri Çek
client = get_gspread_client()
if client:
    try:
        sheet = client.open_by_key(SHEET_ID).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Tablo okuma hatası: {e}")
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])
else:
    st.stop()

if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])

# --- YAN MENÜ: Veri Girişi ---
with st.sidebar:
    st.header("➕ Satış Ekle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("Lot (1 Hesap)", min_value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3], index=2)
    
    if st.button("Kaydet"):
        if h_adi and h_lot > 0:
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
            
            # DataFrame güncelleme
            if h_adi in df["Hisse"].values:
                idx = df[df["Hisse"] == h_adi].index[0]
                df.at[idx, 'Hesap'] = int(df.at[idx, 'Hesap']) + h_hesap
                df.at[idx, 'Kar'] = float(df.at[idx, 'Kar']) + yeni_kar
            else:
                yeni_satir = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar}
                df = pd.concat([df, pd.DataFrame([yeni_satir])], ignore_index=True)
            
            # Google Sheets'e yaz (Tüm tabloyu güncelle)
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            st.success("Başarıyla kaydedildi!")
            st.rerun()

# --- ANA PANEL ---
df["Kar"] = pd.to_numeric(df["Kar"], errors='coerce').fillna(0)
st.metric(label="🚀 TOPLAM NET KAZANÇ", value=f"{df['Kar'].sum():,.2f} TL")
st.dataframe(df, use_container_width=True, hide_index=True)

with st.expander("🗑️ Kayıt Sil"):
    liste = df["Hisse"].tolist()
    if liste:
        secilen = st.selectbox("Silinecek Hisse:", liste)
        if st.button("Kalıcı Olarak Sil"):
            df = df[df["Hisse"] != secilen]
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            st.rerun()
