import streamlit as st
from datetime import datetime, timedelta, time
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Pro Kur Kontrol", layout="wide")
st.title("🏥 Akıllı Kur Farkı & Tespit Sistemi")

# --- UI Düzenlemesi ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    doviz_tipi = st.selectbox("Döviz Cinsi", ["EUR", "USD"])
    tolerans = st.number_input("Tolerans Payı (TL)", value=0.05, step=0.01)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📅 Fatura Bilgileri")
    f_tarih = st.date_input("Fatura Tarihi", datetime.now())
    f_saat = st.time_input("Fatura Saati", time(10, 0)) # Varsayılan 10:00
    fatura_tl = st.number_input("Fatura Toplam Tutarı (TL)", min_value=0.0)

with col2:
    st.subheader("📦 Teslimat Detayı")
    teslimat_tipi = st.radio("Hesaplama Türü", ["Toplam Sipariş Tutarı", "Birim Fiyat x Adet"])
    
    if teslimat_tipi == "Toplam Sipariş Tutarı":
        siparis_doviz = st.number_input(f"Sipariş Toplamı ({doviz_tipi})", min_value=0.0)
    else:
        birim_fiyat = st.number_input(f"Birim Fiyat ({doviz_tipi})", min_value=0.0, format="%.4f")
        adet = st.number_input("Teslim Alınan Adet", min_value=0, step=1)
        siparis_doviz = birim_fiyat * adet
        st.info(f"Hesaplanan Tutar: {siparis_doviz:,.2f} {doviz_tipi}")

# --- TCMB Kur Çekme Mantığı (Gelişmiş) ---
def tcmb_kur_getir(f_tarih, f_saat, doviz):
    # 15:30 Kuralı: 15:30'dan önceyse bir gün önceye git
    sinir_saat = time(15, 30)
    if f_saat < sinir_saat:
        hedef_tarih = f_tarih - timedelta(days=1)
    else:
        hedef_tarih = f_tarih

    # Hafta sonu ve tatil kontrolü (Max 10 gün geri tarama)
    for _ in range(10):
        if hedef_tarih.weekday() == 5: # Cmt -> Cum
            hedef_tarih -= timedelta(days=1)
        if hedef_tarih.weekday() == 6: # Paz -> Cum
            hedef_tarih -= timedelta(days=2)
            
        str_tarih = hedef_tarih.strftime("%d%m%Y")
        ay_yil = hedef_tarih.strftime("%Y%m")
        url = f"https://www.tcmb.gov.tr/kurlar/{ay_yil}/{str_tarih}.xml"
        
        try:
            res = requests.get(url)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for c in root.findall('Currency'):
                    if c.get('CurrencyCode') == doviz:
                        return float(c.find('ForexSelling').text), hedef_tarih
            hedef_tarih -= timedelta(days=1)
        except:
            hedef_tarih -= timedelta(days=1)
    return None, None

# --- Hesaplama ---
if st.button("ANALİZ ET", use_container_width=True):
    if fatura_tl > 0 and siparis_doviz > 0:
        kur, baz_tarih = tcmb_kur_getir(f_tarih, f_saat, doviz_tipi)
        
        if kur:
            beklenen_tl = siparis_doviz * kur
            fark = fatura_tl - beklenen_tl
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Baz Alınan Kur", f"{kur:.4f}")
            c2.metric("Kur Tarihi", baz_tarih.strftime("%d.%m.%Y"))
            c3.metric("Hesaplanan Fark", f"{fark:,.2f} TL", delta=fark, delta_color="inverse")
            
            if abs(fark) <= tolerans:
                st.success("✅ Fatura tutarı kur ile uyumludur.")
            else:
                st.error(f"⚠️ {fark:,.2f} TL tutarında fark tespit edildi!")
        else:
            st.error("Kur verisi çekilemedi.")