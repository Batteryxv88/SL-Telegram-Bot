run = "npm install && npm start"
language = "nodejs" 
import 'dotenv/config';
import admin from 'firebase-admin';
import fetch from 'node-fetch';

// --- ENV-переменные (задать в Replit Secrets) ---
const BOT_TOKEN = process.env.BOT_TOKEN;
if (!BOT_TOKEN) {
  console.error('Error: BOT_TOKEN not set');
  process.exit(1);
}

if (!process.env.GOOGLE_SERVICE_ACCOUNT_KEY_JSON) {
  console.error('Error: GOOGLE_SERVICE_ACCOUNT_KEY_JSON not set');
  process.exit(1);
}

// --- Инициализация Firebase Admin ---
const serviceAccount = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_KEY_JSON);
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});
const db = admin.firestore();

// --- Состояние бота ---
let CHAT_ID = null;
let lastUpdateId = 0;
let scheduled = false;

// --- Утилита отправки в Telegram ---
async function sendTelegramMessage(chatId, text) {
  try {
    const res = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text })
    });
    if (!res.ok) {
      const err = await res.json();
      console.error('Telegram API error:', err);
    }
  } catch (e) {
    console.error('sendTelegramMessage error:', e);
  }
}

// --- Чтение обновлений от Telegram ---
async function getUpdates() {
  try {
    const res = await fetch(
      `https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=${lastUpdateId + 1}`
    );
    const payload = await res.json();
    if (payload.ok && payload.result.length) {
      for (const upd of payload.result) {
        lastUpdateId = upd.update_id;
        if (upd.message) {
          const chatId = upd.message.chat.id;
          const text   = upd.message.text;
          if (!CHAT_ID) {
            CHAT_ID = chatId;
            console.log('Got CHAT_ID:', CHAT_ID);
            if (!scheduled) {
              scheduleNextCheck();
              scheduled = true;
            }
          }
          await handleCommand(chatId, text);
        }
      }
    }
  } catch (e) {
    console.error('getUpdates error:', e);
  }
}

// --- Проверка материалов на складе ---
async function checkMaterials(chatId) {
  try {
    const snapshot = await db.collection('Materials').get();
    const low = [];
    snapshot.forEach(doc => {
      const d = doc.data();
      const qty  = d.qty || 0;
      const type = d.type || doc.id;
      if (qty <= 3) low.push({ type, qty });
    });
    if (low.length) {
      let msg = 'Склад бумаги. Следующие материалы заканчиваются:\n\n';
      low.forEach(m => { msg += `${m.type}: ${m.qty} шт.\n`; });
      msg += '\nНеобходим срочный заказ!';
      await sendTelegramMessage(chatId, msg);
    }
  } catch (e) {
    console.error('checkMaterials error:', e);
  }
}

// --- Статус всех материалов ---
async function getMaterialsStatus(chatId) {
  try {
    const snapshot = await db.collection('Materials').get();
    let msg = 'Текущее количество материалов:\n\n';
    if (snapshot.empty) {
      msg += 'Нет доступных материалов';
    } else {
      snapshot.forEach(doc => {
        const d = doc.data();
        const qty  = d.qty || 0;
        const type = d.type || doc.id;
        msg += `${type}: ${qty} шт.\n`;
      });
    }
    await sendTelegramMessage(chatId, msg);
  } catch (e) {
    console.error('getMaterialsStatus error:', e);
    await sendTelegramMessage(chatId, 'Ошибка при получении статуса материалов');
  }
}

// --- Обновление количества одного материала ---
async function updateMaterialQuantity(chatId, id, quantity) {
  try {
    await db.collection('Materials').doc(id).update({ qty: parseInt(quantity) });
    await sendTelegramMessage(
      chatId,
      `Количество материала ${id} обновлено до ${quantity} шт.`
    );
  } catch (e) {
    console.error('updateMaterialQuantity error:', e);
    await sendTelegramMessage(chatId, 'Ошибка при обновлении количества материала');
  }
}

// --- Обработка команд ---
async function handleCommand(chatId, text) {
  const [cmd, ...args] = text.split(' ');
  switch (cmd) {
    case '/start':
      await sendTelegramMessage(chatId, 'Бот запущен и готов к работе!');
      break;
    case '/status':
      await getMaterialsStatus(chatId);
      break;
    case '/set':
      if (args.length === 2) {
        await updateMaterialQuantity(chatId, args[0], args[1]);
      } else {
        await sendTelegramMessage(chatId, 'Использование: /set [материал] [количество]');
      }
      break;
    case '/test':
      await checkMaterials(chatId);
      await sendTelegramMessage(chatId, 'Проверка материалов выполнена');
      break;
    default:
      await sendTelegramMessage(chatId, 'Неизвестная команда');
  }
}

// --- Расписание ежедневной проверки в 22:00 ---
function scheduleNextCheck() {
  const now    = new Date();
  const target = new Date();
  target.setHours(22, 0, 0, 0);
  if (now > target) target.setDate(target.getDate() + 1);
  const delay = target - now;
  console.log('Next check at', target.toLocaleString());
  setTimeout(async () => {
    if (CHAT_ID) await checkMaterials(CHAT_ID);
    scheduleNextCheck();
  }, delay);
}

// --- Старт бота ---
(async () => {
  console.log('Bot is starting …');
  await getUpdates();
  setInterval(getUpdates, 5000);
})(); 

