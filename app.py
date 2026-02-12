import streamlit as st
import pandas as pd

# 1. Sayfa Ayarları
st.set_page_config(page_title="Halka Arz Takip v4", layout="wide")

# 2. Görsel Stil
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
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Akıllı Halka Arz Takip Paneli")

# 3. Veri Hazırlığı
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

# 4. Yan Menü: Veri Girişi
with st.sidebar:
    st.header("➕ Satış Ekle/Güncelle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("1 Hesaptaki Lot", min_value=0)
    h_hesap_sayisi = st.selectbox("Kaç Hesap Sattın?", [1, 2, 3], index=2)
    
    if st.button("Sisteme İşle"):
        if h_adi and h_lot > 0:
            yeni_hesaplanan_kar = (h_satis - h_alis) * h_lot * h_hesap_sayisi
            
            # EĞER HİSSE ZATEN VARSA ÜZERİNE EKLE
            if h_adi in st.session_state.df["Hisse"].values:
                idx = st.session_state.df[st.session_state.df["Hisse"] == h_adi].index[0]
                st.session_state.df.at[idx, 'Hesap'] += h_hesap_sayisi
                st.session_state.df.at[idx, 'Kar'] += yeni_hesaplanan_kar
                # Satış fiyatını en son girilen fiyatla güncelleyelim
                st.session_state.df.at[idx, 'Satis'] = h_satis 
                st.success(f"{h_adi} güncellendi! Toplam {st.session_state.df.at[idx, 'Hesap']} hesap oldu.")
            else:
                # EĞER HİSSE YOKSA YENİ SATIR EKLE
                yeni_satir = {
                    "Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, 
                    "Lot": h_lot, "Hesap": h_hesap_sayisi, "Kar": yeni_hesaplanan_kar
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([yeni_satir])], ignore_index=True)
                st.success(f"{h_adi} yeni kayıt olarak eklendi!")
            st.rerun()

# 5. Ana Ekran
toplam_net_kar = st.session_state.df["Kar"].sum()
st.metric(label="🚀 CEBE GİREN TOPLAM NET KAZANÇ", value=f"{toplam_net_kar:,.2f} TL")

st.write("---")
st.subheader("📋 Güncel Portföy Özeti")
st.dataframe(
    st.session_state.df,
    column_config={
        "Kar": st.column_config.NumberColumn("Toplam Birikmiş Kar", format="%.2f TL"),
        "Hesap": "Toplam Satılan Hesap",
        "Lot": "Hesap Başı Lot"
    },
    use_container_width=True,
    hide_index=True
)

# 6. Kayıt Silme
st.write("---")
with st.expander("🗑️ Kayıt Yönetimi"):
    liste = st.session_state.df["Hisse"].tolist()
    if liste:
        secilen = st.selectbox("Hisse Seç:", liste)
        if st.button("Hisseye Ait Tüm Kaydı Sil"):
            st.session_state.df = st.session_state.df[st.session_state.df["Hisse"] != secilen].reset_index(drop=True)
            st.rerun()
