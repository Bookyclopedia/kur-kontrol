import streamlit as st
from datetime import datetime, timedelta, time
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Kur Kontrol Sistemi", layout="centered")
st.title("📊 Fatura & Kur Mutabakat Paneli")

# --- MANUEL GİRİŞ EKRANI ---
with st.container():
    col_tarih, col_saat = st.columns(2)
    with col_tarih:
        f_tarih_str = st.text_input("Fatura Tarihi (GG/AA/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
    with col_saat:
        f_saat_str = st.text_input("Fatura Saati (SS:DD)", value="10:00")

    doviz_tipi = st.radio("Döviz Türü", ["EUR", "USD"], horizontal=True)
    st.divider()

    col_fatura, col_siparis = st.columns(2)
    with col_fatura:
        fatura_tl_str = st.text_input("Fatura Toplam Tutarı (TL)", placeholder="Örn: 1500.50")
    with col_siparis:
        siparis_doviz_str = st.text_input(f"Sipariş Toplam Tutarı ({doviz_tipi})", placeholder="Örn: 100")

# --- TCMB KUR MOTORU ---
def tcmb_kur_motoru(tarih_obj, saat_obj, doviz):
    sinir = time(15, 30)
    if saat_obj < sinir:
        hedef = tarih_obj - timedelta(days=1)
    else:
        hedef = tarih_obj

    for _ in range(10):
        if hedef.weekday() == 5: hedef -= timedelta(days=1)
        elif hedef.weekday() == 6: hedef -= timedelta(days=2)
            
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

# --- AKILLI TUTAR TEMİZLEYİCİ ---
def tutar_temizle(metin):
    if not metin:
        return 0.0
    metin = metin.strip()
    # Eğer kopyala-yapıştır ile "1.500,50" gibi binlik ayracı gelirse noktayı sil, virgülü nokta yap
    if "." in metin and "," in metin:
        metin = metin.replace(".", "").replace(",", ".")
    # Sadece virgül kullanıldıysa (Örn: 1500,50) noktaya çevir
    elif "," in metin:
        metin = metin.replace(",", ".")
    return float(metin)

# --- HESAPLAMA VE MANTIK ---
if st.button("KONTROL ET", use_container_width=True, type="primary"):
    # Boş alan kontrolü
    if not fatura_tl_str or not siparis_doviz_str:
        st.warning("⚠️ Lütfen fatura ve sipariş tutarlarını girin.")
        st.stop()

    try:
        # Kullanıcı tarih arasına nokta veya tire koyarsa takılmaması için düzeltme
        tarih_duzenli = f_tarih_str.strip().replace(".", "/").replace("-", "/")
        f_tarih = datetime.strptime(tarih_duzenli, "%d/%m/%Y").date()
        
        # Kullanıcı saate 14.30 yazarsa 14:30 olarak düzeltme
        saat_duzenli = f_saat_str.strip().replace(".", ":")
        f_saat = datetime.strptime(saat_duzenli, "%H:%M").time()
        
        fatura_tl = tutar_temizle(fatura_tl_str)
        siparis_doviz = tutar_temizle(siparis_doviz_str)
        
    except ValueError:
        st.error("⚠️ Lütfen tarih (Örn: 25/04/2026), saat (Örn: 14:30) ve tutar bilgilerini eksiksiz girin.")
        st.stop()

    if fatura_tl > 0 and siparis_doviz > 0:
        kur, baz_tarih = tcmb_kur_motoru(f_tarih, f_saat, doviz_tipi)
        
        if kur:
            beklenen_tl = siparis_doviz * kur
            
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Baz Alınan Kur", f"{kur:.4f}")
            m2.metric("Kur Tarihi", baz_tarih.strftime("%d/%m/%Y"))
            m3.metric("Olması Gereken", f"{beklenen_tl:,.2f} TL")

            # KONTROL MANTIĞI (100 TL ve Düşük Kesme Kuralları)
            if fatura_tl > beklenen_tl + 0.10: 
                fark = fatura_tl - beklenen_tl
                st.error(f"❌ **FARK VAR:** Fatura olması gerekenden **{fark:,.2f} TL FAZLA** kesilmiş!")
                
            elif fatura_tl < beklenen_tl - 0.10: 
                fark = beklenen_tl - fatura_tl
                if fark >= 100:
                    st.warning(f"📉 **BİLGİ:** Firma faturayı **{fark:,.2f} TL DÜŞÜK** kesmiştir.")
                else:
                    st.success(f"✅ **UYUMLU:** Fatura lehimize ufak bir farkla ({fark:,.2f} TL düşük) uygun kesilmiş.")
                    
            else:
                st.success("✅ **TAM UYUMLU:** Fatura tutarı kur ile eşleşiyor.")
        else:
            st.error("TCMB verilerine ulaşılamadı. Lütfen tarihi kontrol edin.")