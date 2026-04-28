import streamlit as st
from datetime import datetime, timedelta, time
import requests
import xml.etree.ElementTree as ET

# Sayfa Genişliği ve Başlık
st.set_page_config(page_title="Hızlı Kur Kontrol", layout="centered")
st.title("📊 Fatura & Kur Mutabakat Paneli")

# --- TEK EKRAN TASARIMI ---
with st.container():
    st.info("💡 İpucu: Fatura saati 15:30'dan önceyse sistem otomatik olarak bir önceki iş gününe gider.")
    
    # 1. Satır: Tarih ve Saat (Yan Yana)
    col_tarih, col_saat = st.columns(2)
    with col_tarih:
        # Streamlit takvimi varsayılan olarak YYYY/MM/DD gelse de, format parametresiyle görüntülebilir
        f_tarih = st.date_input("Fatura Tarihi (Gün/Ay/Yıl)", datetime.now(), format="DD/MM/YYYY")
    with col_saat:
        f_saat = st.time_input("Fatura Saati", time(10, 0))

    # 2. Satır: Döviz Seçimi (Radyo Buton ile Çok Daha Hızlı)
    doviz_tipi = st.radio("Döviz Türü", ["EUR", "USD"], horizontal=True)

    st.divider()

    # 3. Satır: Tutarlar
    col_fatura, col_siparis = st.columns(2)
    with col_fatura:
        fatura_tl = st.number_input("Fatura Toplam (TL)", min_value=0.0, step=0.01, format="%.2f")
    with col_siparis:
        siparis_doviz = st.number_input(f"Sipariş Toplam ({doviz_tipi})", min_value=0.0, step=0.01, format="%.2f")

    # 4. Satır: Tolerans Ayarı (Hız için varsayılan 0.10 TL)
    tolerans = st.slider("Hata Toleransı (TL)", 0.00, 1.00, 0.10)

# --- TCMB HESAPLAMA MOTORU ---
def tcmb_kur_motoru(tarih, saat, doviz):
    # 15:30 Kuralı
    sinir = time(15, 30)
    if saat < sinir:
        hedef = tarih - timedelta(days=1)
    else:
        hedef = tarih

    # Geriye dönük iş günü tarama
    for _ in range(10):
        if hedef.weekday() == 5: # Cmt -> Cum
            hedef -= timedelta(days=1)
        elif hedef.weekday() == 6: # Paz -> Cum
            hedef -= timedelta(days=2)
            
        t_str = hedef.strftime("%d%m%Y")
        y_str = hedef.strftime("%Y%m")
        url = f"https://www.tcmb.gov.tr/kurlar/{y_str}/{t_str}.xml"
        
        try:
            res = requests.get(url)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for c in root.findall('Currency'):
                    if c.get('CurrencyCode') == doviz:
                        return float(c.find('ForexSelling').text), hedef
            hedef -= timedelta(days=1)
        except:
            hedef -= timedelta(days=1)
    return None, None

# --- SONUÇ EKRANI ---
if st.button("HESAPLA VE KONTROL ET", use_container_width=True, type="primary"):
    if fatura_tl > 0 and siparis_doviz > 0:
        kur, baz_tarih = tcmb_kur_motoru(f_tarih, f_saat, doviz_tipi)
        
        if kur:
            beklenen_tl = siparis_doviz * kur
            fark = fatura_tl - beklenen_tl
            ic_kur = fatura_tl / siparis_doviz
            
            st.markdown("---")
            
            # Sonuçları Metrik Kartları ile Göster
            m1, m2, m3 = st.columns(3)
            m1.metric("Baz Alınan Kur", f"{kur:.4f}")
            m2.metric("Kur Tarihi", baz_tarih.strftime("%d/%m/%Y"))
            m3.metric("Fark (TL)", f"{fark:,.2f} TL", delta=f"{fark:,.2f} TL", delta_color="inverse")

            # Durum Mesajları
            if abs(fark) <= tolerans:
                st.success(f"✅ **UYUMLU:** Fatura tutarı kur ile eşleşiyor. (İç Kur: {ic_kur:.4f})")
            else:
                st.error(f"⚠️ **FARK VAR:** Fatura ve sipariş arasında {fark:,.2f} TL fark tespit edildi.")
                st.warning(f"Olması gereken toplam: **{beklenen_tl:,.2f} TL**")
        else:
            st.error("❌ TCMB verilerine ulaşılamadı. Lütfen tarihi kontrol edin.")
    else:
        st.warning("⚠️ Lütfen tutar bilgilerini eksiksiz girin.")