# IVASPER — sadə nömrə qəbulu və siyahı

IVASPER istifadəçi üçün deyil, **yalnız admin üçün** ayrıca nömrə
inventarıdır. Mövcud IVASMS kataloqu, aktiv nömrələri, balansı,
SMS/OTP mətnləri və nömrə arxivinə heç nə yazılmır.

## İstifadə

1. [Sayta](https://ivasmss.onrender.com) Telegram hesabı ilə daxil olun
   (və ya botdakı Mini App-ı açın).
2. **Admin → IVASPER nömrələr → Nömrə qəbul et** hissəsinə keçin.
3. Ölkə və xidməti yazın. Nömrələri alt-alta əlavə edin (1–100 ədəd).
4. **Nömrələri qəbul et** düyməsini sıxın.
5. Səhifəni yenilədikdə nömrələr ayrıca IVASPER siyahısında görünür;
   əvvəlki qeydlər silinmir. Telegram şəxsi çatında `/ivasper`
   siyahıya baxış üçündür.

Nömrələrin siyahıya əlavə edilməsi onların SMS/OTP qəbul etdiyini
təsdiqləmir. Yalnız idarə etdiyiniz və istifadəsinə icazəniz olan
nömrələri əlavə edin.

## Render konfiqurasiyası

Hazırda üç resurs var:
- IVASMS əsas xidmət: `srv-db1pbl9srm7s73co1im0`
- Ayrı IVASPER API: `srv-dbittqoae00c73cm5rr0`
- Ayrı PostgreSQL: `dpg-dbitrics728c7389r7m0-a`

IVASPER API-sində aşağıdakı ayarlar lazımdır:
- `IVASPER_READER_TOKEN` — yalnız oxuma açarı
- `IVASPER_WRITER_TOKEN` — yalnız nömrə qəbulu açarı
- `DATABASE_URL` — **IVASPER PostgreSQL** resursunun
  Render Dashboard → **Connect → Internal Database URL** dəyəri

Əsas IVASMS servisində:
- `IVASPER_NUMBERS_URL=https://ivasper-independent-api.onrender.com/numbers`
- `IVASPER_NUMBERS_TOKEN` — IVASPER API-nin READER açarı ilə eyni
- `IVASPER_IMPORT_TOKEN` — IVASPER API-nin WRITER açarı ilə eyni

İki servisin tokenləri ayrı-ayrı, amma doğru cütlərlə eyni olmalıdır.
**Tokenləri və PostgreSQL bağlantı parolunu GitHub-a və çata
yazmayın.** Render-in Environment səhifəsində məxfi dəyişən kimi saxlayın.

Qeyd: Render bağlantı vasitəsi PostgreSQL bağlantısının məxfi URL-sini
oxumağa imkan vermədiyi üçün `DATABASE_URL` bir dəfə Dashboard-da
özünüz tərəfindən doldurulmalıdır. API-də `DATABASE_URL` olmadığı
halda `/import` HTTP 503 qaytarır — nömrələr **yadda saxlanmır**.
Bağlantı qurulduqdan sonra API öz cədvəlini ilk sorğuda yaradacaq;
əlavə SQL əmri tələb olunmur.

Postgres və IVASPER API eyni workspace və Oregon regionundadır;
daxili baza URL-sini işlədin. Pulsuz bazanın son istifadə tarixi
`2026-11-30`-dur; həmin tarixdən əvvəl davamlı bazaya keçid planlayın.

## Ayrıca API (yalnız səlahiyyətli sistem inteqrasiyası)

Bir müstəqil IVASPER nömrə mənbəyi daxil etmək istəyirsinizsə
`POST https://ivasper-independent-api.onrender.com/import`
(Bearer `IVASPER_WRITER_TOKEN`, Content-Type: application/json)
belə JSON qəbul edir:

```json
{
  "numbers": [
    {"number": "+994501234567", "country": "Azərbaycan", "service": "IVASPER"}
  ]
}
```

Bu sadəcə format nümunəsidir; real ehtiyat deyil.
`GET /numbers` yalnız READER tokenlə işləyir. Əsas sayt vasitəsilə
admin idxalında token istifadəçiyə göndərilmir; backend proxy edir.

## Test

```bash
python -m unittest -v test_ivasper_web.py test_ivasper_admin.py test_ivasper_inventory_service.py
node --check docs/app.js && node test_ivasper_web_ui.cjs
```
