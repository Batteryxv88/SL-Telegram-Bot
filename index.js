import 'dotenv/config';
import admin from 'firebase-admin';
import fetch from 'node-fetch';
import express from 'express';
import fs from 'fs';

const CHAT_FILE = 'chats.json';
// Load saved chat IDs
let CHAT_IDS = new Set();
try {
  const raw = fs.readFileSync(CHAT_FILE, 'utf8');
  CHAT_IDS = new Set(JSON.parse(raw));
  console.log('Loaded chats:', [...CHAT_IDS]);
} catch (e) {
  console.log('No existing chats file, will create it.');
}
function saveChats() {
  fs.writeFileSync(CHAT_FILE, JSON.stringify([...CHAT_IDS], null, 2), 'utf8');
}

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
// let CHAT_ID = null; // больше не используется
let lastUpdateId = 0;
let scheduled = false;

// --- Утилита отправки в Telegram ---
async function sendTelegramMessage(chatId, text, options = {}) {
  try {
    const res = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text, ...options })
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
          // Save chat ID if new
          if (!CHAT_IDS.has(chatId)) {
            CHAT_IDS.add(chatId);
            saveChats();
            console.log('Registered new chat:', chatId);
          }
          if (!scheduled) {
            scheduleNextCheck();
            scheduled = true;
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

// Helper to compare dates ignoring time
function isSameDay(d1, d2) {
  return d1.getFullYear() === d2.getFullYear() &&
         d1.getMonth() === d2.getMonth() &&
         d1.getDate() === d2.getDate();
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
    // Добавляем информацию об аудите склада
    const auditSnap = await db.collection('inventoryCheck').get();
    let auditMsg = '\nАудит склада сегодня не проводился';
    if (!auditSnap.empty) {
      let latest = null;
      auditSnap.forEach(doc => {
        const d = doc.data();
        const dateVal = d.date;
        const dateObj = dateVal.toDate ? dateVal.toDate() : new Date(dateVal);
        if (!latest || dateObj > latest.date) {
          latest = { date: dateObj, userName: d.userName };
        }
      });
      const today = new Date();
      if (latest && isSameDay(latest.date, today)) {
        auditMsg = `\nАудит склада выполнен сегодня. Исполнитель: ${latest.userName}`;
      }
    }
    msg += auditMsg;
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
      await sendTelegramMessage(chatId, 'Бот запущен и готов к работе!', {
        reply_markup: {
          keyboard: [
            ['Статус', 'Тест']
          ],
          resize_keyboard: true,
          one_time_keyboard: false
        }
      });
      break;

    case '/status':
    case 'Статус':
      await getMaterialsStatus(chatId);
      break;

    case '/test':
    case 'Тест':
      await checkMaterials(chatId);
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
    // Send checks to all chats
    for (const id of CHAT_IDS) {
      await checkMaterials(id);
    }
    scheduleNextCheck();
  }, delay);
}

// --- Старт бота ---
(async () => {
  console.log('Bot is starting …');
  await getUpdates();
  setInterval(getUpdates, 5000);
})(); 

//robor
const app = express();

app.get('/ping', (req, res) => {
  res.send('Bot is alive!');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Express server is running on port ${PORT}`);
});


