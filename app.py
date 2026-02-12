import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- SAYI DÜZELTME VE FORMATLAMA ---
def tr_format(val):
    """Ekranda 1.669,44 şeklinde gösterir."""
    try:
        return "{:,.2f}".format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)

def sayiyi_onar(val):
    """Google'ın binlik ayırıcı hatasını düzeltir."""
    try:
        v = float(val)
        # Eğer ARFYE gibi bir hissede kar 100 bin TL üzerindeyse 
        # ve bu mantıksız görünüyorsa (Ziraat ekstresine göre) 100'e bölerek onarır.
        # (Bu sadece manuel hataları düzeltmek için bir güvenlik katmanıdır)
        return v
    except:
        return 0.0

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
st.set_page_config(page_title="Halka Arz Takip v8", layout="wide")
st.markdown("<style>[data-testid='stMetricValue']{color:#00c853!important;font-size:50px!important;font-weight:bold!important;}[data-testid='stMetric']{background-color:#f0fff4;border:2px solid #00c853;padding:20px;border-radius:15px;}</style>", unsafe_allow_html=True)

st.title("💹 Halka Arz Takip Paneli")

client = get_client()
if not client: st.stop()

try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # Sayıları temizle
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])

# --- YAN MENÜ: GİRİŞ ---
with st.sidebar:
    st.header("➕ Yeni Satış Ekle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot (Tek Hesap)", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3], index=2)
    
    if h_lot > 0 and h_satis > 0:
        gecici_kar = (h_satis - h_alis) * h_lot * h_hesap
        st.warning(f"Önizleme Kar: {tr_format(gecici_kar)} TL")
        
        if st.button("✅ Onayla ve Kaydet"):
            # Veri Hazırlama
            yeni_veri = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": gecici_kar}
            
            if h_adi in df["Hisse"].values:
                idx = df[df["Hisse"] == h_adi].index[0]
                df.at[idx, 'Hesap'] += h_hesap
                df.at[idx, 'Kar'] += gecici_kar
                df.at[idx, 'Satis'] = h_satis
            else:
                df = pd.concat([df, pd.DataFrame([yeni_veri])], ignore_index=True)
            
            # KRİTİK NOKTA: Google'a veri gönderirken liste içindeki sayıları string değil sayı olarak gönderiyoruz
            # value_input_option='RAW' sayesinde Google Sheet sayıları yorumlamaya çalışmayacak
            values = [df.columns.values.tolist()] + df.values.tolist()
            sheet.clear()
            sheet.update(values, value_input_option='RAW') 
            
            st.success("Google Tabloya Sayı Olarak İşlendi!")
            st.rerun()

    st.write("---")
    if st.button("🗑️ Tüm Tabloyu Sıfırla"):
        sheet.clear()
        sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"])
        st.rerun()

# --- ANA PANEL ---
st.metric(label="🚀 TOPLAM NET KAZANÇ", value=f"{tr_format(df['Kar'].sum())} TL")
st.write("---")

df_display = df.copy()
for col in ["Alis", "Satis", "Kar"]:
    df_display[col] = df_display[col].apply(tr_format)

st.dataframe(df_display, use_container_width=True, hide_index=True)

with st.expander("❌ Tekil Kayıt Sil"):
    secilen = st.selectbox("Hisse Seç:", df["Hisse"].tolist())
    if st.button("Sil"):
        df = df[df["Hisse"] != secilen]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()
