# IVASPER — ayrı inventar (admin üçün)

Bu bölüm mövcud IVASMS nömrə bazasına **qoşulmur** və heç bir
IVASPER nömrəsini IVASMS aktiv nömrələr, qiymətlər, balans, tarixçə,
range və ya GitHub nömrə arxivinə yazmır.

## Mənbə

Orijinal `shagunallrepo/Ivasmsper` layihəsi nömrələri öz SQLite
`numbers` cədvəlində və ayrıca GN_DATA servis/ölkə ehtiyatında saxlayır.
GitHub kodu öz-özlüyündə həmin canlı bazanı və ya nömrə inventarı
üçün hazır API təqdim etmir. Oradakı `/api/v1/messages` çağırışı
SMS tarixçəsidir; **nömrə inventarı deyil**. Kənar layihədə açıq
qalmış token və bot hesablarından istifadə edilmir.

İdarə etdiyiniz IVASPER instansiyasında yalnız istifadəsinə icazə verilmiş
nömrələr üçün ayrıca HTTPS JSON endpoint-i təqdim edin. Render
servisinin **Environment** bölməsində bu dəyərləri təyin edin:

- `IVASPER_NUMBERS_URL`: öz HTTPS nömrə inventar endpoint-iniz
- `IVASPER_NUMBERS_TOKEN`: endpoint Bearer token tələb edirsə, öz məxfi tokeniniz

*Bu dəyərləri GitHub koduna yazmayın.* Endpoint özünüzə məxsus
nömrə inventarı mənbəyi olmalıdır; SMS/OTP feed-i olmamalıdır.

Dəstəklənən sadə JSON:

```json
{
  "numbers": [
    {"number": "+994501234567", "country": "Azerbaijan", "service": "Telegram"},
    {"number": "+447701112222", "country": "United Kingdom", "service": "WhatsApp"}
  ]
}
```

Bu nömrələr yalnız format nümunəsidir. Adapter həmçinin Ivasmsper-in
`services → Telegram → countries → Azerbaijan → numbers`
formatını oxuya bilir. Nömrələr yalnız ayrıca `/api/ivasper` admin
endpoint-ində **oxuma rejimində** görünür.

## İstifadə

Sayt və Telegram Mini App → **⚙️ Admin → 🧰 IVASPER nömrələr**.
Ölkə, xidmət və nömrə axtarışı; kopyalama düyməsi.

Telegram şəxsi çat: `/ivasper` → **IVASPER nömrələr** → ölkə → səhifə.
Admin girişinin serverdə yoxlanması məcburidir.

`IVASPER_NUMBERS_URL` təyin edilməyibsə, bölmə **mənbə qoşulmayıb**
xəbərdarlığı göstərir və IVASMS nömrələri ilə siyahını doldurmur.
Provider xətası və ya boş inventar real nömrə varmış kimi göstərilmir.

Testlər:

```bash
python -m unittest -v test_ivasper_admin.py test_ivasper_web.py
node --check docs/app.js
node test_ivasper_web_ui.cjs
```
