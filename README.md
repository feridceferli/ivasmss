<div align="center">

# 🇦🇿 AZE SMS PANEL

### Telegram Bot · Mini App · Admin Panel

**Telegram idarəetməsi · Nömrə arxivi · TXT endirmə · GitHub ehtiyat nüsxəsi**

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

## Mündəricat

- [İmkanlar](#imkanlar)
- [Xidmətlər və mövcudluq bildirişləri](#xidmətlər-və-mövcudluq-bildirişləri)
- [TXT arxivi və bot komandaları](#txt-arxivi-və-bot-komandaları)
- [GitHub arxivini qurmaq](#github-arxivini-qurmaq)
- [Konfiqurasiya](#konfiqurasiya)
- [Lokal quraşdırma](#lokal-quraşdırma)
- [Render-də yerləşdirmə](#render-də-yerləşdirmə)
- [Yoxlama](#yoxlama)
- [Problemlərin həlli](#problemlərin-həlli)

## İmkanlar

| Bölmə | İmkan |
|---|---|
| 🤖 Telegram botu | Menyu və komandalar vasitəsilə idarəetmə; API-də aktiv olan xidmətlərin siyahısı |
| 🌐 Dil seçimi | Azərbaycan, ingilis və türk dili üçün menyu dəstəyi |
| 📱 Mini App | Mobil uyğun şəxsi panel |
| 📥 TXT endirmə | İstifadəçi üçün öz nömrələri; admin üçün bütün arxiv |
| 🗃️ Nömrə arxivi | SQLite bazası, təkrarsız nömrələr və yerli TXT nüsxəsi |
| ☁️ GitHub arxivi | Ayrı gizli depoya avtomatik yükləmə və xəta zamanı təkrar cəhd |
| 👤 Profil | İstifadəçi məlumatları və statistika |
| 💰 Balans | AZN balansının göstərilməsi və admin tərəfindən dəyişdirilməsi |
| 📊 Sifarişlər | Aktiv sifarişlər və tarixçə |
| 🏆 Liderlər cədvəli | Günlük OTP sayı əsasında ilk 10 istifadəçi |
| 🛡️ Admin paneli | İstifadəçilər, balanslar və giriş məhdudiyyətləri |
| 📢 Toplu bildiriş | Qeydiyyatda olan istifadəçilərə məlumat mesajı |
| 👥 Kanallar | Məcburi kanal və qrup üzvlüyünün yoxlanması |
| 🔐 Mini App sessiyası | Telegram `initData` məlumatının serverdə yoxlanması |
| ❤️ Health endpoint | `GET /health` ilə backend vəziyyətinin yoxlanması |
| 📶 Xidmət və range məlumatı | Xidmət üzrə ölkə/range-ləri ayrıca nəzərdən keçirmə; range məlumat bölməsi yalnız baxış üçündür və nömrə ayırmır |

## Mini App-in yenilənmiş imkanları

Mini App mobil ekranlara uyğun yenilənib. Bot menyusundan açıldıqda Telegram sessiyası ilə istifadəçi məlumatları serverdə yoxlanır.

- **Ana səhifə:** balans, aktiv sifariş sayı, bugünkü və ümumi statistika, sürətli bölmə keçidləri.
- **Sifarişlər:** hesabın aktiv sifarişlərinə baxış; ayrıca Sandbox bölməsində sınaq sifarişi yaratmaq, ləğv etmək və nümunə SMS-ə baxmaq.
- **Profil:** Telegram hesabı, balans, son 24 saat və 7 gün üzrə statistika, dəvət sayı və mükafat məlumatı.
- **Admin:** yalnız icazəli adminlər üçün istifadəçi siyahısı, banı idarə etmək və balansı dəyişmək.
- **Yeniləmə və dəstək:** panel məlumatları əl ilə yenilənir, açıq olduqda təxminən hər 30 saniyədə avtomatik yenilənir; dəstək linki paneldən açılır.

> [!NOTE]
> Mini App-dəki “Test sifarişi” və “Test SMS” Sandbox nümunələridir; onlar real nömrə ayırmır və real OTP/SMS məzmunu təqdim etmir. Sandbox sifarişləri yaddaşda saxlanılır və server restartı/deploy zamanı sıfırlana bilər. Sifariş və admin dəyişiklikləri üçün API CORS `GET, POST, OPTIONS` metodlarına icazə verir.

## Xidmətlər və mövcudluq bildirişləri

- Xidmət seçimi API-dən gələn cari xidmət siyahısını göstərir; API-də sonradan görünən xidmətlər (məsələn, Bolt) kod dəyişikliyi olmadan siyahıya düşür.
- Xidmətə daxil olduqda ölkələr və uyğun diapazonlar göstərilir. **“RANGE-LƏRƏ BAX (MƏLUMAT)”** bölməsi diapazonları ölkə üzrə nəzərdən keçirmək üçündür; oradan nömrə sifarişi verilmir.
- Bot API-də yeni xidmət və ya yeni xidmət/ölkə mövcudluğu aşkar etdikdə istifadəçilərə, `NOTIFY_GROUP_ID` qurulubsa həmin qrupa da bildiriş göndərir. Yoxlama təxminən hər 30 saniyədə aparılır. Bot restartından sonrakı ilk yoxlama mövcud vəziyyəti yadda saxlayır və həmin anda olan xidmətləri yeni kimi elan etmir.

### API-dən hansı məlumatlar gəlir?

Aşağıdakı cədvəl hazırkı kodun istifadə etdiyi sorğuları təsvir edir:

| Sorğu | Kodda istifadə olunan məlumat | Arxivə təsiri |
|---|---|---|
| `GET /liveaccess` | Xidmətlər və onlara aid diapazonlar | Yeni xidmət/ölkə mövcudluğu aşkarlanır; tam nömrə siyahısı alınmır |
| `POST /getnum` | `rid` üzrə cavabdakı `full_number` | Alınmış nömrə arxivə yazılır |
| `GET /success-otp` | Botun SMS/OTP axınında işlənən məlumat | SMS/OTP mətni TXT arxivinə daxil edilmir |

**Yeni xidmət aşkarlananda onun ölkə kodu altındakı bütün nömrələri avtomatik sifariş etmək hazırda tətbiq edilməyib.** Mövcud inteqrasiyada tam nömrə siyahısını qaytaran toplu sorğu müəyyən edilməyib. Diapazon sayı nömrə sayı deyil. Arxiv yalnız botun aldığı nömrələri və mövcud arxivdən bərpa olunan qeydləri əhatə edir.

## Toplu mesaj necə göndərilir?

1. Admin hesabı ilə botu açın. Birbaşa başlamaq üçün şəxsi çatda `/broadcast` yazın.
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
| `number_archive.py` | SQLite nömrə arxivi, TXT çıxışı və gizli GitHub depo sinxronizasiyası |
| `test_number_archive.py` | Arxiv, istifadəçi icazələri və GitHub toqquşma testləri |
| `data_storage.py` | JSON məlumatları üçün saxlama yolları və atomik yazma köməkçisi |
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

## TXT arxivi və bot komandaları

Komandaları botun **şəxsi çatında** istifadə edin:

| Komanda / düymə | Kim istifadə edir? | Nəticə |
|---|---|---|
| `/numbers_txt` · **📥 NÖMRƏLƏRİM — TXT** | İstifadəçi | Yalnız özünə ayrılmış nömrələrin tarixçəsi |
| `/all_numbers_txt` · **📥 BÜTÜN NÖMRƏLƏR — TXT** | Admin | Botun saxladığı bütün nömrələr |
| `/numbers_status` | Admin | GitHub arxivinin son sinxronizasiya vəziyyəti |

Ban edilmiş istifadəçilər fayl endirə bilmir. Endirmə zamanı tələb olunan kanal/qrup üzvlüyü də yoxlanır. Qrup çatına TXT faylı göndərilmir.

### Faylın formatı

- UTF-8 mətn, hər sətirdə bir `+nömrə`.
- Təkrar nömrələr bir dəfə saxlanılır; nömrələr sıralanır.
- TXT-də yalnız nömrələr olur; SMS, OTP, token, istifadəçi ID-si və profil məlumatı daxil edilmir.
- Bot faylları `my_numbers_1.txt` və `all_numbers_1.txt` adları ilə göndərir. Böyük siyahılar təxminən 2 MB-lıq hissələrə bölünür.
- Arxiv tarixçədir: nömrənin faylda olması onun hazırda aktiv olduğunu göstərmir.

### Saxlama və bərpa

| Fayl | Təyinat |
|---|---|
| `number_archive.sqlite3` | Bütün nömrələr və istifadəçi üzrə ayrılma qeydləri |
| `numbers.txt` | Yerli tam siyahı; hər sinxronizasiya dövründə yenilənir |
| `datarange.json` | Bot başlayanda arxivə idxal edilən mövcud qeydlər |

GitHub konfiqurasiyası olmasa da yerli arxiv və botdan TXT endirmə işləyir. Standart dövr 60 saniyədir. Mövcud GitHub siyahısı yerli arxivlə birləşdirilir; məzmun dəyişməyibsə yeni commit yaradılmır. Yazı toqquşmasında uzaq fayl yenidən oxunur, müvəqqəti xətalarda növbəti dövrdə cəhd edilir.

**Qalıcı saxlama üçün `DB_FOLDER` həqiqi qalıcı diskə yönəlməlidir.** GitHub TXT nüsxəsindən ümumi nömrə siyahısı bərpa olunur, amma istifadəçi üzrə tarixçə bərpa olunmur. Qalıcı disk yoxdursa hələ GitHub-a göndərilməmiş nömrələr restart zamanı itə bilər. Əvvəl silinmiş və heç bir nüsxəsi qalmamış məlumat bərpa edilmir.

Botu bir instansiya ilə işlədin. Bu tətbiq GitHub TXT arxivini 40 MB ilə məhdudlaşdırır; həddə çatdıqda saxlama mexanizmini genişləndirmək lazımdır.

## GitHub arxivini qurmaq

### 1. Gizli depo yaradın

[GitHub → New repository](https://github.com/new) səhifəsini açın:

| Sahə | Nümunə |
|---|---|
| Owner | `feridceferli` |
| Repository name | `numbers-archive` |
| Visibility | **Private** |
| Add README | Aktiv |

**Create repository** seçin. Aşağıdakı nümunələr bu adda depo yaratdığınızı fərz edir. Başqa ad seçsəniz konfiqurasiyadakı depo adını dəyişin. Kod arxivi açıq depoya yükləməyə icazə vermir.

### 2. Yazma icazəli token yaradın

[GitHub → Fine-grained token yarat](https://github.com/settings/personal-access-tokens/new) səhifəsini açın:

| Sahə | Dəyər |
|---|---|
| Token name | `Numbers Archive Bot` |
| Resource owner | Arxiv deposunun sahibi |
| Expiration | Özünüzə uyğun müddət; məsələn, 90 gün |
| Repository access | **Only select repositories** |
| Selected repositories | `numbers-archive` |
| Repository permissions → Contents | **Read and write** |

**Generate token** seçin. Tokeni kopyalayıb yalnız serverin mühit dəyişəninə yerləşdirin. Tokenin müddəti bitəndə Render-də dəyəri yeniləyib deploy edin.

### 3. Render-də dəyişənləri əlavə edin

[Render Dashboard](https://dashboard.render.com/) → botun xidməti → **Environment** → **Add Environment Variable**:

| Dəyişən | Dəyər | Tələb |
|---|---|---|
| `NUMBER_ARCHIVE_GITHUB_REPO` | `feridceferli/numbers-archive` | GitHub sinxronizasiyası üçün |
| `NUMBER_ARCHIVE_GITHUB_TOKEN` | Yaratdığınız token | GitHub sinxronizasiyası üçün |
| `NUMBER_ARCHIVE_GITHUB_BRANCH` | Boş buraxıla bilər | Boşdursa deponun standart branch-i |
| `NUMBER_ARCHIVE_GITHUB_PATH` | `numbers.txt` | İstəyə bağlı; standart dəyər |
| `NUMBER_ARCHIVE_SYNC_SECONDS` | `60` | İstəyə bağlı; minimum 30 saniyə |
| `DB_FOLDER` | Məsələn, `/var/data` | Bu yola qalıcı disk qoşulmalıdır |

Repo dəyərində URL yox, yalnız `istifadəçi/depo` yazılır. Tokeni dırnaqsız və əlavə boşluqsuz daxil edin. Mövcud bot və API dəyişənlərini saxlayın.

**Save, rebuild, and deploy** seçin. Deploy-un uğurla tamamlandığını və TXT dəstəyini ehtiva edən kod versiyasının yerləşdirildiyini yoxlayın.

### 4. Nəticəni yoxlayın

Admin hesabı ilə botun şəxsi çatında:

```text
/numbers_status
/all_numbers_txt
```

| Status mətni | Mənası |
|---|---|
| `GitHub sinxronizasiyası hələ başlamayıb.` | Arxiv dövrü hələ nəticə verməyib |
| `Yerli TXT hazırdır; GitHub repo/token konfiqurasiyası yoxdur.` | GitHub dəyişənlərindən biri və ya hər ikisi boşdur |
| `GitHub arxivi yeniləndi.` | Son dövrdə fayl GitHub-a yazılıb |
| `GitHub arxivi yenidir.` | Uzaq fayl yoxlanıb, əlavə yazmağa ehtiyac yoxdur |
| `GitHub sinxronizasiya xətası (...); yenidən sınanacaq.` | Sinxronizasiya alınmayıb; səbəbi aşağıdakı problem cədvəli ilə yoxlayın |

Ən azı bir nömrə saxlanandan və sinxronizasiya tamamlanandan sonra gizli depoda `numbers.txt` görünür. Boş arxiv üçün GitHub-da yeni boş fayl yaradılmır. Status son dövrün nəticəsidir; sonradan alınmış nömrə növbəti dövrdə yüklənə bilər.

Rəsmi təlimatlar: [GitHub tokenləri](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) · [Render mühit dəyişənləri](https://render.com/docs/configure-environment-variables).

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
| `DB_FOLDER` | Xeyr | JSON və SQLite arxivi üçün qovluq; qalıcı disk yolu, məsələn `/var/data` |
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
- Qalıcı disk qoşun və mövcud `DB_FOLDER` dəstəyi ilə JSON və SQLite fayllarını həmin diskə yazdırın.
- Təkcə planı yüksəltmək və ya disk qoşmaq faylları avtomatik qorumur: kod həqiqətən qalıcı saxlama yerinə yazmalıdır. `DB_FOLDER` mühit dəyişənini diskin mount yoluna (məsələn `/var/data`) təyin edin. JSON faylları bu qovluqda saxlanılır. İlk keçiddə hələ mövcud olan yerli JSON faylları yeni qovluğa köçürülür; əvvəl itmiş istifadəçilər avtomatik bərpa edilmir.

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
python -m unittest test_safe_broadcast test_premium_ui test_number_archive -v
```

GitHub Actions-da toplu bildiriş və Premium UI üçün ayrıca yoxlamalar mövcuddur. Arxiv testləri istifadəçi üzrə giriş məhdudiyyətlərini, təkrarların silinməsini, restartdan sonra saxlanmanı və GitHub yazı toqquşmalarını yoxlayır. Testlər real API-dən nömrə almır, GitHub-a arxiv yükləmir və real istifadəçilərə bildiriş göndərmir.

## Problemlərin həlli

| Problem | Yoxlanılacaq məqam |
|---|---|
| TXT komandası cavab vermir | Son kodun deploy olunması, şəxsi çat, admin icazəsi və ban vəziyyəti |
| TXT boşdur və ya saxlanmış nömrə yoxdur | Botun həqiqətən nömrə alması; istifadəçi üçün özünə ayrılma qeydi; arxiv diskinin qorunması |
| Yeni xidmət göründü, amma bütün nömrələr TXT-də yoxdur | Yeni xidmət bildirişi toplu nömrə sifarişini başlatmır; yalnız alınmış nömrələr arxivləşdirilir |
| GitHub repo/token konfiqurasiyası yoxdur | Hər iki `NUMBER_ARCHIVE_GITHUB_...` əsas dəyişəninin dolu olması və deploy |
| GitHub xətası `401` | Tokenin düzgünlüyü, müddəti və ləğv edilib-edilməməsi |
| GitHub xətası `403` və ya `404` | Repo adı, tokenin seçilmiş depoya girişi və `Contents: Read and write` icazəsi; 403 limitlə də bağlı ola bilər |
| GitHub xətası `ValueError` | Deponun Private olması, TXT yolunun düzgünlüyü, uzaq faylda yalnız nömrələrin olması və 40 MB həddi |
| GitHub xətası `RuntimeError` | Təkrar yazı toqquşması; eyni arxivə yazan başqa prosesləri yoxlayın |
| GitHub-da nömrələr var, istifadəçinin TXT-si boşdur | Ümumi TXT istifadəçi ilə nömrə əlaqəsini saxlamır; SQLite və ya mövcud `datarange.json` qeydləri lazımdır |
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
