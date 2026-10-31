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
