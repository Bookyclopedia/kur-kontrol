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
        # Virgüllü veya noktalı girişi kabul eden metin kutusu
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

# --- HESAPLAMA VE MANTIK ---
if st.button("KONTROL ET", use_container_width=True, type="primary"):
    # Metin girişlerini sistemin anlayacağı tarih ve rakamlara çevirme
    try:
        f_tarih = datetime.strptime(f_tarih_str.strip(), "%d/%m/%Y").date()
        f_saat = datetime.strptime(f_saat_str.strip(), "%H:%M").time()
        
        # Kullanıcı virgül girerse noktaya çevir
        fatura_tl = float(fatura_tl_str.replace(",", "."))
        siparis_doviz = float(siparis_doviz_str.replace(",", "."))
    except ValueError:
        st.error("⚠️ Lütfen tarih (Örn: 25/04/2026), saat (Örn: 14:30) ve tutar bilgilerini doğru formatta girin.")
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

            # YENİ KONTROL MANTIĞI
            if fatura_tl > beklenen_tl + 0.10: 
                # Durum 1: Fatura yüksek kesilmiş (Aleyhimize)
                fark = fatura_tl - beklenen_tl
                st.error(f"❌ **FARK VAR:** Fatura olması gerekenden **{fark:,.2f} TL FAZLA** kesilmiş!")
                
            elif fatura_tl < beklenen_tl - 0.10: 
                # Durum 2: Fatura düşük kesilmiş (Lehimize)
                fark = beklenen_tl - fatura_tl
                if fark >= 100:
                    st.warning(f"📉 **BİLGİ:** Firma faturayı **{fark:,.2f} TL DÜŞÜK** kesmiştir.")
                else:
                    st.success(f"✅ **UYUMLU:** Fatura lehimize ufak bir farkla ({fark:,.2f} TL düşük) uygun kesilmiş.")
                    
            else:
                # Durum 3: Tam eşleşme (Kuruşluk farklar hariç)
                st.success("✅ **TAM UYUMLU:** Fatura tutarı kur ile eşleşiyor.")
        else:
            st.error("TCMB verilerine ulaşılamadı. Lütfen tarihi kontrol edin.")