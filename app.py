import streamlit as st
from datetime import datetime, timedelta, time
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Hızlı Kur Kontrol", layout="centered")
st.title("⚡ Hızlı Fatura Denetim Paneli")

# --- AKILLI FORMATLAYICI FONKSİYONLAR ---
def akilli_tarih_duzelt(metin):
    metin = metin.strip().replace(".", "").replace("/", "").replace("-", "")
    if len(metin) == 8: # Örn: 28042026 -> 28/04/2026
        return f"{metin[:2]}/{metin[2:4]}/{metin[4:]}"
    return metin

def akilli_saat_duzelt(metin):
    metin = metin.strip().replace(":", "").replace(".", "")
    if len(metin) == 4: # Örn: 1030 -> 10:30
        return f"{metin[:2]}:{metin[2:]}"
    return metin

def tutar_temizle(metin):
    if not metin: return 0.0
    metin = metin.strip().replace(" ", "")
    if "." in metin and "," in metin:
        metin = metin.replace(".", "").replace(",", ".")
    elif "," in metin:
        metin = metin.replace(",", ".")
    return float(metin)

# --- GİRİŞ ALANI ---
with st.container():
    st.info("💡 Tarihi '28042026', saati '1030' şeklinde sadece rakamla yazabilirsiniz.")
    
    c1, c2 = st.columns(2)
    with c1:
        f_tarih_raw = st.text_input("Fatura Tarihi", value=datetime.now().strftime("%d%m%Y"), help="Örn: 28042026")
    with c2:
        f_saat_raw = st.text_input("Fatura Saati", value="10:00", help="Örn: 1030")

    doviz_tipi = st.radio("Döviz Türü", ["EUR", "USD"], horizontal=True)
    
    st.divider()
    
    c3, c4 = st.columns(2)
    with c3:
        fatura_tl_str = st.text_input("Fatura Toplam (TL)")
    with c4:
        siparis_doviz_str = st.text_input(f"Sipariş Toplam ({doviz_tipi})")

# --- TCMB MOTORU ---
def tcmb_kur_motoru(tarih_obj, saat_obj, doviz):
    sinir = time(15, 30)
    hedef = tarih_obj - timedelta(days=1) if saat_obj < sinir else tarih_obj
    
    for _ in range(10):
        if hedef.weekday() == 5: hedef -= timedelta(days=1)
        elif hedef.weekday() == 6: hedef -= timedelta(days=2)
        url = f"https://www.tcmb.gov.tr/kurlar/{hedef.strftime('%Y%m')}/{hedef.strftime('%d%m%Y')}.xml"
        try:
            res = requests.get(url)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for c in root.findall('Currency'):
                    if c.get('CurrencyCode') == doviz:
                        return float(c.find('ForexSelling').text), hedef
            hedef -= timedelta(days=1)
        except: hedef -= timedelta(days=1)
    return None, None

# --- HESAPLAMA ---
if st.button("HESAPLA", use_container_width=True, type="primary"):
    try:
        # Girdileri akıllıca düzelt
        tarih_final = akilli_tarih_duzelt(f_tarih_raw)
        saat_final = akilli_saat_duzelt(f_saat_raw)
        
        f_tarih = datetime.strptime(tarih_final, "%d/%m/%Y").date()
        f_saat = datetime.strptime(saat_final, "%H:%M").time()
        
        f_tl = tutar_temizle(fatura_tl_str)
        s_doviz = tutar_temizle(siparis_doviz_str)
        
        kur, baz_tarih = tcmb_kur_motoru(f_tarih, f_saat, doviz_tipi)
        
        if kur:
            olmasi_gereken = s_doviz * kur
            st.markdown(f"### 🗓️ Kur Tarihi: {baz_tarih.strftime('%d/%m/%Y')} | 💱 Kur: **{kur:.4f}**")
            
            if f_tl > olmasi_gereken + 0.10:
                fark = f_tl - olmasi_gereken
                st.error(f"⚠️ **FAZLA FATURA:** Olması gereken {olmasi_gereken:,.2f} TL iken, {fark:,.2f} TL fazla kesilmiş!")
            
            elif f_tl < olmasi_gereken - 0.10:
                fark = olmasi_gereken - f_tl
                if fark >= 100:
                    st.warning(f"📉 **DÜŞÜK FATURA:** Firma faturayı {fark:,.2f} TL eksik kesmiştir.")
                else:
                    st.success(f"✅ **UYGUN:** Lehimize küçük fark ({fark:,.2f} TL).")
            else:
                st.success("✅ **TAM UYUMLU:** Her şey doğru görünüyor.")
        else:
            st.error("Kur verisi çekilemedi.")
            
    except Exception as e:
        st.error(f"Hata: Lütfen girişleri kontrol edin. (Detay: {e})")