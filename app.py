import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import re

# --- GOOGLE SHEETS AYARLARI ---
SHEET_ID = "16EPbOhnGAqFYqiFOrHXfJUpCKVO5wugkoP1f_49rcF4"

def get_client():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scopes))
    except: return None

def sayi_temizle(val):
    """Her türlü noktalama hatasını (166.944 vs 1.669) temizleyen motor"""
    if val is None or val == "": return 0.0
    s = str(val).strip()
    # Eğer sayı 1.669,44 gibi gelirse noktayı sil, virgülü noktaya çevir
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    
    # Sadece rakam ve nokta kalsın
    s = re.sub(r'[^\d.-]', '', s)
    try:
        res = float(s)
        # Halka arz koruması: Kar 50 bin üzeriyse kesin 100 kat hatasıdır
        if res > 50000: res /= 100
        return res
    except: return 0.0

def tr_format(val):
    """Ekranda 1.669,44 formatında gösterir"""
    try:
        return "{:,.2f}".format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")
    except: return str(val)

# --- TASARIM (SİYAH TEMA & NET RENKLER) ---
st.set_page_config(page_title="Borsa Pro Terminal v14", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0d11; color: #ffffff; }
    [data-testid='stMetricValue'] { font-size: 48px !important; font-weight: bold !important; }
    .stMetric { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 12px; padding: 25px; }
    
    /* Kazanç Yeşil, Zarar Kırmızı - Beyaz Yazı Sorunu Çözüldü */
    [data-testid='stMetricValue'] { color: #00ff41 !important; }
    [data-testid='stMetricDelta'] > div { color: #ff3131 !important; }
    
    h1, h2, h3, p, span, label { color: white !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0b0d11; }
    </style>
    """, unsafe_allow_html=True)

client = get_client()
if not client: st.stop()

# --- VERİ ÇEKME VE TEMİZLİK ---
sheet = client.open_by_key(SHEET_ID).sheet1
all_data = sheet.get_all_records()
df = pd.DataFrame(all_data)

if df.empty:
    df = pd.DataFrame(columns=["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
else:
    if "Tur" not in df.columns: df["Tur"] = "Halka Arz"
    for col in ["Alis", "Satis", "Lot", "Hesap", "Kar"]:
        df[col] = df[col].apply(sayi_temizle)

# --- YAN MENÜ ---
with st.sidebar:
    st.header("➕ Portföy İşlemleri")
    h_tur = st.radio("Kategori", ["Halka Arz", "Normal Borsa"])
    h_adi = st.text_input("Hisse Kodu").upper().strip()
    h_alis = st.number_input("Alış Fiyatı", value=0.0, format="%.2f")
    h_lot = st.number_input("Lot", value=0)
    h_hesap = st.selectbox("Hesap Sayısı", [1, 2, 3, 4], index=0)
    
    # Canlı fiyat çekme (Basitleştirildi)
    h_satis = st.number_input("Güncel/Satış Fiyatı", value=0.0, format="%.2f")
    if h_tur == "Normal Borsa" and h_adi:
        if st.button("🔍 Canlı Fiyat Getir"):
            try:
                p = yf.Ticker(f"{h_adi}.IS").fast_info['last_price']
                st.write(f"Canlı: {p:.2f} TL")
            except: st.error("Fiyat çekilemedi.")

    if st.button("💾 Kaydet ve Yedekle"):
        kar = (h_satis - h_alis) * h_lot * h_hesap
        yeni = {"Hisse": h_adi, "Alis": h_alis, "Satis": h_satis, "Lot": h_lot, "Hesap": h_hesap, "Kar": kar, "Tur": h_tur}
        df = pd.concat([df[df["Hisse"] != h_adi], pd.DataFrame([yeni])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.success("Google Sheets Güncellendi!")
        st.rerun()

# --- ANA PANEL ---
st.title("📟 Borsa Portföy Yönetimi")

ha_kar = df[df["Tur"] == "Halka Arz"]["Kar"].sum()
nb_kar = df[df["Tur"] == "Normal Borsa"]["Kar"].sum()

c1, c2 = st.columns(2)
with c1:
    st.metric("🎁 HALKA ARZ NET KAR", f"{tr_format(ha_kar)} TL")


with c2:
    delta_val = f"{tr_format(nb_kar)} TL"
    st.metric("📊 BORSA DURUMU", f"{tr_format(nb_kar)} TL", delta=delta_val if nb_kar < 0 else None)

tab1, tab2 = st.tabs(["💎 Halka Arz Verileri", "💹 Normal Borsa Portföy"])

with tab1:
    df_ha = df[df["Tur"] == "Halka Arz"].copy()
    for c in ["Alis", "Satis", "Kar"]: df_ha[c] = df_ha[c].apply(tr_format)
    st.dataframe(df_ha, use_container_width=True, hide_index=True)

with tab2:
    df_nb = df[df["Tur"] == "Normal Borsa"].copy()
    for c in ["Alis", "Satis", "Kar"]: df_nb[c] = df_nb[c].apply(tr_format)
    st.dataframe(df_nb, use_container_width=True, hide_index=True)

# --- YÖNETİM ---
st.write("---")
st.subheader("⚙️ Kayıt Silme")
col_s1, col_s2 = st.columns([3, 1])
with col_s1:
    sil_hisse = st.selectbox("Hisse Seçiniz:", ["-"] + df["Hisse"].tolist())
with col_s2:
    if sil_hisse != "-" and st.button("❌ Sil"):
        df = df[df["Hisse"] != sil_hisse]
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='RAW')
        st.rerun()

if st.button("🚨 TÜM VERİLERİ SIFIRLA VE TEMİZLE"):
    sheet.clear()
    sheet.append_row(["Hisse", "Alis", "Satis", "Lot", "Hesap", "Kar", "Tur"])
    st.rerun()
