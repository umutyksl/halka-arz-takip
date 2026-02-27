import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- GOOGLE SHEETS AYARLARI ---
# Senin mevcut ID'n ve bağlantı ayarların (Dokunmuyoruz)
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
        st.error(f"Kimlik doğrulama hatası: {e}")
        return None

def tr_format(val):
    try:
        return "{:,.2f}".format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Halka Arz & Borsa Takip", layout="wide")

# CSS: Kar/Zarar Renkleri ve Metrikler
st.markdown("""
    <style>
    [data-testid='stMetricValue'] { font-size: 40px !important; font-weight: bold !important; }
    .stMetric { padding: 15px; border-radius: 15px; border: 2px solid #ddd; }
    /* Yeşil Pozitif Kar */
    .profit { color: #00c853 !important; }
    /* Kırmızı Negatif Zarar */
    .loss { color: #ff1744 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Portföy Takip Paneli")

client = get_gspread_client()
if client:
    try:
        sheet = client.open_by_key(SHEET_ID).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # ESKİ VERİLERİ KORUMA: Eğer 'Tur' sütunu yoksa ekle ve hepsini 'Halka Arz' yap
        if not df.empty and "Tur" not in df.columns:
            df["Tur"] = "Halka Arz"
        elif df.empty:
            df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
            
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
else:
    st.stop()

# --- YAN MENÜ: VERİ GİRİŞİ ---
with st.sidebar:
    st.header("➕ Yeni İşlem Ekle")
    
    # 1. İşlem Türü Seçimi
    h_tur = st.radio("İşlem Türü", ["Halka Arz", "Normal Borsa"])
    
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    
    # Normal borsa ise 'Satış' yerine 'Güncel Fiyat' gibi düşünelim
    satis_label = "Satış Fiyatı" if h_tur == "Halka Arz" else "Güncel Fiyat"
    h_satis = st.number_input(satis_label, min_value=0.0, format="%.2f")
    
    h_lot = st.number_input("Lot (Hesap Başı)", min_value=0)
    
    # Hesap sayısı artık 4'e kadar
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=2)
    
    if st.button("Kaydet"):
        if h_adi and h_lot > 0:
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap
            
            # Akıllı Güncelleme
            if h_adi in df["Hisse"].values:
                idx = df[df["Hisse"] == h_adi].index[0]
                df.at[idx, 'Hesap'] = int(df.at[idx, 'Hesap']) + h_hesap
                df.at[idx, 'Kar'] = float(df.at[idx, 'Kar']) + yeni_kar
                df.at[idx, 'Satis'] = h_satis
                df.at[idx, 'Tur'] = h_tur
            else:
                yeni_satir = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": yeni_kar, "Tur": h_tur}
                df = pd.concat([df, pd.DataFrame([yeni_satir])], ignore_index=True)
            
            # Google Sheets'e Yaz
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.success("Veri başarıyla işlendi!")
            st.rerun()

# --- ANA PANEL: ÖZET METRİKLER ---
# Verileri sayıya çevir
for col in ["Kar", "Alis", "Satis"]:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

col1, col2 = st.columns(2)

# Halka Arz Karı (Sadece Yeşil)
halka_arz_toplam = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
with col1:
    st.metric(label="🚀 TOPLAM HALKA ARZ KAZANCI", value=f"{tr_format(halka_arz_toplam)} TL")

# Normal Borsa Kar/Zarar (Dinamik Renk)
normal_borsa_toplam = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()
with col2:
    label_text = "📉 NORMAL BORSA ZARAR" if normal_borsa_toplam < 0 else "📈 NORMAL BORSA KAR"
    # Delta rengi otomatik ayarlar
    st.metric(label=label_text, value=f"{tr_format(normal_borsa_toplam)} TL", delta=f"{tr_format(normal_borsa_toplam)}", delta_color="normal")

st.write("---")

# --- TABLOLAR ---
tab1, tab2 = st.tabs(["🎁 Halka Arzlarım", "📊 Normal Portföy"])

with tab1:
    st.subheader("Halka Arz Satış Detayları")
    df_halka = df[df["Tur"] == "Halka Arz"].copy()
    if not df_halka.empty:
        st.dataframe(df_halka[["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
    else:
        st.info("Henüz halka arz verisi yok.")

with tab2:
    st.subheader("Normal Hisse Kar/Zarar Durumu")
    df_normal = df[df["Tur"] == "Normal Borsa"].copy()
    if not df_normal.empty:
        # Kar/Zarar durumuna göre renklendirme için bir fonksiyon
        def color_kar(val):
            color = 'red' if val < 0 else 'green'
            return f'color: {color}; font-weight: bold'
        
        st.dataframe(df_normal[["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
    else:
        st.info("Henüz normal borsa verisi yok.")

# Kayıt Silme
with st.expander("🗑️ Kayıt Sil"):
    liste = df["Hisse"].tolist()
    if liste:
        secilen = st.selectbox("Silinecek Hisse:", liste)
        if st.button("Kalıcı Olarak Sil"):
            df = df[df["Hisse"] != secilen]
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.rerun()
