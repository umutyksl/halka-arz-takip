import streamlit as st
import pandas as pd

# Uygulama Başlığı
st.set_page_config(page_title="Halka Arz Takip", layout="wide")
st.title("📊 Halka Arz Kar Takip Paneli (3 Hesap)")

# Mevcut Verilerin (Senin Geçmiş Hisselerin)
initial_data = [
    {"Tarih": "26.11.2025", "Hisse": "PAHOL", "Alis": 1.50, "Satis": 1.68, "Lot": 2800, "Kar_3_Hesap": 1512.00},
    {"Tarih": "23.12.2025", "Hisse": "ZERGY", "Alis": 13.00, "Satis": 13.22, "Lot": 193, "Kar_3_Hesap": 127.38},
    {"Tarih": "09.01.2026", "Hisse": "ARFYE", "Alis": 19.50, "Satis": 31.34, "Lot": 47, "Kar_3_Hesap": 1669.44},
    {"Tarih": "16.01.2026", "Hisse": "MEYSU", "Alis": 7.50, "Satis": 10.96, "Lot": 128, "Kar_3_Hesap": 1328.64},
    {"Tarih": "20.01.2026", "Hisse": "FRMPL", "Alis": 30.24, "Satis": 44.24, "Lot": 40, "Kar_3_Hesap": 1680.00},
    {"Tarih": "20.01.2026", "Hisse": "ZGYO", "Alis": 9.77, "Satis": 12.99, "Lot": 111, "Kar_3_Hesap": 1072.26},
    {"Tarih": "30.01.2026", "Hisse": "UCAYM", "Alis": 18.00, "Satis": 35.00, "Lot": 54, "Kar_3_Hesap": 2754.00},
    {"Tarih": "11.02.2026", "Hisse": "AKHAN", "Alis": 21.50, "Satis": 31.46, "Lot": 35, "Kar_3_Hesap": 1045.80}
]

# Verileri Session State'de tutuyoruz
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(initial_data)

# Sol Menü: Yeni Hisse Girişi
with st.sidebar:
    st.header("➕ Yeni Hisse Ekle")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("1 Hesaptaki Lot", min_value=0)
    
    if st.button("Hesapla ve Listeye Ekle"):
        if h_adi and h_lot > 0:
            yeni_kar = (h_satis - h_alis) * h_lot * 3
            yeni_satir = {"Tarih": "Bugün", "Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Kar_3_Hesap": yeni_kar}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([yeni_satir])], ignore_index=True)
            st.success(f"{h_adi} eklendi!")
        else:
            st.error("Lütfen tüm alanları doldurun.")

# Ana Ekran Özeti
toplam_kar_degeri = st.session_state.df["Kar_3_Hesap"].sum()
st.metric(label="🚀 Toplam Net Kazanç (3 Hesap)", value=f"{toplam_kar_degeri:,.2f} TL")

st.subheader("📋 Kar/Zarar Geçmişin")
st.dataframe(st.session_state.df, use_container_width=True)
