import streamlit as st
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Halka Arz Takip v2", layout="wide")

# ÖZEL RENK AYARLARI (Yeşil Kazanç İçin)
st.markdown("""
    <style>
    /* Toplam Kar Rakamını Yeşil ve Büyük Yapar */
    [data-testid="stMetricValue"] {
        color: #00c853 !important;
        font-size: 48px !important;
        font-weight: bold !important;
    }
    /* Metrik kutusunun etrafını belirginleştirir */
    [data-testid="stMetric"] {
        background-color: #f0fff4;
        border: 2px solid #00c853;
        padding: 20px;
        border-radius: 15px;
    }
    /* Tablo başlıklarını koyulaştırır */
    .stDataFrame {
        border: 1px solid #e6e9ef;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Halka Arz Kar Takip Paneli (3 Hesap)")

# Mevcut Veriler (AKHAN Dahil)
initial_data = [
    {"Hisse": "PAHOL", "Alis": 1.50, "Satis": 1.68, "Lot": 2800, "Kar_3_Hesap": 1512.00},
    {"Hisse": "ZERGY", "Alis": 13.00, "Satis": 13.22, "Lot": 193, "Kar_3_Hesap": 127.38},
    {"Hisse": "ARFYE", "Alis": 19.50, "Satis": 31.34, "Lot": 47, "Kar_3_Hesap": 1669.44},
    {"Hisse": "MEYSU", "Alis": 7.50, "Satis": 10.96, "Lot": 128, "Kar_3_Hesap": 1328.64},
    {"Hisse": "FRMPL", "Alis": 30.24, "Satis": 44.24, "Lot": 40, "Kar_3_Hesap": 1680.00},
    {"Hisse": "ZGYO", "Alis": 9.77, "Satis": 12.99, "Lot": 111, "Kar_3_Hesap": 1072.26},
    {"Hisse": "UCAYM", "Alis": 18.00, "Satis": 35.00, "Lot": 54, "Kar_3_Hesap": 2754.00},
    {"Hisse": "AKHAN", "Alis": 21.50, "Satis": 31.46, "Lot": 35, "Kar_3_Hesap": 1045.80}
]

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(initial_data)

# --- YAN MENÜ: Yeni Hisse Ekleme ---
with st.sidebar:
    st.header("➕ Yeni Halka Arz Ekle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("1 Hesaptaki Lot", min_value=0)
    
    if st.button("Listeye Ekle ve Hesapla"):
        if h_adi and h_lot > 0:
            yeni_kar = (h_satis - h_alis) * h_lot * 3
            yeni_satir = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Kar_3_Hesap": yeni_kar}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([yeni_satir])], ignore_index=True)
            st.success(f"{h_adi} Eklendi!")
        else:
            st.warning("Eksik veri girmeyin.")

# --- ANA PANEL ---
toplam_kar = st.session_state.df["Kar_3_Hesap"].sum()

# Kar Metriği (Senin istediğin o büyük yeşil rakam)
st.metric(label="🚀 TOPLAM NET KAZANÇ (3 HESAP)", value=f"{toplam_kar:,.2f} TL")

st.write("---")
st.subheader("📋 İşlem Geçmişi")

# Tablo Görünümü
st.dataframe(
    st.session_state.df,
    column_config={
        "Kar_3_Hesap": st.column_config.NumberColumn("Toplam Kar (3 Hesap)", format="%.2f TL"),
        "Alis": "Alış (₺)",
        "Satis": "Satış (₺)",
        "Lot": "Lot (Tek)"
    },
    use_container_width=True,
    hide_index=True
)

# --- SİLME BÖLÜMÜ ---
st.write("---")
with st.expander("🗑️ Kayıt Silme Paneli"):
    hisse_listesi = st.session_state.df["Hisse"].tolist()
    secili_hisse = st.selectbox("Silmek istediğin hisseyi seç:", hisse_listesi)
    if st.button("Seçili Hisseyi Sil"):
        st.session_state.df = st.session_state.df[st.session_state.df["Hisse"] != secili_hisse].reset_index(drop=True)
        st.rerun()
    
