import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- GOOGLE SHEETS AYARLARI ---
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

def tr_format(val):
    try:
        return "{:,.2f}".format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Halka Arz & Borsa Takip v10", layout="wide")

# Kar/Zarar Renk Tasarımı
st.markdown("""
    <style>
    [data-testid='stMetricValue'] { font-size: 45px !important;  font-color: #008000 !important; font-weight: bold !important; }
    .stMetric { border-radius: 15px; padding: 15px; border: 1px solid #e6e9ef; background-color: #000000; }
    </style>
    """, unsafe_allow_html=True)

st.title("💹 Portföy Yönetim Paneli")

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME VE TEMİZLEME ---
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
    else:
        df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

    # Eksik Sütun Kontrolü
    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"
    
    # SAYI TEMİZLEME (Kritik Nokta)
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        # Önce virgülleri temizleyip noktaya çeviriyoruz ki Python doğru okusun
        df[col] = df[col].astype(str).str.replace(".", "").str.replace(",", ".")
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # ⚠️ MANUEL DÜZELTME: Eğer Kar 100.000'den büyükse muhtemelen 100 kat hatasıdır
    # Sadece Halka Arzlar için bu kontrolü yapıyoruz
    df.loc[(df["Tur"] == "Halka Arz") & (df["Kar"] > 50000), "Kar"] /= 100

except:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])

# --- YAN MENÜ ---
with st.sidebar:
    st.header("➕ Yeni İşlem")
    h_tur = st.radio("İşlem Türü", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_satis = st.number_input("Satış / Güncel Fiyat", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot (Tek Hesap)", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=2)
    
    if h_lot > 0:
        gecici_kar = (h_satis - h_alis) * h_lot * h_hesap
        st.info(f"Hesaplanan Kar: {tr_format(gecici_kar)} TL")
        if st.button("✅ Kaydet"):
            yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": gecici_kar, "Tur": h_tur}
            if h_adi in df["Hisse"].values:
                df = df[df["Hisse"] != h_adi] # Eskisini sil yenisini ekle (Güncelleme)
            df = pd.concat([df, pd.DataFrame([yeni])], ignore_index=True)
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
            st.rerun()

    st.write("---")
    if st.button("🚨 TÜM TABLOYU SIFIRLA"):
        sheet.clear()
        sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
        st.rerun()

# --- ÜST ÖZET ---
col1, col2 = st.columns(2)
halka_arz_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
normal_borsa_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

with col1:
    st.metric("🚀 TOPLAM HALKA ARZ", f"{tr_format(halka_arz_kar)} TL")


with col2:
    color = "normal" if normal_borsa_kar >= 0 else "inverse"
    st.metric("📊 NORMAL BORSA DURUM", f"{tr_format(normal_borsa_kar)} TL", delta=f"{tr_format(normal_borsa_kar)} TL", delta_color=color)

# --- TABLOLAR ---
tab1, tab2 = st.tabs(["🎁 Halka Arzlarım", "💹 Normal Hisse Portföy"])

with tab1:
    df_ha = df[df["Tur"] == "Halka Arz"].copy()
    if not df_ha.empty:
        for c in ["Alis", "Satis", "Kar"]: df_ha[c] = df_ha[c].apply(tr_format)
        st.dataframe(df_ha[["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)

with tab2:
    df_nb = df[df["Tur"] == "Normal Borsa"].copy()
    if not df_nb.empty:
        for c in ["Alis", "Satis", "Kar"]: df_nb[c] = df_nb[c].apply(tr_format)
        st.dataframe(df_nb[["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar"]], use_container_width=True, hide_index=True)
    else:
        st.info("Normal borsa hissesi henüz eklenmemiş.")
