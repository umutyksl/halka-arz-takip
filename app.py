import streamlit as st
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Halka Arz Takip v2", layout="wide")

# Görsel Stil Ayarları
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        border-left: 6px solid #198754;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Halka Arz Kar Takip Paneli (3 Hesap)")

# Mevcut Veriler
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
            st.success(f"{h_adi} Listeye Eklendi!")
        else:
            st.warning("Lütfen Hisse Adı ve Lot girin.")

# --- ANA PANEL ---
toplam_kar = st.session_state.df["Kar_3_Hesap"].sum()

col1, col2 = st.columns([2, 1])
with col1:
    st.metric(label="💰 TOPLAM NET KAZANÇ (3 HESAP)", value=f"{toplam_kar:,.2f} TL")
with col2:
    st.info(f"Toplam {len(st.session_state.df)} farklı halka arz satışı yapıldı.")

st.subheader("📋 İşlem Geçmişi")

# Hata veren background_gradient yerine column_config kullanarak renklendirme yapıyoruz
st.dataframe(
    st.session_state.df,
    column_config={
        "Kar_3_Hesap": st.column_config.NumberColumn(
            "Toplam Kar (TL)",
            format="%.2f TL",
        ),
        "Alis": "Alış Fiyatı",
        "Satis": "Satış Fiyatı",
        "Lot": "Lot (Tek)"
    },
    use_container_width=True,
    hide_index=True
)

# --- SİLME BÖLÜMÜ ---
st.write("---")
st.subheader("🗑️ Kayıt Yönetimi")
col_sil, col_bos = st.columns([1, 2])
with col_sil:
    hisse_listesi = st.session_state.df["Hisse"].tolist()
    secili_hisse = st.selectbox("Silmek istediğin hisseyi seç:", hisse_listesi)
    if st.button("Seçili Hisseyi Sil"):
        st.session_state.df = st.session_state.df[st.session_state.df["Hisse"] != secili_hisse].reset_index(drop=True)
        st.warning(f"{secili_hisse} başarıyla silindi.")
        st.rerun()
