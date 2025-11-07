# Ebelik Araştırması İstatistiksel Analiz Motoru (TÜBİTAK 2209-A Projesi)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tubitak-2209a-ebelik-projesi-calismasi.streamlit.app)

Bu proje, bir **TÜBİTAK 2209-A** araştırma projesi kapsamında geliştirilen, ebelik bilim dalında yapılan randomize kontrollü bir deneyi (RCT) analiz etmek için tasarlanmış **Python tabanlı bir "Uzman Sistem" web uygulamasıdır.**

Uygulamanın temel amacı, karmaşık istatistiksel analiz sürecini (FAZ 1 denklik testleri, FAZ 2 ANCOVA, dinamik düzeltme ve görselleştirme) otomatize ederek, teknik istatistik bilgisi olmayan sağlık profesyonellerinin (ebeler, doktorlar, araştırmacılar) bile kendi verilerini kolayca analiz etmesini, yorumlamasını ve raporlamasını sağlamaktır.

## 🚀 Canlı Uygulamaya Erişim

Bu "Uzman Analiz Sistemi"ni **canlı olarak test etmek, şablonu indirmek ve kendi verilerinizi analiz etmek** için aşağıdaki linki (sizin talebiniz üzerine oluşturulan URL) kullanabilirsiniz:

### **[https://tubitak-2209a-ebelik-projesi-calismasi.streamlit.app](https://tubitak-2209a-ebelik-projesi-calismasi.streamlit.app)**

---

## 📸 Uygulama Arayüzü

<img width="1908" height="885" alt="Ekran görüntüsü 2025-11-08 023222" src="https://github.com/user-attachments/assets/ddd09fb7-176f-4593-af99-52b86d306b97" />


---

## ✨ Temel Özellikler

Bu uygulama, basit bir veri yükleyiciden çok daha fazlasıdır. Bir "Uzman Sistem" olarak şu karmaşık işlemleri otomatik olarak gerçekleştirir:

1.  **Kullanıcı Dostu Şablon Yöntemi (v10.0)**
    * Teknik olmayan kullanıcıların sütun adlarıyla boğuşmaması için, sistemin beklediği tüm sütunları içeren **boş bir Excel şablonu** sunar. Kullanıcı, verilerini bu şablona girip yükler, böylece `KeyError` (sütun hatası) riski sıfıra iner.

2.  **Otomatik Veri Temizleme (v12.1)**
    * Kullanıcıların Excel'e `7` (sayı) yerine `7,0` (virgül), `yok` veya `bilinmiyor` (metin) girmesinden kaynaklanan `agg function failed [dtype->object]` hatasını öngörür.
    * Analizden önce tüm sayısal sütunları otomatik olarak temizler (`pd.to_numeric(errors='coerce')`), "kirli" verileri boş değere (`NaN`) dönüştürür ve **programın çökmesini engeller.**

3.  **Gelişmiş Keşifsel Veri Analizi (EDA) Dashboard (v8.0)**
    * Veriyi sadece test etmez, aynı zamanda "📊 Veri Seti Özeti" sekmesinde derinlemesine görselleştirir. Bu sekme şunları içerir:
        * **Frekans Tabloları ve Pasta Grafikler:** Tüm sosyodemografik verilerin (medeni durum, gelir düzeyi vb.) yüzdesel ve sayısal (`n`) dağılımları.
        * **Kutu Grafikleri (Box Plots):** `Yaş` ve `Gebelik Haftası` gibi sayısal değişkenlerin gruplar arası denklik durumunun görsel kontrolü.
        * **Çizgi Grafikler (Line Plots):** "Müdahale" ve "Kontrol" gruplarının ortalama korku puanlarının (VAS, Ölçek) zaman içindeki (Baseline, 4cm, 8cm) evrimini gösterir.
        * **Likert-tipi Yığılmış Grafikler:** Korku puanlarını "Düşük/Orta/Yüksek" olarak kategorize eder ve bu dağılımın gruplar arasında zamanla nasıl değiştiğini gösterir (Müdahalenin etkisinin en net görüldüğü yer).
        * **Korelasyon Isı Haritası:** `Yaş`, `Gebelik Haftası` ve tüm `korku/endişe` puanları arasındaki gizli ilişkileri gösteren profesyonel bir ısı haritası.

4.  **Akıllı İstatistiksel Analiz Motoru (Dinamik Düzeltme) (v6.0)**
    * **FAZ 1 (Denklik):** Yüklenen verinin FAZ 1 denklik testlerini (t-Testi, Ki-Kare) otomatik olarak yapar.
    * **AKILLI DÜZELTME:** Eğer FAZ 1'de bir denklik hatası bulursa (örn: `gelir_duzeyi` p < 0.05), sadece hata verip durmaz. Bir istatistikçi gibi davranır, bu "sorunlu" değişkeni (`gelir_duzeyi`) bir "karıştırıcı değişken" (confounder) olarak belirler.
    * **FAZ 2 (ANCOVA):** H1, H2 ve H3 hipotezlerini test ederken, FAZ 1'de bulduğu "sorunlu" değişkeni ANCOVA formülüne **otomatik olarak bir 'kovaryant' (kontrol değişkeni) olarak ekler.**
    * **Sonuç:** Çıkan p-değerleri, denklik hatasından arındırılmış, "düzeltilmiş" ve bilimsel olarak daha güvenilir sonuçlardır.

5.  **Kapsamlı ve Yorumlu PDF Raporu (v12.0)**
    * Analiz bittiğinde, "Raporu Dışa Aktar" butonu, tüm bu süreci özetleyen **çok sayfalı bir PDF** oluşturur:
        * **Sayfa 1-2:** FAZ 1 (Denklik) ve FAZ 2 (ANCOVA) test sonuçları.
        * **Sayfa 3:** "Nihai Rapor Yorumu" (Analist Özeti) - (örn: "Güçlü Bulgular" veya "Düzeltilmiş Bulgular").
        * **Sayfa 4-X (EK'ler):** "Dashboard" sekmesinde oluşturulan **tüm pasta, çizgi, kutu ve ısı haritası grafiklerini** otomatik olarak PDF'e resim olarak ekler.

---

## 🔧 Nasıl Kullanılır (Kullanıcı Rehberi)

Bu "Uzman Sistem"i kullanmak için teknik bilgiye gerek yoktur:

1.  **Adım 1: Şablonu İndirin**
    * Canlı uygulamanın sol menüsündeki (sidebar) **"Boş Excel Şablonunu İndir"** butonuna basın.

2.  **Adım 2: Verinizi Doldurun**
    * İndirdiğiniz `Ebelik_Veri_Giris_Sabloni.xlsx` dosyasını açın.
    * Kendi 120 (veya daha fazla) katılımcınızın verisini, şablondaki ilgili sütunların (`yas`, `grup`, `korku_vas_baseline` vb.) altına girin.
    * (Not: Sayısal sütunlara `yok`, `bilinmiyor` veya `7,0` (virgül) gibi metinler girmeniz sorun yaratmaz; v12.1'deki "Otomatik Veri Temizleme" motoru bunları görmezden gelecektir.)

3.  **Adım 3: Yükleyin ve Analiz Edin**
    * Doldurduğunuz Excel dosyasını Adım 2'deki "Şablonu Yükleyin" alanına sürükleyin.
    * Adım 3'teki **"Analizi Başlat"** butonuna basın.

4.  **Adım 4: Raporunuzu İnceleyin ve İndirin**
    * **"📊 Veri Seti Özeti"** sekmesine giderek verinizin görsel özetini (pasta, çizgi, ısı haritası) inceleyin.
    * **"📈 İstatistiksel Analiz"** sekmesine giderek p-değerlerini, hipotez sonuçlarını (DESTEKLENDİ/Reddedildi) ve "Nihai Rapor Yorumu"nu okuyun.
    * Raporun en altındaki **"Kapsamlı Raporu PDF Olarak İndir"** butonuna basarak tüm bu bulguları (metin + grafikler) bilgisayarınıza indirin.

---

## 🛠️ Teknoloji Mimarisi (Kullanılan Kütüphaneler)

Bu proje, aşağıdaki Python kütüphaneleri kullanılarak oluşturulmuştur:

* **Arayüz (Frontend):** `streamlit`
* **Veri İşleme (Backend):** `pandas` ve `numpy`
* **İstatistiksel Analiz:** `scipy` (t-test, Ki-Kare) ve `statsmodels` (ANCOVA)
* **Veri Görselleştirme:** `plotly` (İnteraktif Grafikler)
* **Raporlama (PDF):** `fpdf2` (PDF Oluşturma) ve `kaleido` (Grafikleri Resme Çevirme)
* **Dosya İşlemleri:** `openpyxl` (Excel Okuma/Yazma)


---
