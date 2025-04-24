# Telegram + Firestore Bot на Replit

## Настройка

1. Перейдите в "Secrets" (Environment Variables) Replit:
   - **BOT_TOKEN** = `<ваш токен от BotFather>`
   - **GOOGLE_SERVICE_ACCOUNT_KEY_JSON** = содержимое вашего Service Account JSON (скопируйте весь JSON в одну строку или экранируйте переводы строк `\n`).

2. Нажмите **Run**.

## Команды бота

- `/start` — запустить бота
- `/status` — вывести текущие остатки материалов
- `/set <id> <qty>` — установить количество материала `<id>` в `<qty>`
- `/test` — ручная проверка низкого остатка

## Планы

- Автоматическая ежедневная проверка в 22:00 