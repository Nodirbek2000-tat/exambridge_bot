# ExamBridge Telegram bot

aiogram 2.25.2. Sayt (exambridge.uz) bilan bitta serverda, bitta Docker tarmog'ida ishlaydi.

## Nima qiladi

- **/start** — majburiy kanallarga a'zolikni tekshiradi, telefon raqam orqali saytda akkaunt ochadi.
- **💎 Premium sotib olish** — tarif (1 oy / 3 oy) → karta raqami → o'quvchi chek yuboradi →
  chek **@exambridgemoney** kanaliga ✅ / ❌ tugmalari bilan tushadi → admin tasdiqlasa Premium ochiladi
  va o'quvchiga xabar boradi.
- **🌐 Saytga kirish** — 10 daqiqalik bir martalik havola, parolsiz kirish.
- Saytdagi **Pay via Telegram** tugmasi o'quvchining sayt akkauntini botga ulaydi (`/start link_...`).
- **/admin** (faqat `ADMINS`) — sayt statistikasi va majburiy kanallar (qo'shish / o'chirish).
  Kanal qo'shishda bot o'sha kanalda admin bo'lmasa, darhol "Bot admin emas" deydi.

Karta raqami va narxlar sayt admin panelida: **Admin panel → Payments**.

## Serverga o'rnatish

1. @BotFather → `/newbot` → token oling.
2. Botni **@exambridgemoney** kanaliga **admin** qiling (post yozish huquqi bilan).
3. Saytning `.env` fayliga (`~/ExamBridge.uz/.env`):

   ```
   TELEGRAM_BOT_TOKEN=<token>
   TELEGRAM_BOT_USERNAME=<bot username, @ siz>
   TELEGRAM_BOT_API_SECRET=<uzun tasodifiy kalit>
   TELEGRAM_PAYMENTS_CHAT=@exambridgemoney
   ```

   va saytni qayta ishga tushiring: `docker compose up -d --build`.
4. Bot papkasida `.env.dist` dan `.env` yarating, `BOT_TOKEN`, `ADMINS`, `BOT_API_SECRET`
   (saytdagi `TELEGRAM_BOT_API_SECRET` bilan bir xil) ni yozing.
5. `docker compose up -d --build` — bot ishga tushgach, adminlarga "🤖 Bot ishga tushdi" xabari keladi.

Loglar: `docker compose logs -f bot`

> Bitta token bilan faqat bitta bot nusxasi ishlashi mumkin. Serverda ishlayotgan paytda
> kompyuterda o'sha token bilan ishga tushirmang.

## Lokal ishga tushirish

```
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.dist .env   # BACKEND_URL=http://127.0.0.1:8000, BACKEND_HOST= (bo'sh)
venv\Scripts\python app.py
```
