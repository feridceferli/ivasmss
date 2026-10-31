# IVASPER — yalnız admin üçün nəzarət

Mənbə layihə: https://github.com/shagunallrepo/Ivasmsper

Mövcud IVASMS botuna mənbənin ölkələr üzrə nömrə ehtiyatı statistikasının və sistem statusunun yanaşması ayrıca, yalnız oxunan modul kimi uyğunlaşdırıldı. Xarici bot prosesi, başqa hesabların tokenləri və avtomatik mesaj yönləndirilməsi daxil edilməyib.

## Botda istifadə

Admin özəl çatda `/ivasper` komandasını yaza bilər və ya admin menyusunda **🧰 IVASPER NƏZARƏT** seçə bilər.

Menyuda API monitorunun statusu, saxlanan nömrələrin ölkələr üzrə sayları, servis və range qeydlərinin sayı var. Arxiv sayı və range sayı real vaxtda aktiv nömrə ehtiyatını təsdiqləmir.

## İcazələr və məxfilik

Komanda və bütün düymə sorğuları serverdə `is_admin` yoxlamasından keçir; qrupda və adi istifadəçi hesabında işləmir. Şəxsi nömrələr, SMS/OTP mətnləri, tokenlər və digər istifadəçilərin ID-ləri göstərilmir.

Mənbədə açıq yerləşdirilmiş bot/API tokenləri, başqa admin ID-ləri, xarici qruplar və avtomatik OTP yönləndirilməsi heç bir formada daxil edilməyib. Mövcud provayderin işləməsi yalnız sizin Render-də təyin etdiyiniz mühit dəyişənlərindən asılıdır.

## Test

`python -m unittest -v test_ivasper_admin.py`


## Sayt və Telegram Mini App inteqrasiyası

Hər iki mühitdə **⚙️ Admin → 🧰 IVASPER nömrələr** bölməsi mövcuddur.
Orada servis və ölkə/range siyahıları eyni mövcud IVASMS API-dən götürülür.
Range seçimi köhnə `/api/get-number` iki mərhələli axınına yönləndirilir:
əvvəl 5 nömrə variantı, sonra seçilən 1 nömrənin admin hesabına ayrılması.
Xidmət/range siyahısı real vaxt ehtiyatı deyil.

`GET /api/ivasper` yalnız doğrulanmış Telegram Mini App initData
və ya Telegram ilə əlaqələndirilmiş etibarlı sayt sessiyası olduqda işləyir.
Server bütün çağırışlarda admin və bloklanma statusunu yoxlayır. Yalnız
həmin adminin aktiv nömrələri qaytarılır; digər istifadəçilərə məxsus
nömrələr, OTP mətnləri, API tokenləri və kənar panel məlumatları ötürülmür.
İnterfeys açıq internetdə olsa da, giriş serverdə 403 ilə məhdudlaşdırılır.

Testlər:

```bash
python -m unittest -v test_ivasper_admin.py test_ivasper_web.py
node --check docs/app.js
node test_ivasper_web_ui.cjs
```


## Ölkələr üzrə arxivdə tam nömrələr

**Sayt və Mini App:** Admin → IVASPER nömrələr → Ölkələr üzrə nömrə arxivim.
Ölkəni (məsələn 🇦🇿 Azərbaycan) seçdikdə həmin adminin hesabına
əvvəllər ayrılmış tam nömrələr və range qeydləri göstərilir. Bir səhifədə
25 nömrə var; Növbəti/Əvvəlki ilə bütün şəxsi qeydləri görmək olar.
Kopyala düyməsi mövcuddur. Arxiv nömrəsinin aktiv olmasına zəmanət yoxdur.

**Telegram bot:** Şəxsi çatda /ivasper → 📦 Ölkələr üzrə arxiv → ölkəni
seç. Eyni hesabın nömrələri 12-li səhifələrlə göstərilir.

Ölkənin **ümumi** arxiv sayı bütün istifadəçilərin qeydlərini də əhatə
edir, ancaq tam nömrələr yalnız həmin Telegram admin ID-sinə aid
`datarange.json` qeydlərindən gəlir. Başqa istifadəçilərin nömrələri,
OTP/SMS mətnləri və giriş açarları API-də qaytarılmır. Əgər həmin ölkədə
sizin hesabınıza ayrılmış nömrə yoxdursa, boş siyahı və izahlı mətn
göstərilir. Digər hesabların qeydini avtomatik özünüzə aid etmək olmaz.
