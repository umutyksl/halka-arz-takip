import streamlit as st
import pandas as pd

# 1. Sayfa Ayarları
st.set_page_config(page_title="Halka Arz Takip v3", layout="wide")

# 2. Yeşil Kar ve Stil Ayarları
st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        color: #00c853 !important;
        font-size: 48px !important;
        font-weight: bold !important;
    }
    [data-testid="stMetric"] {
        background-color: #f0fff4;
        border: 2px solid #00c853;
        padding: 20px;
        border-radius: 15px;
    }
    .stDataFrame {
        border: 1px solid #e6e9ef;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Halka Arz Kar Takip Paneli")

# 3. Veri Hafızası ve Geçmiş Kayıtlar
if 'df' not in st.session_state:
    initial_data = [
        {"Hisse": "PAHOL", "Alis": 1.50, "Satis": 1.68, "Lot": 2800, "Hesap": 3, "Kar": 1512.00},
        {"Hisse": "ZERGY", "Alis": 13.00, "Satis": 13.22, "Lot": 193, "Hesap": 3, "Kar": 127.38},
        {"Hisse": "ARFYE", "Alis": 19.50, "Satis": 31.34, "Lot": 47, "Hesap": 3, "Kar": 1669.44},
        {"Hisse": "MEYSU", "Alis": 7.50, "Satis": 10.96, "Lot": 128, "Hesap": 3, "Kar": 1328.64},
        {"Hisse": "FRMPL", "Alis": 30.24, "Satis": 44.24, "Lot": 40, "Hesap": 3, "Kar": 1680.00},
        {"Hisse": "ZGYO", "Alis": 9.77, "Satis": 12.99, "Lot": 111, "Hesap": 3, "Kar": 1072.26},
        {"Hisse": "UCAYM", "Alis": 18.00, "Satis": 35.00, "Lot": 54, "Hesap": 3, "Kar": 2754.00},
        {"Hisse": "AKHAN", "Alis": 21.50, "Satis": 31.46, "Lot": 35, "Hesap": 3, "Kar": 1045.80}
    ]
    st.session_state.df = pd.DataFrame(initial_data)

# 4. Yan Menü: Yeni Satış Ekleme
with st.sidebar:
    st.header("➕ Yeni Satış Ekle")
    h_adi = st.text_input("Hisse Kodu (Örn: NETCD)").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("1 Hesaptaki Lot", min_value=0)
    
    # NETCD İÇİN BURADAN 1, 2 veya 3 SEÇEBİLİRSİN
    h_hesap_sayisi = st.selectbox("Kaç Hesap Sattın?", [1, 2, 3], index=2)
    
    if st.button("Listeye Ekle"):
        if h_adi and h_lot > 0:
            # Hesaplama: (Satış-Alış) * Lot * Kaç hesap seçildiyse
            yeni_kar = (h_satis - h_alis) * h_lot * h_hesap_sayisi
            yeni_satir = {
                "Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, 
                "Lot": h_lot, "Hesap": h_hesap_sayisi, "Kar": yeni_kar
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([yeni_satir])], ignore_index=True)
            st.success(f"{h_adi} ({h_hesap_sayisi} Hesap) Eklendi!")
        else:
            st.warning("Lütfen bilgileri tam girin.")

# 5. Ana Ekran Özet Rakam
toplam_kar = st.session_state.df["Kar"].sum()
st.metric(label="🚀 CEBE GİREN TOPLAM NET KAZANÇ", value=f"{toplam_kar:,.2f} TL")

st.write("---")
st.subheader("📋 Satış Detayları")

# Tablo Görünümü
st.dataframe(
    st.session_state.df,
    column_config={
        "Kar": st.column_config.NumberColumn("Toplam Kar (TL)", format="%.2f TL"),
        "Hesap": "Satılan Hesap",
        "Alis": "Alış (₺)",
        "Satis": "Satış (₺)",
        "Lot": "Tek Hesap Lot"
    },
    use_container_width=True,
    hide_index=True
)

# 6. Kayıt Silme Paneli
st.write("---")
with st.expander("🗑️ Hatalı Kayıt Sil"):
    hisse_listesi = st.session_state.df["Hisse"].tolist()
    if hisse_listesi:
        secili = st.selectbox("Silinecek hisseyi seç:", hisse_listesi)
        if st.button("Seçili Hisseyi Sil"):
            st.session_state.df = st.session_state.df[st.session_state.df["Hisse"] != secili].reset_index(drop=True)
            st.rerun()
