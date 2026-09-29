# ⚡ Blöf-MüsaitlikTakip - Arkadaş Grubu Ders ve Müsaitlik Takip Sistemi

Üniversite ve okul arkadaş grubunun haftalık ders programlarını senkronize eden, seçilen gün ve saatte **kimlerin boş olduğunu en üstte**, **kimlerin ise saat kaça kadar dolu olduğunu altta** gösteren modern web uygulaması.

---

## 🌟 Öne Çıkan Özellikler

1. **Gelişmiş Giriş ve Üyelik Sistemi**:
   - İsim, e-posta ve şifre ile hızlı kayıt.
   - **Büyük/Küçük Harf Duyarsızlığı**: Kullanıcı adı aramalarında ve girişlerde `Ahmet`, `ahmet`, `AHMET` aynı kabul edilir.
   - **Oturumu Açık Tut**: 30 günlük kalıcı oturum çerezi desteği.
   - **Tek Tıkla Demo Girişi**: Sistemi hemen test etmek için hazır arkadaşlar (Ahmet, Zeynep, Burak, Ayşe).

2. **Ders Programı Yükleme & Ayrıştırma (Görsel, OBS, SUIS, AM/PM)**:
   - **Görsel / Ekran Görüntüsü Yükleme**:
     - Sabancı Üniversitesi (SUIS / Banner), İTÜ, YTÜ, Boğaziçi veya standart OBS haftalık çizelge ekran görüntüleri.
     - **Google Gemini Vision**: API anahtarı girildiğinde karmaşık çizelgeleri %100 doğrulukla JSON'a dönüştürür.
     - **Sütunlu OCR Motoru**: Türkçe ve İngilizce dil desteği ile ders saatlerini algılar.
   - **Çoklu Format Metin Ayrıştırıcı**:
     - 12 saatlik AM/PM saatleri (`9:40 am - 10:30 am`, `12:40 pm - 1:30 pm`, `4:40 pm - 6:30 pm`).
     - 24 saatlik formatlar (`09:40 - 10:30`, `16:40 - 18:30`).
     - Çok satırlı ders blokları (Ders Kodu, CRN/Şube, Saat, Derslik).
     - Hem İngilizce (`Monday`, `Tuesday`...) hem Türkçe (`Pazartesi`, `Salı`...) gün başlıkları.
   - **Tek Tıkla Sabancı (SUIS) Örnek Programı**:
     - Yüklediğiniz çizelgedeki 16 dersin tamamı (MATH 203R, CS 204, DSA 440, HUM 201, vb.) tek tıkla hesabınıza yüklenebilir.
   - **İnteraktif Haftalık Düzenleyici**:
     - Takvimde derslere tıklayıp saat, isim, derslik düzenleme ve tek tıkla yeni ders ekleme.

3. **Akıllı Müsaitlik & "Kim Boş?" Motoru (15 Dakika Kuralı)**:
   - Kullanıcı belirli bir gün ve saat girdiğinde (veya "Şu An Kim Boş?" butonuna bastığında):
     - 🟢 **En Üstte: BOŞ OLANLAR**
       - Müsaitlik süresi (örn: `14:00'e kadar boş - 1 saat 15 dk`).
       - Sıradaki dersin adı, saati ve amfisi.
     - 🔴 **Listenin Altında: DOLU OLANLAR**
       - **Saat kaça kadar meşgul oldukları** (örn: `15:50'ye kadar aralıksız dolu`).
       - Şu an hangi derste oldukları ve derslik bilgisi.
   - **15 Dakika Mola Kuralı Uygulaması**:
     - *Kural*: "Boş duruma çıkabilmesi için aranın 15 dakikadan fazla olması gerekiyor."
     - İki ders arasındaki mola 15 dakika veya daha azsa (örneğin 10 dakikalık üniversite blok ders araları), sistem bunu boş vakit olarak saymaz; ardışık dersler zincirleme tek bir meşgul blok olarak hesaplanır ve son dersin bitiş saatine kadar dolu gösterilir.
     - Sıradaki derse 15 dakika veya daha az kalmışsa kullanıcı "Derse Az Kaldı / Hazırlık" durumuyla dolu kabul edilir.

4. **Ortak Takvim ve Arkadaş Profilleri**:
   - Haftalık tüm grubu saat saat karşılaştıran matris tablosu.
   - Herhangi bir arkadaşın haftalık tam ders çizelgesini tek tıkla modalda görüntüleme.

---

## 🚀 Kurulum ve Çalıştırma

Proje klasöründe terminalden veya `run.bat` dosyasına çift tıklayarak çalıştırabilirsiniz:

```powershell
python app.py
```

Ardından tarayıcınızdan aşağıdaki adrese gidin:
👉 **http://localhost:5000**
