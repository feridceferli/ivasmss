# Aze Sms Panel xidmeti --- Telegram Mini App

Telegram botu, müasir Telegram Mini App interfeysi, istifadəçi paneli,
admin idarəetməsi və Render + GitHub Pages üzərindən yerləşdirmə dəstəyi
olan layihə.

> **Vacib:** Bu layihə yalnız qanuni və icazəli istifadə üçün nəzərdə
> tutulub. Başqa şəxslərin hesablarına, mesajlarına, autentifikasiya
> məlumatlarına və ya üçüncü tərəf xidmətlərinə icazəsiz giriş üçün
> istifadə etməyin.
https://t.me/xudafis
## ✨ Xüsusiyyətlər

-   🤖 Telegram bot interfeysi
-   📱 Müasir və mobil cihazlara uyğun Mini App
-   👤 İstifadəçi profili və şəxsi panel
-   💰 Balans məlumatlarının göstərilməsi
-   🏆 Liderlər cədvəli
-   🔗 Dəstək keçidləri
-   🛡️ Yalnız adminlər üçün idarəetmə paneli
-   👥 İstifadəçilərin idarə edilməsi
-   ⚙️ Sistem konfiqurasiyası
-   📢 Məcburi kanal və qrupların idarə edilməsi
-   🌐 GitHub Pages üzərindən frontend
-   🚀 Render üzərindən botun yerləşdirilməsi
-   🔐 Token və API açarlarının Environment Variables ilə qorunması

## 🖥️ Mini App

Mini App Telegram-ın daxili brauzeri və mobil cihazlar üçün hazırlanıb.
Frontend faylları `docs/` qovluğunda yerləşir:
https://t.me/xudafis
``` text
docs/
├── index.html
├── style.css
└── app.js
```

GitHub Pages `/docs` qovluğundan yayımlandıqda bu qovluq Mini App-in
frontend hissəsi kimi işləyir.

## 🛡️ Admin Panel

Admin əməliyyatları yalnız frontend səviyyəsində qorunmamalıdır. Python
backend hər admin əməliyyatında Telegram istifadəçisinin admin
səlahiyyətini ayrıca yoxlamalıdır.

Admin panel vasitəsilə aşağıdakı bölmələr idarə oluna bilər:

-   İstifadəçilərin idarə edilməsi
-   Sistem parametrləri
-   Məcburi kanal və qruplar
-   Xidmət parametrləri
-   Sistem vəziyyəti

## 📁 Layihənin strukturu

``` text
ivasmss/
├── main.py
├── bot_localization.py
├── bot_text_az.json
├── requirements.txt
├── Procfile
├── README.md
└── docs/
    ├── index.html
    ├── style.css
    └── app.js
```
https://t.me/xudafis
## ⚙️ Environment Variables

Gizli məlumatları birbaşa mənbə koduna yazmayın.

Hosting xidmətində tələb olunan dəyişənləri əlavə edin:

``` env
BOT_TOKEN=telegram_bot_tokeniniz
VOLTX_API_KEY=api_acariniz
WEBAPP_URL=https://ISTIFADECI_ADI.github.io/REPO_ADI/
```

Deployment konfiqurasiyasından asılı olaraq aşağıdakı dəyişən də
istifadə oluna bilər:

``` env
WEBHOOK_URL=https://sizin-servisiniz.example/webhook
```

### 🔐 Tokenləri GitHub-a yükləməyin

Real bot tokenini, API açarını, parolu, cookie-ni və digər məxfi
məlumatları repoya commit etməyin.

Token və ya API açarı təsadüfən yayımlanarsa, dərhal onu ləğv edib
yenisini yaradın və hosting xidmətində dəyişdirin.

## 🚀 Quraşdırma və Deployment

### 1. GitHub

Layihəni GitHub reposuna yükləyin.

Frontend strukturu belə olmalıdır:

``` text
repository/
├── main.py
└── docs/
    ├── index.html
    ├── style.css
    └── app.js
```
https://t.me/xudafis
Aşağıdakı kimi səhv qovluq strukturu yaratmayın:

``` text
docs/docs/index.html
```

### 2. GitHub Pages

Repository-də:

1.  **Settings → Pages** bölməsinə keçin.
2.  **Deploy from a branch** seçin.
3.  Branch olaraq `main` seçin.
4.  Folder olaraq `/docs` seçin.
5.  **Save** düyməsinə basın.
6.  GitHub saytın yayımlandığını bildirənə qədər gözləyin.

GitHub Pages tərəfindən verilən HTTPS ünvanını `WEBAPP_URL` olaraq
istifadə edin.

### 3. Render

GitHub reposuna bağlı Python Web Service yaradın.

Render-də tələb olunan Environment Variables dəyişənlərini əlavə edin və
son commit-i deploy edin.

Tipik start command:

``` bash
python main.py
```
https://t.me/xudafis
Layihənin istifadə etdiyiniz versiyasında fərqli start command tələb
olunursa, həmin əmrdən istifadə edin.

## 📲 Telegram Mini App qurulması

Telegram botuna HTTPS Mini App URL-i qoşulmalıdır.

Frontend, bot kodu və ya Environment Variables dəyişdirildikdən sonra
Render-də yeni deploy başladın və test zamanı Telegram bot söhbətini
yenidən açın.

## 🧰 Lokal quraşdırma

Virtual environment yaradın:

``` bash
python -m venv .venv
```

Linux/macOS:

``` bash
source .venv/bin/activate
```

Windows:

``` powershell
.venv\Scripts\activate
```

Asılılıqları quraşdırın:

``` bash
pip install -r requirements.txt
```

Tələb olunan Environment Variables dəyişənlərini təyin etdikdən sonra
botu başladın:

``` bash
python main.py
```
https://t.me/xudafis
## 🔧 Problemlərin həlli

### Mini App 404 göstərir

Bunları yoxlayın:

-   GitHub Pages aktivdir.
-   Pages `main` branch və `/docs` qovluğundan yayımlanır.
-   `docs/index.html` mövcuddur.
-   URL `https://` ilə başlayır.
-   `WEBAPP_URL` GitHub Pages-in tam və düzgün ünvanıdır.
-   `docs/docs/` kimi səhv qovluq strukturu yoxdur.

### Mini App açılır, amma düymələr işləmir

Bunları yoxlayın:

-   Render-də işləyən `main.py` ən son versiyadır.
-   Telegram Web App məlumatlarını qəbul edən uyğun backend handler
    mövcuddur.
-   Mini App layihədə nəzərdə tutulan üsulla açılır.
-   Frontend JavaScript xətası yoxdur.
-   Render loglarında exception görünmür.

### Bot Render-də başlamır

Environment Variables dəyişənlərinin mövcudluğunu yoxlayın.

Xüsusilə:

``` text
BOT_TOKEN
VOLTX_API_KEY
WEBAPP_URL
```
https://t.me/xudafis
Son Render deploy loglarını da yoxlayın.

## 🔒 Təhlükəsizlik

-   Token və API açarlarını Environment Variables daxilində saxlayın.
-   Admin icazəsini həmişə backend-də yoxlayın.
-   Frontend JavaScript-dən gələn istifadəçi ID-sinə kor-koranə etibar
    etməyin.
-   Mini App-dən gələn məlumatları backend-də yoxlayın.
-   Yalnız HTTPS istifadə edin.
-   Yayımlanmış tokenləri dərhal dəyişdirin.
-   Məxfi məlumatları loglara yazmayın.
-   Admin funksiyalarını yalnız səlahiyyətli istifadəçilərə açın.
-   Asılılıqları mütəmadi yeniləyin.

## 🤝 Layihəyə töhfə

UI, sabitlik, sənədləşdirmə, əlçatanlıq və təhlükəsizliyi yaxşılaşdıran
dəyişikliklər qəbul edilə bilər.

Dəyişiklik göndərməzdən əvvəl:

1.  Botu mümkün olduqda lokal test edin.
2.  Mini App-in mobil Telegram-da düzgün açıldığını yoxlayın.
3.  Commit daxilində token və API açarı olmadığından əmin olun.
4.  Təhlükəsizlik yoxlamalarını backend tərəfində saxlayın.

## 📄 Lisenziya
https://t.me/xudafis
Repository-də ayrıca `LICENSE` faylı olmadığı halda avtomatik olaraq
açıq mənbə lisenziyası verilmir.

Başqalarının layihəni hansı şərtlərlə istifadə, dəyişdirmə və
paylaşmasına icazə verdiyinizi göstərmək üçün ayrıca `LICENSE` faylı
əlavə edin.

------------------------------------------------------------------------
https://t.me/xudafis
### Aze Sms Panel xidmeti

**Telegram Bot + Müasir Mini App**

Layihəni istifadə edərkən təhlükəsizlik qaydalarına və istifadə
etdiyiniz xidmətlərin şərtlərinə əməl edin.
https://t.me/xudafis
