# Tələb olunan kanallar

Üç keçid [`required_channels.defaults.json`](required_channels.defaults.json) faylında saxlanılır. Bot başlayanda `data_storage.data_path()` bu siyahını yerli `required_channels.json` ilə birləşdirir. Mövcud əlavə kanallar və uyğun keçidlərin chat ID-ləri qorunur. GitHub-dakı konfiqurasiyadan hazır olan kanallar hər restart/deploy zamanı yenidən siyahıya əlavə edilir.

| Kanal | Keçid | Üzvlük yoxlaması üçün |
|---|---|---|
| @betrunaz | https://t.me/betrunaz | `betrunaz` istifadəçi adı konfiqurasiyadadır |
| Kanal 2 | https://t.me/+zNOPEh3GpI83ZDli | Rəqəmsal chat ID lazımdır |
| Kanal 3 | https://t.me/+MCTJqBiqQ1piMjIy | Rəqəmsal chat ID lazımdır |

İki gizli keçidin `chat_id` sahəsi hazırda `null`-dır. Telegram dəvət linkini üzvlük yoxlamasında chat ID kimi qəbul etmir. Əvvəlki yerli qeyddə həmin keçidin chat ID-si varsa istifadə olunur. Əks halda keçid mənbə faylında saxlanır, lakin ID qurulanadək yeni məcburi üzvlük tələbi kimi aktivləşmir. Əvvəldən mövcud tələblər silinmir.

## Gizli kanalların ID-lərini daimi saxlamaq

Həqiqi mənfi Telegram chat ID-sini uyğun keçidin `chat_id` sahəsinə yazıb deploy edin. Alternativ olaraq Render Environment bölməsində bunları təyin etmək olar:

| Dəyişən | Uyğun kanal |
|---|---|
| `REQUIRED_CHANNEL_2_ID` | `https://t.me/+zNOPEh3GpI83ZDli` |
| `REQUIRED_CHANNEL_3_ID` | `https://t.me/+MCTJqBiqQ1piMjIy` |

Mühit dəyişənində düzgün mənfi ID varsa o, fayldakı ID-dən üstün tutulur. Dəvət linkinin sonundakı mətn chat ID deyil. Yerli faylda saxlanan ID qalıcı disk yoxdursa itə bilər; GitHub və ya Render dəyişənində saxlanması bunu aradan qaldırır.

Botu hər kanalda admin edin. Digər istifadəçilərin üzvlüyünün etibarlı yoxlanması üçün bu lazımdır: [Telegram getChatMember](https://core.telegram.org/bots/api#getchatmember).

Bot menyusundan edilən dəyişikliklər yerli siyahıya təsir edir. Sabit kanalın silinməsini daimi etmək üçün GitHub-dakı standart siyahıdan və botun yerli siyahısından silmək lazımdır; yalnız botdan silinən sabit kanal növbəti başlanğıcda geri gəlir.

## Yoxlama

```bash
python -m unittest test_required_channels_config -v
```

Testlər linklərin saxlanmasını, mövcud ID-lərin qorunmasını, yeni gizli kanalların ID-siz aktivləşməməsini və başlanğıcda konfiqurasiyanın bərpasını yoxlayır. Canlı Telegram üzvlüyü bu testlərlə təsdiqlənmir.
