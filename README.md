<div align="center">

# 🇦🇿 AZE SMS PANEL

### Telegram Bot · Mini App · Admin Panel

**Python ilə hazırlanmış Telegram idarəetmə sistemi**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Mini%20App-229ED9?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/webapps)
[![Render](https://img.shields.io/badge/Render-Web%20Service-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/)
[![License](https://img.shields.io/badge/License-GPLv3-blue?style=for-the-badge)](LICENSE)

[Admin ilə əlaqə](https://t.me/xudafis) · [Mini App](https://feridceferli.github.io/ivasmss/) · [Backend vəziyyəti](https://ivasmss.onrender.com/health)

</div>

---

## Layihə haqqında

**Aze SMS Panel** Telegram botunu, Python backend-i və Telegram Mini App interfeysini bir layihədə birləşdirir. Backend webhook vasitəsilə Telegram yeniləmələrini qəbul edir və Mini App üçün HTTP API təqdim edir.

Mini App-i botun menyusundan açın. Adi brauzerdə açılan səhifədə Telegram sessiyası olmadığı üçün şəxsi panelə giriş alınmaya bilər.

## İmkanlar

| Bölmə | İmkan |
|---|---|
| 🤖 Telegram botu | Menyu və komandalar vasitəsilə idarəetmə |
| 🌐 Dil seçimi | Azərbaycan, ingilis və türk dili üçün menyu dəstəyi |
| 📱 Mini App | Mobil uyğun şəxsi panel |
| 👤 Profil | İstifadəçi məlumatları və statistika |
| 💰 Balans | AZN balansının göstərilməsi və admin tərəfindən dəyişdirilməsi |
| 📊 Sifarişlər | Aktiv sifarişlər və tarixçə |
| 🏆 Liderlər cədvəli | İstifadəçi statistikası |
| 🛡️ Admin paneli | İstifadəçilər, balanslar və giriş məhdudiyyətləri |
| 📢 Toplu bildiriş | Qeydiyyatda olan istifadəçilərə məlumat mesajı |
| 👥 Kanallar | Məcburi kanal və qrup üzvlüyünün yoxlanması |
| 🔐 Mini App sessiyası | Telegram `initData` məlumatının serverdə yoxlanması |
| ❤️ Health endpoint | `GET /health` ilə backend vəziyyətinin yoxlanması |

## Toplu mesaj necə göndərilir?

1. Admin hesabı ilə botu açın.
2. **Admin paneli → 📢 BÜTÜN İSTİFADƏÇİLƏRƏ MESAJ GÖNDƏR** düyməsini seçin.
3. Göndəriləcək məlumat mətnini yazın. Ləğv etmək üçün ləğv düyməsini seçin.
4. Göndərişin sonunda çatdırılan, çatdırılmayan, botu bloklayan və təkrar cəhd limiti bitən istifadəçilərin sayı göstərilir.

Göndəriş arxa planda işləyir və uzun toplu göndərişi webhook sorğusunun içində gözlətmir. Eyni anda yalnız bir toplu göndəriş başladılır. Müvəqqəti şəbəkə xətalarında təkrar cəhd edilir və Telegramın `RetryAfter` gözləmə müddətinə əməl olunur.

- Mesaj yalnız botla əvvəllər əlaqə qurmuş və `users.json` faylında qeydiyyatda olan istifadəçilərə göndərilə bilər.
- Botu bloklayan istifadəçilərə mesaj çatdırılmır.
- Bildiriş ən çox **3400 simvol** olmalıdır; boş mətn qəbul edilmir.
- Toplu bildiriş adi məlumat üçündür. OTP/SMS təsdiq kodları və parollar göndərilməməlidir; göndəricidə bu məzmun üçün yoxlamalar mövcuddur.
- Arxa plan tapşırığı yaddaşda saxlanılır. Restart və ya deploy zamanı yarımçıq göndərişin avtomatik davam etdirilməsi hazırda tətbiq edilməyib.

## Layihə faylları

| Fayl | Təyinat |
|---|---|
| `main.py` | Bot, webhook serveri və Mini App API |
| `safe_broadcast.py` | Toplu məlumat bildirişi, Telegram limitləri və təkrar cəhdlər |
| `bot_languages.py` | Dil seçimi və menyu mətnləri |
| `bot_localization.py` | Mətnlərin lokallaşdırılması və düymə girişlərinin uyğunlaşdırılması |
| `bot_text_az.json` | Azərbaycan dilində mətnlər |
| `premium_ui.py` | Premium emoji interfeysi və uyğunluq funksiyaları |
| `test_safe_broadcast.py` | Toplu bildiriş testləri |
| `test_premium_ui.py` | Premium interfeys testləri |
| `requirements.txt` | Python asılılıqları |
| `.env.example` | Məxfi dəyərlərsiz konfiqurasiya nümunəsi |
| `docs/index.html` | Mini App səhifəsi |
| `docs/app.js` | Mini App məntiqi və backend ünvanı |
| `docs/style.css` | Mini App görünüşü |

## Konfiqurasiya

Dəyişənləri Render **Environment** bölməsində və ya lokal terminalın mühitində təyin edin. Real token və API açarlarını GitHub-a yükləməyin.

| Dəyişən | Məcburidir? | Təyinat |
|---|---|---|
| `BOT_TOKEN` | Bəli | Telegram bot tokeni |
| `AZE_SMS_API_KEY` | Bəli* | Backend-in istifadə etdiyi API açarı |
| `VOLTX_API_KEY` | Xeyr | `AZE_SMS_API_KEY` olmadıqda köhnə konfiqurasiya üçün alternativ |
| `WEBAPP_URL` | Xeyr | Mini App HTTPS ünvanı; standart ünvan `https://feridceferli.github.io/ivasmss/` |
| `WEBHOOK_URL` | Render-də xeyr | Tam webhook ünvanı, məsələn `https://example.com/webhook` |
| `RENDER_EXTERNAL_URL` | Render avtomatik verir | `WEBHOOK_URL` yoxdursa bu ünvana `/webhook` əlavə edilir |
| `PORT` | Xeyr | HTTP portu; standart `8080`, Render öz portunu verir |
| `NOTIFY_GROUP_ID` | Xeyr | Qrup bildirişləri üçün qrup ID-si |
| `NOTIFY_BOT_TOKEN` | Xeyr | Qrup bildiriş botu; boşdursa əsas `BOT_TOKEN` istifadə olunur |
| `IVASSMS_WEB_URL` | Xeyr | Əlaqəli IVAS web xidmətinin ünvanı |

*Başlama üçün `AZE_SMS_API_KEY` və ya `VOLTX_API_KEY` dəyərlərindən biri olmalıdır.

Admin icazələri hazırda `main.py` daxilindəki `ADMINS` siyahısı ilə idarə olunur. `ADMIN_ID` adlı mühit dəyişəni hazırkı kodda bu siyahını dəyişmir.

> [!NOTE]
> Hazırkı kod `.env` faylını avtomatik oxumur. Təkcə `.env.example` faylını kopyalamaq kifayət deyil; dəyərlər prosesin mühitinə ötürülməlidir.

## Lokal quraşdırma

### 1. Layihəni əldə edin

```bash
git clone https://github.com/feridceferli/ivasmss.git
cd ivasmss
python -m venv .venv
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Asılılıqları quraşdırın

```bash
python -m pip install -r requirements.txt
```

### 3. Mühit dəyişənlərini təyin edib başladın

**Linux / macOS**

```bash
export BOT_TOKEN="TELEGRAM_BOT_TOKENINIZ"
export AZE_SMS_API_KEY="API_ACARINIZ"
export WEBHOOK_URL="https://SIZIN_HTTPS_UNVANINIZ/webhook"
python main.py
```

**Windows PowerShell**

```powershell
$env:BOT_TOKEN="TELEGRAM_BOT_TOKENINIZ"
$env:AZE_SMS_API_KEY="API_ACARINIZ"
$env:WEBHOOK_URL="https://SIZIN_HTTPS_UNVANINIZ/webhook"
python main.py
```

Nümunə dəyərləri öz məlumatlarınızla əvəz edin. Hazırkı giriş nöqtəsi **webhook** ilə işləyir; lokal kompüterdə Telegram yeniləmələrini almaq üçün ictimai HTTPS ünvanı serverin `/webhook` endpoint-inə yönəlməlidir. Sadəcə `localhost` ünvanı Telegram üçün əlçatan deyil.

## Render-də yerləşdirmə

GitHub repository-yə bağlı **Python Web Service** istifadə edin. Botun webhook-u və Mini App API-si eyni HTTP serverində işlədiyi üçün hazırkı giriş nöqtəsi Background Worker üçün nəzərdə tutulmayıb.

| Parametr | Dəyər |
|---|---|
| Repository | `https://github.com/feridceferli/ivasmss` |
| Branch | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python main.py` |
| Health Check Path | `/health` |

`BOT_TOKEN` və API açarını **Environment** bölməsinə əlavə edin. Render-də `RENDER_EXTERNAL_URL` verildiyi üçün ayrıca `WEBHOOK_URL` yazmaq məcburi deyil. Avtomatik deploy aktivdirsə, `main`-ə yeni commit gələndə yerləşdirmə başlayır.

Server başlayan zaman gözləyən Telegram yeniləmələri qəsdən silinmir (`drop_pending_updates=False`). Bu parametr yerli istifadəçi fayllarını və yarımçıq toplu göndərişi bərpa etmir.

### Davamlı işləmə və məlumatların saxlanması

Render-in pulsuz web xidməti **15 dəqiqə giriş trafiki olmayanda dayanır**. Növbəti sorğu xidməti yenidən başladır; ilk cavab gecikə bilər. Pulsuz plan 24/7 fasiləsiz işləmə üçün uyğun deyil.

İstifadəçilər, balanslar və digər məlumatlar hazırda yerli JSON fayllarında saxlanılır. Qalıcı disk olmayan Render xidmətində bu fayllardakı dəyişikliklər **deploy, restart və ya dayanma zamanı itir**. Beləliklə köhnə istifadəçilər toplu mesaj siyahısından da çıxa bilər.

Davamlı istifadə üçün:

- Boşdayanma səbəbindən yuxuya getməyən ödənişli compute planı istifadə edin.
- JSON fayllarını qalıcı diskin mount yoluna yazmaq üçün kodu uyğunlaşdırın və ya məlumat bazasına keçin.
- Təkcə planı yüksəltmək və ya disk qoşmaq faylları avtomatik qorumur: kod həqiqətən qalıcı saxlama yerinə yazmalıdır. Hazırkı kodda `DB_FOLDER` dəstəyi yoxdur.

Rəsmi məlumat: [Render Free](https://render.com/docs/free) · [Persistent Disks](https://render.com/docs/disks).

## GitHub Pages — Mini App

Repository-də **Settings → Pages** bölməsini açın:

| Parametr | Dəyər |
|---|---|
| Source | Deploy from a branch |
| Branch | `main` |
| Folder | `/docs` |

Yaranan HTTPS ünvanını `WEBAPP_URL` kimi istifadə edin. Backend başqa ünvana köçürülərsə, `docs/app.js` daxilindəki `API_BASE` dəyərini də yeniləyin; yalnız `WEBAPP_URL` dəyişmək backend ünvanını dəyişmir.

## Yoxlama

**Backend vəziyyəti**

```bash
curl https://ivasmss.onrender.com/health
```

Gözlənilən cavab:

```json
{"ok": true, "service": "aze-sms-panel"}
```

Bu endpoint HTTP serverinin cavab verdiyini göstərir; bütün xarici API-lərin işlədiyini və mesajın hər istifadəçiyə çatdığını ayrıca təsdiqləmir.

**Avtomatik testlər**

```bash
python -m unittest test_safe_broadcast test_premium_ui -v
```

GitHub Actions-da toplu bildiriş və Premium UI üçün ayrıca yoxlamalar mövcuddur. Testlər real istifadəçilərə bildiriş göndərmir.

## Problemlərin həlli

| Problem | Yoxlanılacaq məqam |
|---|---|
| Bot gec cavab verir | Render Free planında xidmətin yuxuya getməsi və deploy vəziyyəti |
| İstifadəçilər və balanslar yox olub | Yerli JSON fayllarının qalıcı saxlama yerinə yazılıb-yazılmaması |
| Toplu mesaj hamıya çatmır | `users.json` siyahısı, botun bloklanması və göndəriş nəticə sayğacları |
| “Əvvəlki bildiriş hələ göndərilir” | Cari toplu göndərişin tamamlanmasını gözləyin |
| Mini App 404 qaytarır | Pages üçün `main /docs` və `WEBAPP_URL` |
| Mini App 401 qaytarır | Mini App-i Telegram botundan açın; bot tokeni və sessiya uyğunluğunu yoxlayın |
| Mini App backend-ə qoşulmur | `docs/app.js` daxilindəki `API_BASE` və backend vəziyyəti |
| Server başlamır | `BOT_TOKEN`, API açarı və `WEBHOOK_URL` / `RENDER_EXTERNAL_URL` |
| Admin menyusu görünmür | Telegram istifadəçi ID-sinin `ADMINS` siyahısında olması |

## Məxfi məlumatlar

Token və API açarlarını yalnız serverin mühit dəyişənlərində saxlayın. Sessiya məlumatlarını, istifadəçi fayllarını və real məxfi dəyərləri repository-yə əlavə etməyin. Mini App sorğularında istifadəçi kimliyi serverdə yoxlanmalıdır. Layihədən yalnız icazəli məqsədlər üçün istifadə edin.

## Lisenziya

Layihə **GNU General Public License v3.0 or later** altında yayımlanır. Ətraflı məlumat üçün [LICENSE](LICENSE) faylına baxın.

---

<div align="center">

**🇦🇿 AZE SMS PANEL**

[Layihə ilə bağlı əlaqə — @xudafis](https://t.me/xudafis)

</div>
