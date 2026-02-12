import streamlit as st
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Halka Arz Takip v2", layout="wide")

# Özel CSS ile Renklendirme
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #28a745;
    }
    </style>
    """, unsafe_allow_status_with_danger=True)

st.title("💹 Halka Arz Kar Takip Paneli")

# Başlangıç Verileri
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

# --- YAN MENÜ: Veri Girişi ---
with st.sidebar:
    st.header("➕ Yeni İşlem")
    h_adi = st.text_input("Hisse Kodu").upper()
    h_alis = st.number_input("Alış Fiyatı", min_value=0.0, format="%.2f")
    h_satis = st.number_input("Satış Fiyatı", min_value=0.0, format="%.2f")
    h_lot = st.number_input("1 Hesaptaki Lot", min_value=0)
    
    if st.button("Listeye Ekle"):
        if h_adi and h_lot > 0:
            yeni_kar = (h_satis - h_alis) * h_lot * 3
            yeni_satir = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Kar_3_Hesap": yeni_kar}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([yeni_satir])], ignore_index=True)
            st.success(f"{h_adi} Eklendi!")

# --- ANA EKRAN ---
toplam_kar = st.session_state.df["Kar_3_Hesap"].sum()
st.metric(label="💰 TOPLAM NET KAZANÇ (3 HESAP)", value=f"{toplam_kar:,.2f} TL", delta="Hayırlı Olsun!")

st.subheader("📋 İşlem Geçmişi")
st.dataframe(st.session_state.df.style.format(subset=["Alis", "Satis", "Kar_3_Hesap"], formatter="{:.2f}"), use_container_width=True)

# --- HİSSE SİLME BÖLÜMÜ ---
st.divider()
st.subheader("🗑️ Kayıt Sil")
silinecek_hisse = st.selectbox("Silmek istediğin hisseyi seç:", st.session_state.df["Hisse"].tolist())

if st.button("Seçili Hisseyi Sil"):
    st.session_state.df = st.session_state.df[st.session_state.df["Hisse"] != silinecek_hisse].reset_index(drop=True)
    st.warning(f"{silinecek_hisse} listeden kaldırıldı.")
    st.rerun()
