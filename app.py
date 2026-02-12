import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re

# --- FONKSİYONLAR ---
def temiz_sayi(val):
    """Google Sheets'ten gelen karmaşık formatlı sayıları temizler."""
    if isinstance(val, (int, float)): return float(val)
    s = str(val).strip()
    if not s: return 0.0
    # Eğer sayıda hem nokta hem virgül varsa (Örn: 1.234,56)
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    # Sadece virgül varsa (Örn: 1234,56)
    elif "," in s:
        s = s.replace(",", ".")
    # Sayı olmayan karakterleri temizle (₺ sembolü vb.)
    s = re.sub(r'[^\d.-]', '', s)
    try:
        return float(s)
    except:
        return 0.0

def tr_format(val):
    """Sayıyı ekranda 1.669,44 formatında gösterir."""
    try:
        val = float(val)
        return "{:,.2f}".format(val).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)

# --- GOOGLE SHEETS BAĞLANTI ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_client():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scopes))
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Halka Arz Kar Takip v7", layout="wide")
st.markdown("<style>[data-testid='stMetricValue']{color:#00c853!important;font-size:50px!important;font-weight:bold!important;}[data-testid='stMetric']{background-color:#f0fff4;border:2px solid #00c853;padding:20px;border-radius:15px;}</style>", unsafe_allow_html=True)

st.title("💹 Halka Arz Kar Takip Paneli")

client = get_client()
if not client: st.stop()

try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # Gelen tüm sayısal sütunları temizle
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        if col in df.columns:
            df[col] = df[col].apply(temiz_sayi)
except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])

# --- YAN MENÜ: GİRİŞ ---
with st.sidebar:
    st.header("➕ Yeni Satış Ekle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f", step=0.01)
    h_satis = st.number_input("Satış Fiyatı", value=0.0, format="%.2f", step=0.01)
    h_lot = st.number_input("Lot (Tek Hesap)", value=0, step=1)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3], index=2)
    
    # HESAPLAMA ÖNİZLEME (Hata yapmanı engeller)
    if h_lot > 0 and h_satis > 0:
        gecici_kar = (h_satis - h_alis) * h_lot * h_hesap
        st.warning(f"Önizleme Kar: {tr_format(gecici_kar)} TL")
        
        if st.button("✅ Onayla ve Google'a Kaydet"):
            if h_adi in df["Hisse"].values:
                idx = df[df["Hisse"] == h_adi].index[0]
                df.at[idx, 'Hesap'] += h_hesap
                df.at[idx, 'Kar'] += gecici_kar
                df.at[idx, 'Satis'] = h_satis
            else:
                yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": gecici_kar}
                df = pd.concat([df, pd.DataFrame([yeni])], ignore_index=True)
            
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            st.success("Kaydedildi!")
            st.rerun()

    st.write("---")
    if st.button("🗑️ Tüm Tabloyu Sıfırla (Dikkat!)"):
        sheet.clear()
        sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])
        st.rerun()

# --- ANA PANEL ---
toplam_kar = df["Kar"].sum()
st.metric(label="🚀 TOPLAM NET KAZANÇ", value=f"{tr_format(toplam_kar)} TL")

st.write("---")
df_goster = df.copy()
# Sayıları güzel gösterelim
for col in ["Alis", "Satis", "Kar"]:
    df_goster[col] = df_goster[col].apply(tr_format)

st.dataframe(df_goster, use_container_width=True, hide_index=True)

with st.expander("❌ Tekil Kayıt Sil"):
    secilen = st.selectbox("Hisse Seç:", df["Hisse"].tolist())
    if st.button("Seçileni Sil"):
        df = df[df["Hisse"] != secilen]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.rerun()
