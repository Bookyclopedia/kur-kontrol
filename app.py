import streamlit as st
from datetime import datetime, timedelta
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Kur Farkı Hesaplayıcı", layout="centered")
st.title("🏥 Fatura Kur Kontrol Sistemi")

# --- 1. ADIM: KULLANICI GİRİŞLERİ ---
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        fatura_tarihi = st.date_input("Fatura Tarihi", datetime.now())
        doviz_tipi = st.selectbox("Döviz Cinsi", ["EUR", "USD"])
    with col2:
        fatura_tl = st.number_input("Fatura Toplam (TL)", min_value=0.0, step=0.01)
        siparis_doviz = st.number_input(f"Sipariş Toplam ({doviz_tipi})", min_value=0.0, step=0.01)

# --- 2. ADIM: TCMB KUR ÇEKME FONKSİYONU (T-1 Mantığı) ---
def tcmb_kur_bul(tarih, doviz):
    # Bir gün öncesinden aramaya başla
    hedef_tarih = tarih - timedelta(days=1)
    
    # Maksimum 10 gün geriye git (Resmi tatiller ve hafta sonları için döngü)
    for _ in range(10):
        # Hafta sonu kontrolü
        if hedef_tarih.weekday() == 5: # Cumartesi -> Cuma'ya git
            hedef_tarih -= timedelta(days=1)
        if hedef_tarih.weekday() == 6: # Pazar -> Cuma'ya git
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
                        kur_degeri = float(c.find('ForexSelling').text)
                        return kur_degeri, hedef_tarih
            else:
                # O tarihte kur yoksa (Resmi tatil vb.), bir gün daha geriye git
                hedef_tarih -= timedelta(days=1)
        except:
            hedef_tarih -= timedelta(days=1)
    return None, None

# --- 3. ADIM: HESAPLAMA VE SONUÇ ---
if st.button("KONTROL ET VE HESAPLA"):
    if fatura_tl > 0 and siparis_doviz > 0:
        kur, bulunan_tarih = tcmb_kur_bul(fatura_tarihi, doviz_tipi)
        
        if kur:
            ic_kur = fatura_tl / siparis_doviz
            olmasi_gereken_tl = siparis_doviz * kur
            fark = fatura_tl - olmasi_gereken_tl
            
            st.markdown("---")
            st.write(f"🔍 **Baz Alınan Kur Tarihi:** {bulunan_tarih.strftime('%d.%m.%Y')}")
            st.write(f"📈 **TCMB Döviz Satış Kuru:** {kur:.4f}")
            
            if abs(ic_kur - kur) < 0.0001:
                st.success(f"✅ Kur eşleşti! (İç Kur: {ic_kur:.4f})")
            else:
                st.error(f"⚠️ Kur Farkı Tespit Edildi!")
                st.metric("Ödenen / Fatura TL", f"{fatura_tl:,.2f} TL")
                st.metric("Olması Gereken TL", f"{olmasi_gereken_tl:,.2f} TL", delta=f"-{fark:,.2f} TL" if fark > 0 else f"{abs(fark):,.2f} TL")
                st.info(f"Fatura İç Kuru: {ic_kur:.4f} | Fark: {fark:,.2f} TL")
        else:
            st.error("TCMB verilerine ulaşılamadı. Lütfen internet bağlantısını kontrol edin.")
    else:
        st.warning("Lütfen tüm tutarları girin.")