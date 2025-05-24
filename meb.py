import requests
import json
from bs4 import BeautifulSoup
import urllib3
import re
import time
from test_tureng import TurengCeviri
from deep_translator import GoogleTranslator

# SSL uyarılarını sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TDKKelimeAnalizi:
    def __init__(self):
        self.base_url = "https://sozluk.gov.tr/gts"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Referer': 'https://sozluk.gov.tr/',
            'Content-Type': 'application/json'
        }
    
    def es_ve_zit_anlamli_cek(self, anlam_metni):
        """
        Anlam metninden eş anlamlı ve zıt anlamlı kelimeleri çıkarır
        """
        es_anlamli = []
        zit_anlamli = []
        
        # Noktalı virgül sonrası eş anlamlıları yakala
        if ';' in anlam_metni:
            parcalar = anlam_metni.split(';')
            if len(parcalar) > 1:
                es_anlamli_kisim = parcalar[1].strip()
                # Virgülle ayrılmış kelimeleri al
                es_kelimeler = [k.strip() for k in es_anlamli_kisim.split(',')]
                # Temizle
                for kelime in es_kelimeler:
                    # Parantez içini çıkar: "mama (II)" -> "mama"
                    kelime = re.sub(r'\s*\([^)]*\)', '', kelime)
                    # Özel karakterleri temizle
                    kelime = re.sub(r'[►▲▼◄►]', '', kelime).strip()
                    if kelime and len(kelime) > 1:
                        es_anlamli.append(kelime)
        
        # Zıt anlamlıları yakala - "karşıtı" ifadesi varsa
        if 'karşıtı' in anlam_metni.lower():
            # "X, Y karşıtı" formatını yakala
            karsi_pattern = r'([^,;]+),?\s*karşıtı'
            matches = re.findall(karsi_pattern, anlam_metni, re.IGNORECASE)
            for match in matches:
                # Virgülle ayrılmış zıt anlamlıları al
                zit_kelimeler = [k.strip() for k in match.split(',')]
                for kelime in zit_kelimeler:
                    kelime = re.sub(r'[►▲▼◄►]', '', kelime).strip()
                    if kelime and len(kelime) > 1:
                        zit_anlamli.append(kelime)
        
        # "zıttı" ifadesi varsa
        if 'zıttı' in anlam_metni.lower():
            zit_pattern = r'([^,;]+),?\s*zıttı'
            matches = re.findall(zit_pattern, anlam_metni, re.IGNORECASE)
            for match in matches:
                zit_kelimeler = [k.strip() for k in match.split(',')]
                for kelime in zit_kelimeler:
                    kelime = re.sub(r'[►▲▼◄►]', '', kelime).strip()
                    if kelime and len(kelime) > 1:
                        zit_anlamli.append(kelime)
        
        return list(set(es_anlamli)), list(set(zit_anlamli))
    
    def atasozleri_cek(self, kelime):
        """
        Kelime ile ilgili atasözlerini çeker
        """
        try:
            url = "https://sozluk.gov.tr/atasozu"
            params = {'ara': kelime}
            response = requests.get(url, params=params, headers=self.headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # İlk 3 atasözünü al
                    atasozleri = []
                    for item in data[:3]:
                        if isinstance(item, dict) and 'madde' in item:
                            atasozleri.append(item['madde'])
                    return atasozleri
        except:
            pass
        return []
    
    def kelime_analiz_listesi(self, kelime):
        """
        Kelime analizini liste formatında döndürür
        """
        try:
            # TDK API'sine istek gönder
            params = {'ara': kelime}
            
            # Farklı yöntemler deneyerek bağlantı kurmaya çalış
            try:
                # İlk deneme: Normal HTTPS
                response = requests.get(
                    self.base_url, 
                    params=params, 
                    headers=self.headers,
                    timeout=15,
                    verify=True
                )
                response.raise_for_status()
                
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
                # İkinci deneme: SSL doğrulaması olmadan
                response = requests.get(
                    self.base_url, 
                    params=params, 
                    headers=self.headers,
                    timeout=15,
                    verify=False
                )
                response.raise_for_status()
            
            # JSON yanıtını parse et
            data = response.json()
            
            if not data or len(data) == 0:
                return {"hata": f"'{kelime}' kelimesi TDK sözlüğünde bulunamadı."}
            
            sonuclar = []
            
            for i, anlam_grubu in enumerate(data):
                if 'anlamlarListe' in anlam_grubu:
                    telaffuz = anlam_grubu.get('telaffuz', '')
                    
                    # Kelime kökeni bilgisi
                    lisan = anlam_grubu.get('lisan', '')
                    
                    # Birleşik kelimeler
                    birlesikler = anlam_grubu.get('birlesikler', '')
                    birlesik_liste = []
                    if birlesikler:
                        # Virgülle ayrılmış birleşik kelimeleri al (ilk 10'u)
                        birlesik_liste = [b.strip() for b in birlesikler.split(',')[:10]]
                    
                    # Ana objede bulunan atasözleri
                    atasozu_listesi = anlam_grubu.get('atasozu', [])
                    ana_atasozleri = []
                    if atasozu_listesi:
                        for atasozu in atasozu_listesi[:3]:  # İlk 3'ü al
                            if isinstance(atasozu, dict) and 'madde' in atasozu:
                                ana_atasozleri.append(atasozu['madde'])
                    
                    # Her anlam için ayrı sonuç oluştur
                    anlamlar_ve_turleri = []
                    tum_es_anlamli = set()
                    tum_zit_anlamli = set()
                    
                    for anlam in anlam_grubu['anlamlarListe']:
                        # Bu anlamın kelime türünü ve özelliklerini bul
                        kelime_turu = 'Belirtilmemiş'
                        ozellikler = []
                        
                        if 'ozelliklerListe' in anlam:
                            for ozellik in anlam['ozelliklerListe']:
                                tur = ozellik.get('tur')
                                tam_adi = ozellik.get('tam_adi', '')
                                
                                if tur == '3':  # Kelime türü
                                    kelime_turu = tam_adi
                                elif tur == '4':  # Özellik
                                    ozellikler.append(tam_adi)
                        
                        # Özel durum: nesnesiz, -e, -i kelimeleri fiil yap
                        nesnesiz_var = 'nesnesiz' in [o.lower() for o in ozellikler]
                        if nesnesiz_var or kelime_turu in ['-e', '-i']:
                            kelime_turu = 'fiil'
                            # Nesnesiz özelliğini çıkar
                            ozellikler = [o for o in ozellikler if o.lower() != 'nesnesiz']
                        
                        # Özellikte "nesnesiz" varsa ve kelime türü belirlenmemişse fiil yap
                        if 'nesnesiz' in [o.lower() for o in ozellikler] and kelime_turu == 'Belirtilmemiş':
                            kelime_turu = 'fiil'
                            ozellikler = [o for o in ozellikler if o.lower() != 'nesnesiz']
                        
                        # Nesnesiz kelime türünü fiil yap
                        if kelime_turu.lower() == 'nesnesiz':
                            kelime_turu = 'fiil'
                        
                        # Eğer kelime türü hala bulunamadıysa akıllı tahmin yap
                        if kelime_turu == 'Belirtilmemiş':
                            # Diğer anlamlardan dominant kelime türünü bul
                            for diger_anlam in anlam_grubu['anlamlarListe']:
                                if 'ozelliklerListe' in diger_anlam:
                                    for ozellik in diger_anlam['ozelliklerListe']:
                                        if ozellik.get('tur') == '3':
                                            kelime_turu = ozellik.get('tam_adi', 'isim')
                                            break
                                if kelime_turu != 'Belirtilmemiş':
                                    break
                            
                            # Hala bulunamadıysa mecaz varsa isim varsay
                            if kelime_turu == 'Belirtilmemiş' and 'mecaz' in ozellikler:
                                kelime_turu = 'isim'
                            
                            # Son çare: default isim
                            if kelime_turu == 'Belirtilmemiş':
                                kelime_turu = 'isim'
                        
                        # Kelime türü ve özellikleri birleştir
                        tur_metni = kelime_turu
                        if ozellikler:
                            tur_metni += ', ' + ', '.join(ozellikler)
                        
                        # Son kontrol: tur_metni'nde nesnesiz varsa fiil yap
                        if 'nesnesiz' in tur_metni.lower():
                            tur_metni = 'fiil'
                            if ', mecaz' in tur_metni.lower():
                                tur_metni = 'fiil, mecaz'
                        
                        # -e ve -i kelime türlerini de fiil yap
                        if tur_metni in ['-e', '-i']:
                            tur_metni = 'fiil'
                        
                        # Anlamı temizle
                        anlam_metni = anlam.get('anlam', '')
                        if anlam_metni:
                            soup = BeautifulSoup(anlam_metni, 'html.parser')
                            temiz_anlam = soup.get_text().strip()
                            temiz_anlam = ' '.join(temiz_anlam.split())
                            
                            # Eş ve zıt anlamlıları çek
                            es_anlamli, zit_anlamli = self.es_ve_zit_anlamli_cek(temiz_anlam)
                            tum_es_anlamli.update(es_anlamli)
                            tum_zit_anlamli.update(zit_anlamli)
                            
                            anlamlar_ve_turleri.append({
                                'kelime_turu': tur_metni,
                                'anlam': temiz_anlam,
                                'es_anlamli': es_anlamli,
                                'zit_anlamli': zit_anlamli
                            })
                    
                    # Ek atasözlerini API'den çek
                    ek_atasozleri = self.atasozleri_cek(kelime)
                    
                    # Sadece ilk 3 atasözünü al
                    tum_atasozleri = (ana_atasozleri + ek_atasozleri)[:3]
                    
                    # Sonucu kaydet
                    sonuc = {
                        'kelime': kelime,
                        'telaffuz': telaffuz,
                        'lisan': lisan,
                        'birlesikler': birlesik_liste,
                        'atasozleri': tum_atasozleri,
                        'anlamlar_ve_turleri': anlamlar_ve_turleri,
                        'tum_es_anlamli': list(tum_es_anlamli),
                        'tum_zit_anlamli': list(tum_zit_anlamli)
                    }
                    
                    sonuclar.append(sonuc)
            
            return sonuclar
            
        except requests.exceptions.RequestException as e:
            return {"hata": f"API'ye bağlanırken hata oluştu: {str(e)}"}
        except json.JSONDecodeError:
            return {"hata": "API'den alınan yanıt işlenirken hata oluştu."}
        except Exception as e:
            return {"hata": f"Beklenmeyen bir hata oluştu: {str(e)}"}

    def kelime_turunu_al(self, kelime):
        """
        TDK API'sinden kelimenin türünü çeker
        """
        try:
            # TDK API'sine istek gönder
            params = {'ara': kelime}
            
            # Farklı yöntemler deneyerek bağlantı kurmaya çalış
            try:
                # İlk deneme: Normal HTTPS
                response = requests.get(
                    self.base_url, 
                    params=params, 
                    headers=self.headers,
                    timeout=15,
                    verify=True
                )
                response.raise_for_status()
                
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
                # İkinci deneme: SSL doğrulaması olmadan
                response = requests.get(
                    self.base_url, 
                    params=params, 
                    headers=self.headers,
                    timeout=15,
                    verify=False
                )
                response.raise_for_status()
            
            # JSON yanıtını parse et
            data = response.json()
            
            if not data or len(data) == 0:
                return f"'{kelime}' kelimesi TDK sözlüğünde bulunamadı."
            
            sonuclar = []
            
            for i, anlam_grubu in enumerate(data):
                if 'anlamlarListe' in anlam_grubu:
                    telaffuz = anlam_grubu.get('telaffuz', '')
                    
                    # Kelime kökeni bilgisi
                    lisan = anlam_grubu.get('lisan', '')
                    
                    # Birleşik kelimeler
                    birlesikler = anlam_grubu.get('birlesikler', '')
                    birlesik_liste = []
                    if birlesikler:
                        # Virgülle ayrılmış birleşik kelimeleri al (ilk 10'u)
                        birlesik_liste = [b.strip() for b in birlesikler.split(',')[:10]]
                    
                    # Ana objede bulunan atasözleri
                    atasozu_listesi = anlam_grubu.get('atasozu', [])
                    ana_atasozleri = []
                    if atasozu_listesi:
                        for atasozu in atasozu_listesi[:3]:  # İlk 3'ü al
                            if isinstance(atasozu, dict) and 'madde' in atasozu:
                                ana_atasozleri.append(atasozu['madde'])
                    
                    # Her anlam için ayrı sonuç oluştur
                    anlamlar_ve_turleri = []
                    tum_es_anlamli = set()
                    tum_zit_anlamli = set()
                    
                    for anlam in anlam_grubu['anlamlarListe']:
                        # Bu anlamın kelime türünü ve özelliklerini bul
                        kelime_turu = 'Belirtilmemiş'
                        ozellikler = []
                        
                        if 'ozelliklerListe' in anlam:
                            for ozellik in anlam['ozelliklerListe']:
                                tur = ozellik.get('tur')
                                tam_adi = ozellik.get('tam_adi', '')
                                
                                if tur == '3':  # Kelime türü
                                    kelime_turu = tam_adi
                                elif tur == '4':  # Özellik
                                    ozellikler.append(tam_adi)
                        
                        # Özel durum: nesnesiz, -e, -i kelimeleri fiil yap
                        nesnesiz_var = 'nesnesiz' in [o.lower() for o in ozellikler]
                        if nesnesiz_var or kelime_turu in ['-e', '-i']:
                            kelime_turu = 'fiil'
                            # Nesnesiz özelliğini çıkar
                            ozellikler = [o for o in ozellikler if o.lower() != 'nesnesiz']
                        
                        # Özellikte "nesnesiz" varsa ve kelime türü belirlenmemişse fiil yap
                        if 'nesnesiz' in [o.lower() for o in ozellikler] and kelime_turu == 'Belirtilmemiş':
                            kelime_turu = 'fiil'
                            ozellikler = [o for o in ozellikler if o.lower() != 'nesnesiz']
                        
                        # Nesnesiz kelime türünü fiil yap
                        if kelime_turu.lower() == 'nesnesiz':
                            kelime_turu = 'fiil'
                        
                        # Eğer kelime türü hala bulunamadıysa akıllı tahmin yap
                        if kelime_turu == 'Belirtilmemiş':
                            # Diğer anlamlardan dominant kelime türünü bul
                            for diger_anlam in anlam_grubu['anlamlarListe']:
                                if 'ozelliklerListe' in diger_anlam:
                                    for ozellik in diger_anlam['ozelliklerListe']:
                                        if ozellik.get('tur') == '3':
                                            kelime_turu = ozellik.get('tam_adi', 'isim')
                                            break
                                if kelime_turu != 'Belirtilmemiş':
                                    break
                            
                            # Hala bulunamadıysa mecaz varsa isim varsay
                            if kelime_turu == 'Belirtilmemiş' and 'mecaz' in ozellikler:
                                kelime_turu = 'isim'
                            
                            # Son çare: default isim
                            if kelime_turu == 'Belirtilmemiş':
                                kelime_turu = 'isim'
                        
                        # Kelime türü ve özellikleri birleştir
                        tur_metni = kelime_turu
                        if ozellikler:
                            tur_metni += ', ' + ', '.join(ozellikler)
                        
                        # Son kontrol: tur_metni'nde nesnesiz varsa fiil yap
                        if 'nesnesiz' in tur_metni.lower():
                            tur_metni = 'fiil'
                            if ', mecaz' in tur_metni.lower():
                                tur_metni = 'fiil, mecaz'
                        
                        # -e ve -i kelime türlerini de fiil yap
                        if tur_metni in ['-e', '-i']:
                            tur_metni = 'fiil'
                        
                        # Anlamı temizle
                        anlam_metni = anlam.get('anlam', '')
                        if anlam_metni:
                            soup = BeautifulSoup(anlam_metni, 'html.parser')
                            temiz_anlam = soup.get_text().strip()
                            temiz_anlam = ' '.join(temiz_anlam.split())
                            
                            # Eş ve zıt anlamlıları çek
                            es_anlamli, zit_anlamli = self.es_ve_zit_anlamli_cek(temiz_anlam)
                            tum_es_anlamli.update(es_anlamli)
                            tum_zit_anlamli.update(zit_anlamli)
                            
                            anlamlar_ve_turleri.append({
                                'kelime_turu': tur_metni,
                                'anlam': temiz_anlam,
                                'es_anlamli': es_anlamli,
                                'zit_anlamli': zit_anlamli
                            })
                    
                    # Ek atasözlerini API'den çek
                    ek_atasozleri = self.atasozleri_cek(kelime)
                    
                    # Sadile ilk 3 atasözünü al
                    tum_atasozleri = (ana_atasozleri + ek_atasozleri)[:3]
                    
                    # Sonucu kaydet
                    sonuc = {
                        'kelime': kelime,
                        'telaffuz': telaffuz,
                        'lisan': lisan,
                        'birlesikler': birlesik_liste,
                        'ana_atasozleri': ana_atasozleri,
                        'ek_atasozleri': ek_atasozleri,
                        'anlamlar_ve_turleri': anlamlar_ve_turleri,
                        'tum_es_anlamli': list(tum_es_anlamli),
                        'tum_zit_anlamli': list(tum_zit_anlamli)
                    }
                    
                    sonuclar.append(sonuc)
            
            return self.sonuclari_formatla(sonuclar)
            
        except requests.exceptions.RequestException as e:
            return f"API'ye bağlanırken hata oluştu: {str(e)}"
        except json.JSONDecodeError:
            return "API'den alınan yanıt işlenirken hata oluştu."
        except Exception as e:
            return f"Beklenmeyen bir hata oluştu: {str(e)}"
    
    def sonuclari_formatla(self, sonuclar):
        """
        Sonuçları terminal için formatlar
        """
        if not sonuclar:
            return "Kelime bulunamadı."
        
        formatli_sonuc = "\n"
        formatli_sonuc += "="*60 + "\n"
        formatli_sonuc += "🇹TDK KELİME ANALİZİ SONUCU\n"
        formatli_sonuc += "="*60 + "\n"
        
        for i, sonuc in enumerate(sonuclar, 1):
            formatli_sonuc += f"\n{sonuc['kelime'].upper()}\n"
            
            if sonuc['telaffuz']:
                formatli_sonuc += f"Telaffuz: {sonuc['telaffuz']}\n"
            
            if sonuc['lisan']:
                formatli_sonuc += f"Kökeni: {sonuc['lisan']}\n"
            
            # Genel eş ve zıt anlamlıları göster
            if sonuc['tum_es_anlamli']:
                formatli_sonuc += f"Eş Anlamlıları: {', '.join(sonuc['tum_es_anlamli'])}\n"
            
            if sonuc['tum_zit_anlamli']:
                formatli_sonuc += f"Zıt Anlamlıları: {', '.join(sonuc['tum_zit_anlamli'])}\n"
            
            # Birleşik kelimeler
            if sonuc['birlesikler']:
                formatli_sonuc += f"Birleşik Kelimeler: {', '.join(sonuc['birlesikler'])}\n"
            
            # Atasözleri
            tum_atasozleri = sonuc['ana_atasozleri'] + sonuc['ek_atasozleri']
            if tum_atasozleri:
                formatli_sonuc += f"Atasözleri:\n"
                for atasozu in tum_atasozleri[:3]:  # İlk 3'ünü göster
                    formatli_sonuc += f"   • {atasozu}\n"
            
            formatli_sonuc += f"\nAnlamlar:\n"
            for j, item in enumerate(sonuc['anlamlar_ve_turleri'], 1):
                formatli_sonuc += f"   {j}. Kelime Türü: {item['kelime_turu']}\n"
                formatli_sonuc += f"Anlam: {item['anlam']}\n"
            
            
            if i < len(sonuclar):
                formatli_sonuc += "-"*40 + "\n"
        
        formatli_sonuc += "="*60 + "\n"
        return formatli_sonuc

class TurengCeviri:
    def __init__(self):
        self.translator = GoogleTranslator(source='tr', target='en')
    
    def kelime_cevir(self, kelime):
        """
        Türkçe kelimenin İngilizce çevirisini getirir
        """
        try:
            # Google Translate ile çeviri yap
            translation = self.translator.translate(text=kelime)
            
            if translation:
                return translation
            
            return None
            
        except Exception as e:
            print(f"Çeviri hatası: {str(e)}")
            return None

def kelime_basliklarini_al(analyzer, kelime):
    """
    Kelimeyi analiz edip başlık: değer formatında return eder
    """
    sonuc = analyzer.kelime_analiz_listesi(kelime)
    
    if isinstance(sonuc, dict) and 'hata' in sonuc:
        return f"Hata: {sonuc['hata']}"
    
    if not sonuc:
        return "Kelime bulunamadı"
    
    # İlk sonuçtan verileri al
    if len(sonuc) > 0:
        veri = sonuc[0]
        
        sonuc_dict = {}
        
        # Ana verileri ekle
        sonuc_dict['kelime'] = veri.get('kelime', '-')
        sonuc_dict['telaffuz'] = veri.get('telaffuz', '-') if veri.get('telaffuz') else '-'
        sonuc_dict['lisan'] = veri.get('lisan', '-') if veri.get('lisan') else '-'
        sonuc_dict['birlesikler'] = ', '.join(veri.get('birlesikler', [])) if veri.get('birlesikler') else '-'
        sonuc_dict['atasozleri'] = ', '.join(veri.get('atasozleri', [])) if veri.get('atasozleri') else '-'
        sonuc_dict['tum_es_anlamli'] = ', '.join(veri.get('tum_es_anlamli', [])) if veri.get('tum_es_anlamli') else '-'
        sonuc_dict['tum_zit_anlamli'] = ', '.join(veri.get('tum_zit_anlamli', [])) if veri.get('tum_zit_anlamli') else '-'
        
        # Anlamları ekle
        anlamlar = []
        if 'anlamlar_ve_turleri' in veri and veri['anlamlar_ve_turleri']:
            for i, anlam in enumerate(veri['anlamlar_ve_turleri'], 1):
                anlam_str = f"{i}. Tür: {anlam.get('kelime_turu', '-')}, Anlam: {anlam.get('anlam', '-')}"
                anlamlar.append(anlam_str)
        
        sonuc_dict['anlamlar'] = anlamlar if anlamlar else ['-']
        
        # Google Translate çevirilerini ekle
        tureng = TurengCeviri()
        ceviri = tureng.kelime_cevir(kelime)
        
        if ceviri:
            sonuc_dict['google_ceviri'] = ceviri
        else:
            sonuc_dict['google_ceviri'] = '-'
        
        return sonuc_dict
    
    return "Veri bulunamadı"

def main():
    
    print("="*40)
    print("Çıkmak için 'q' yazın.\n")
    
    analyzer = TDKKelimeAnalizi()
    
    while True:
        try:
            kelime = input("Kelime girin: ").strip()
            
            if not kelime:
                print("Lütfen bir kelime girin.\n")
                continue
                
            if kelime.lower() in ['q', 'quit', 'çık', 'exit']:
                print("Program sonlandırılıyor")
                break
            
            # Analiz et
            sonuc = kelime_basliklarini_al(analyzer, kelime)
            
            if isinstance(sonuc, dict):
                print(f"\n=== '{kelime}' KELİMESİ ANALİZİ ===")               
                print(f"Kelime: {sonuc['kelime']}")
                print(f"Telaffuz: {sonuc['telaffuz']}")
                print(f"Lisan: {sonuc['lisan']}")
                print(f"Birleşikler: {sonuc['birlesikler']}")
                print(f"Atasözleri: {sonuc['atasozleri']}")
                print(f"Eş Anlamlılar: {sonuc['tum_es_anlamli']}")
                print(f"Zıt Anlamlılar: {sonuc['tum_zit_anlamli']}")
                
                print("\nAnlamlar:")
                for anlam in sonuc['anlamlar']:
                    print(f"  {anlam}")
                
                print(f"\nİngilizcesi:")
                print(f"  {sonuc['google_ceviri']}")
                
                print("=" * 40)
            else:
                print(sonuc)
            
        except KeyboardInterrupt:
            print("\n\nProgram sonlandırılıyor")
            break
        except Exception as e:
            print(f"Hata: {e}\n")

if __name__ == "__main__":
    main()
