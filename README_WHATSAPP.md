# WhatsApp bağlantı testi (təhlükəsiz inteqrasiya)

Orijinal `Whatsapp bot(1).zip` arxivində sonsuz dövrdə WhatsApp qeydiyyat kodu tələb edən skript var. Bu kod **istifadə olunmur**. Arxivdəki 350 MB `numbers.json` bazası da təhlükəsizlik/məxfilik səbəbindən layihəyə əlavə edilmir.

Bu inteqrasiya yalnız adminlər üçün iki komanda əlavə edir:

- `/wa_status` — WhatsApp Cloud API parametrlərinin mövcudluğunu yoxlayır; şəbəkəyə sorğu göndərmir.
- `/wa_test` — yalnız əvvəlcədən `WA_TEST_RECIPIENT` dəyişənində müəyyən edilmiş, sizin nəzarətinizdə olan və mesaj almağa razılaşmış bir nömrəyə *bir ədəd sabit mətn* göndərir; beş dəqiqəlik limit və avtomatik təkrar etməmə qaydası var.

## Render Environment dəyişənləri

```
WA_ACCESS_TOKEN=your_meta_system_user_access_token
WA_PHONE_NUMBER_ID=your_whatsapp_business_phone_number_id
WA_TEST_RECIPIENT=994501112233
WA_GRAPH_VERSION=v25.0
```

`WA_TEST_RECIPIENT` nümunədir, yalnız sizin icazəli real test nömrənizi yazın. `WA_ACCESS_TOKEN`-i GitHub koduna yerləşdirməyin. WhatsApp Business Platform (Cloud API) hesabı lazımdır. Azad mətn mesajları üçün müştərinin son 24 saatda biznesə yazmış olması tələb oluna bilər; əks halda Meta uyğun şablon tələb edə bilər. API-nin mesajı qəbul etməsi çatdırılmaya zəmanət vermir.

## Test

```
python -m unittest discover -s tests -v
```

Yerli testlər API-ni simulyasiya edir, real WhatsApp-a mesaj göndərmir. Real test yalnız Render-də etibarnamələr verildikdən və admin `/wa_test` yazdıqdan sonra işə düşəcək.

## Mövcud ivasmss layihəsinə əlavə etmə

`whatsapp_safe.py` və `integrate_into_ivasmss.py` fayllarını botun `main.py` faylı olan qovluğa köçürün, sonra:

```
python integrate_into_ivasmss.py
python -m unittest discover -s tests -v
```

İnteqrasiya skripti `main.py`-yə yalnız import və iki admin komandasını qeydiyyata alan bir sətr əlavə edir. Mövcud `main.py` faylını `main.py.before_whatsapp_safe.bak` adı ilə ehtiyatlayır. Bir neçə dəfə işə salındıqda eyni dəyişiklikləri təkrarlamır. WhatsApp parametrlərini Render > Environment bölməsində yazın və yenidən deploy edin.
