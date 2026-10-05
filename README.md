# 🇦🇿 Aze SMS Panel

**Telegram Bot + Telegram Mini App idarəetmə paneli**

Aze SMS Panel Python backend, Telegram bot və mobil uyğun Mini App interfeysini bir layihədə birləşdirir. Layihə Render üzərində backend, GitHub Pages üzərində isə Mini App frontend ilə işləmək üçün hazırlanıb.

> **Qeyd:** Layihədən yalnız qanuni və icazəli məqsədlər üçün istifadə edin. Token, API açarı və digər məxfi məlumatları repoya əlavə etməyin.

<p align="center">
  <a href="https://t.me/xudafis"><img src="https://img.shields.io/badge/Telegram-Admin-229ED9?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Admin"></a>
</p>

## ✨ Əsas imkanlar

- 🤖 Telegram bot interfeysi
- 📱 Mobil cihazlara uyğun Telegram Mini App
- 👤 İstifadəçi profili və şəxsi panel
- 💰 AZN balans göstəricisi
- 📊 Aktiv sifariş və tarixçə görünüşü
- 🏆 Liderlər cədvəli
- 🛡️ Admin idarəetmə paneli
- 👥 İstifadəçilərin idarə edilməsi
- ⚙️ Sistem konfiqurasiyası
- 📢 Məcburi kanal və qrup idarəetməsi
- 🔐 Telegram Mini App initData yoxlaması
- ❤️ Health-check endpoint
- 🌐 GitHub Pages frontend dəstəyi
- 🚀 Render deployment dəstəyi
- 🔒 Environment Variables ilə məxfi məlumatların qorunması

## 👑 Admin və əlaqə

Layihənin admini ilə Telegram üzərindən əlaqə:

**Admin:** [@xudafis](https://t.me/xudafis)

[![Admin ilə əlaqə](https://img.shields.io/badge/Admin%20ilə%20əlaqə-Telegram-229ED9?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/xudafis)

## 🖥️ Mini App

Frontend faylları `docs/` qovluğundadır:

```text
docs/
├── index.html
├── style.css
└── app.js
```

GitHub Pages `main` branch-in `/docs` qovluğundan yayımlandıqda Mini App frontend işləyir.

## 📁 Layihə strukturu

```text
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

## ⚙️ Environment Variables

Məxfi məlumatları mənbə koduna yazmayın. Hosting tərəfində Environment Variables istifadə edin:

```env
BOT_TOKEN=telegram_bot_tokeniniz
AZE_SMS_API_KEY=api_acariniz
WEBAPP_URL=https://ISTIFADECI_ADI.github.io/REPO_ADI/
```

Layihədə köhnə uyğunluq üçün `VOLTX_API_KEY` fallback olaraq dəstəklənə bilər. Render webhook URL-ni avtomatik qura bilmirsə:

```env
WEBHOOK_URL=https://sizin-servisiniz.example/webhook
```

## 🚀 Quraşdırma

```bash
git clone https://github.com/feridceferli/ivasmss.git
cd ivasms
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 🌐 GitHub Pages

1. Repository-də **Settings → Pages** bölməsini açın.
2. **Deploy from a branch** seçin.
3. Branch: **main**.
4. Folder: **/docs**.
5. **Save** düyməsinə basın.
6. Yaranan HTTPS ünvanını `WEBAPP_URL` kimi istifadə edin.

## ☁️ Render

GitHub reposuna bağlı Python Web Service yaradın. Environment Variables əlavə etdikdən sonra start command:

```bash
python main.py
```

Servisin işlədiyini yoxlamaq üçün backend-də `/health` endpoint-i mövcuddur.

## 🛡️ Admin təhlükəsizliyi

Admin funksiyalarını yalnız frontend-də gizlətmək kifayət deyil. Backend hər admin əməliyyatında istifadəçinin səlahiyyətini ayrıca yoxlamalıdır.

- Admin icazəsini backend-də yoxlayın.
- Telegram Mini App-dən gələn initData-nı serverdə doğrulayın.
- Client tərəfindən göndərilən user ID-yə təkbaşına etibar etməyin.
- Token/API açarlarını loglara yazmayın.
- Yalnız HTTPS istifadə edin.

## 🔧 Tez-tez rast gəlinən problemlər

**Mini App 404 göstərir:** GitHub Pages-in `main /docs` konfiqurasiyasını və `docs/index.html` faylını yoxlayın.

**Mini App 401 göstərir:** Mini App-i birbaşa brauzer linkindən deyil, Telegram bot daxilindəki Mini App düyməsindən açın və Render-də düzgün `BOT_TOKEN` istifadə olunduğunu yoxlayın.

**Render başlamır:** `BOT_TOKEN`, `AZE_SMS_API_KEY` və deployment URL dəyişənlərini yoxlayın. Son deploy logundakı ilk exception əsas səbəbi göstərir.

## 🔐 Təhlükəsizlik

- Real token və API açarlarını GitHub-a commit etməyin.
- Sızmış tokenləri dərhal dəyişdirin.
- Məxfi məlumatları frontend-ə yerləşdirməyin.
- Admin endpointlərini server tərəfində qoruyun.
- Asılılıqları mütəmadi yeniləyin.
- İstifadə etdiyiniz API və platformaların qaydalarına əməl edin.

## 📄 Lisenziya

Bu layihə **GNU General Public License v3.0 (GPL-3.0)** altında yayımlanır. İstifadə, dəyişdirmə və paylaşma şərtləri üçün repository-dəki [`LICENSE`](LICENSE) faylına baxın.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

---

<p align="center">
  <b>Aze SMS Panel</b><br>
  Telegram Bot + Mini App<br><br>
  <a href="https://t.me/xudafis">💬 Admin ilə Telegram-da əlaqə</a>
</p>
