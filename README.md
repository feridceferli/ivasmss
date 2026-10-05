<div align="center">

# 🇦🇿 AZE SMS PANEL

### Telegram Bot • Mini App • Admin Dashboard

**Sürətli, müasir və mobil uyğun Telegram idarəetmə sistemi**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Mini%20App-229ED9?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/webapps)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/)
[![License](https://img.shields.io/badge/License-GPLv3-blue?style=for-the-badge)](LICENSE)

<br>

[![Admin](https://img.shields.io/badge/💬_ADMIN_İLƏ_ƏLAQƏ-@xudafis-229ED9?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/xudafis)

</div>

---

## 🚀 Layihə haqqında

**Aze SMS Panel** Python backend, Telegram Bot API və Telegram Mini App frontend hissəsini bir layihədə birləşdirən idarəetmə sistemidir.

> [!IMPORTANT]
> Layihədən yalnız qanuni və icazəli məqsədlər üçün istifadə edin. Bot tokeni, API açarı və digər məxfi məlumatları heç vaxt GitHub-a commit etməyin.

## ✨ Xüsusiyyətlər

| Bölmə | İmkan |
|---|---|
| 🤖 **Telegram Bot** | Telegram daxilində əsas idarəetmə |
| 📱 **Mini App** | Mobil uyğun müasir interfeys |
| 👤 **Profil** | İstifadəçi məlumatları və şəxsi panel |
| 💰 **Balans** | AZN balans məlumatı |
| 📊 **Sifarişlər** | Aktiv sifariş və tarixçə görünüşü |
| 🏆 **Leaderboard** | Liderlər cədvəli |
| 🛡️ **Admin Panel** | Admin üçün idarəetmə funksiyaları |
| 👥 **Users** | İstifadəçilərin idarə edilməsi |
| 📢 **Channels** | Məcburi kanal və qrup idarəetməsi |
| 🔐 **Security** | Telegram Mini App initData yoxlaması |
| ❤️ **Health Check** | Backend vəziyyətinin yoxlanması |
| ☁️ **Deployment** | Render + GitHub Pages dəstəyi |

## 👑 Admin

<div align="center">

### @xudafis

Layihə ilə bağlı əlaqə və dəstək:

[![Telegram Admin](https://img.shields.io/badge/Telegram-Adminə_yaz-229ED9?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/xudafis)

</div>

## 🧩 Sistem arxitekturası

```text
Telegram
   │
   ├── Telegram Bot
   │       │
   │       └── Python Backend ── API
   │
   └── Mini App
           │
           ├── HTML
           ├── CSS
           └── JavaScript
```

Backend **Render**, Mini App frontend isə **GitHub Pages** üzərində işləyə bilər.

## 📁 Layihə strukturu

```text
ivasmss/
│
├── main.py
├── bot_localization.py
├── bot_text_az.json
├── requirements.txt
├── Procfile
├── README.md
├── LICENSE
│
└── docs/
    ├── index.html
    ├── style.css
    └── app.js
```

## ⚙️ Environment Variables

> [!CAUTION]
> Aşağıdakı dəyərlərin real versiyalarını README və ya mənbə koduna yazmayın.

```env
BOT_TOKEN=telegram_bot_tokeniniz
AZE_SMS_API_KEY=api_acariniz
WEBAPP_URL=https://ISTIFADECI_ADI.github.io/REPO_ADI/
```

Lazım olduqda:

```env
WEBHOOK_URL=https://sizin-servisiniz.example/webhook
```

Layihədə köhnə konfiqurasiyalarla uyğunluq üçün `VOLTX_API_KEY` fallback kimi dəstəklənə bilər.

## 🛠️ Lokal quraşdırma

### 1. Repository-ni klonlayın

```bash
git clone https://github.com/feridceferli/ivasmss.git
cd ivasms
```

### 2. Virtual environment yaradın

```bash
python -m venv .venv
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

**Windows**

```powershell
.venv\Scripts\activate
```

### 3. Asılılıqları quraşdırın

```bash
pip install -r requirements.txt
```

### 4. Botu başladın

```bash
python main.py
```

## 🌐 GitHub Pages — Mini App

Mini App frontend faylları `docs/` qovluğundadır.

GitHub-da:

```text
Settings
└── Pages
    ├── Source: Deploy from a branch
    ├── Branch: main
    └── Folder: /docs
```

Yaranan HTTPS ünvanını `WEBAPP_URL` Environment Variable kimi istifadə edin.

## ☁️ Render Deployment

Render-də GitHub repository-yə bağlı **Python Web Service** yaradın.

**Start Command**

```bash
python main.py
```

Environment Variables əlavə edildikdən sonra son commit-i deploy edin.

Backend vəziyyətini yoxlamaq üçün:

```text
/health
```

endpoint-i istifadə edilə bilər.

## 🔐 Təhlükəsizlik

- 🔑 Token və API açarlarını yalnız Environment Variables daxilində saxlayın.
- 🛡️ Admin icazəsini backend tərəfində yoxlayın.
- 📲 Telegram Mini App `initData` məlumatını serverdə doğrulayın.
- 🚫 Client tərəfindən göndərilən user ID-yə təkbaşına etibar etməyin.
- 🔒 Yalnız HTTPS istifadə edin.
- 📝 Məxfi məlumatları loglara yazmayın.
- ♻️ Sızmış token və API açarlarını dərhal dəyişdirin.

## 🩺 Problemlərin həlli

<details>
<summary><b>Mini App 404 göstərir</b></summary>

- GitHub Pages aktiv olmalıdır.
- Source `main /docs` olmalıdır.
- `docs/index.html` mövcud olmalıdır.
- `WEBAPP_URL` tam HTTPS ünvanı olmalıdır.

</details>

<details>
<summary><b>Mini App 401 göstərir</b></summary>

Mini App-i adi brauzer linkindən deyil, Telegram daxilində botun Mini App düyməsindən açın. Render-də istifadə olunan `BOT_TOKEN` ilə Mini App-i açan botun tokeninin uyğun olduğunu yoxlayın.

</details>

<details>
<summary><b>Render başlamır</b></summary>

`BOT_TOKEN`, `AZE_SMS_API_KEY` və deployment dəyişənlərini yoxlayın. Render loglarında görünən ilk exception-u araşdırın.

</details>

## 📄 Lisenziya

Bu layihə **GNU General Public License v3.0 or later** altında yayımlanır.

[![GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Ətraflı məlumat üçün [LICENSE](LICENSE) faylına baxın.

---

<div align="center">

### 🇦🇿 Aze SMS Panel

**Telegram Bot + Modern Mini App**

Made with Python • Telegram • GitHub • Render

<br>

[![Contact](https://img.shields.io/badge/Telegram-@xudafis-229ED9?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/xudafis)

<br><br>

⭐ Layihəni bəyəndinizsə repository-yə star verə bilərsiniz.

</div>
