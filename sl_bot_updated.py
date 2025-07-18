#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SL Telegram Bot - Python Version (Updated)
Мониторинг склада материалов и тонеров
"""

import os
import json
import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from threading import Thread
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SLBot:
    def __init__(self):
        # Загрузка переменных окружения
        load_dotenv()
        
        self.bot_token = os.getenv('BOT_TOKEN')
        self.google_service_key = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_JSON')
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        if not self.google_service_key:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY_JSON не установлен в .env файле")
        
        # Файл для сохранения chat_id
        self.chat_file = 'chats.json'
        self.chat_ids = self.load_chats()
        
        # Инициализация Firebase
        self.init_firebase()
        
        # Создание приложения Telegram
        self.application = Application.builder().token(self.bot_token).build()
        self.setup_handlers()
        
        # Флаг для планировщика
        self.scheduler_started = False
    
    def load_chats(self):
        """Загрузка сохраненных chat_id"""
        try:
            with open(self.chat_file, 'r', encoding='utf-8') as f:
                chat_list = json.load(f)
                logger.info(f"Загружены чаты: {chat_list}")
                return set(chat_list)
        except FileNotFoundError:
            logger.info("Файл чатов не найден, будет создан новый")
            return set()
        except json.JSONDecodeError:
            logger.error("Ошибка чтения файла чатов")
            return set()
    
    def save_chats(self):
        """Сохранение chat_id в файл"""
        try:
            with open(self.chat_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.chat_ids), f, ensure_ascii=False, indent=2)
            logger.info(f"Чаты сохранены: {self.chat_ids}")
        except Exception as e:
            logger.error(f"Ошибка сохранения чатов: {e}")
    
    def init_firebase(self):
        """Инициализация Firebase Admin"""
        try:
            service_account = json.loads(self.google_service_key)
            cred = credentials.Certificate(service_account)
            
            # Проверяем, не инициализирован ли уже Firebase
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            logger.info("Firebase успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Firebase: {e}")
            raise
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        
        # Обработчики кнопок клавиатуры
        self.application.add_handler(MessageHandler(filters.Regex("^(Статус)$"), self.status_command))
        self.application.add_handler(MessageHandler(filters.Regex("^(Тест)$"), self.test_command))
        
        # Обработчик неизвестных команд
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.unknown_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        chat_id = update.effective_chat.id
        
        # Добавляем новый chat_id
        if chat_id not in self.chat_ids:
            self.chat_ids.add(chat_id)
            self.save_chats()
            logger.info(f"Зарегистрирован новый чат: {chat_id}")
        
        # Запускаем планировщик если еще не запущен
        if not self.scheduler_started:
            self.start_scheduler()
            self.scheduler_started = True
        
        # Создаем клавиатуру
        keyboard = [['Статус', 'Тест']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(
            'Бот запущен и готов к работе!',
            reply_markup=reply_markup
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status - показ статуса материалов"""
        chat_id = update.effective_chat.id
        await self.get_materials_status(chat_id, context)
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test - тестовая проверка материалов"""
        chat_id = update.effective_chat.id
        await self.check_materials(chat_id, context)
    
    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных команд"""
        await update.message.reply_text('Неизвестная команда')
    
    async def check_materials(self, chat_id, context):
        """Проверка материалов на складе (низкие остатки)"""
        try:
            # Проверка материалов (бумага) - ТОЛЬКО со статусом "new"
            materials_ref = self.db.collection('Materials').where('status', '==', 'new')
            materials_docs = materials_ref.stream()
            
            low_materials = []
            for doc in materials_docs:
                data = doc.to_dict()
                qty = data.get('qty', 0)
                material_type = data.get('type', doc.id)
                
                if qty <= 3:
                    low_materials.append({'type': material_type, 'qty': qty})
            
            if low_materials:
                msg = 'Склад бумаги. Следующие материалы заканчиваются:\n\n'
                for material in low_materials:
                    msg += f"{material['type']}: {material['qty']} шт.\n"
                msg += '\nНеобходим срочный заказ!'
                
                await context.bot.send_message(chat_id=chat_id, text=msg)
            
            # Проверка тонеров (без изменений)
            toners_ref = self.db.collection('TonersStorage')
            toners_docs = toners_ref.stream()
            
            low_toners = []
            for doc in toners_docs:
                data = doc.to_dict()
                qty = data.get('qty', 0)
                color = data.get('color', doc.id)
                
                if qty <= 8:
                    low_toners.append({'color': color, 'qty': qty})
            
            if low_toners:
                msg = 'Склад тонеров. Следующие тонеры заканчиваются:\n\n'
                for toner in low_toners:
                    msg += f"{toner['color']}: {toner['qty']} шт.\n"
                msg += '\nНеобходим срочный заказ!'
                
                await context.bot.send_message(chat_id=chat_id, text=msg)
                
        except Exception as e:
            logger.error(f"Ошибка проверки материалов: {e}")
    
    async def get_materials_status(self, chat_id, context):
        """Получение полного статуса всех материалов"""
        try:
            # Получение материалов - ТОЛЬКО со статусом "new"
            materials_ref = self.db.collection('Materials').where('status', '==', 'new')
            materials_docs = materials_ref.stream()
            
            msg = 'Текущее количество материалов (новые):\n\n'
            
            # Порядок вывода материалов
            types_order = ['FA', 'FH', 'PA', 'PH', 'Clear', 'Metall', 'Verge']
            data_map = {}
            
            for doc in materials_docs:
                data = doc.to_dict()
                material_type = data.get('type', doc.id)
                qty = data.get('qty', 0)
                data_map[material_type] = qty
            
            if not data_map:
                msg += 'Нет доступных новых материалов'
            else:
                for material_type in types_order:
                    qty = data_map.get(material_type, 0)
                    msg += f"{material_type}: {qty} шт.\n"
            
            # Получение тонеров (без изменений)
            toners_ref = self.db.collection('TonersStorage')
            toners_docs = toners_ref.stream()
            
            msg += '\n\nТекущее количество тонеров:\n\n'
            
            toners_found = False
            for doc in toners_docs:
                data = doc.to_dict()
                color = data.get('color', doc.id)
                qty = data.get('qty', 0)
                msg += f"{color}: {qty} шт.\n"
                toners_found = True
            
            if not toners_found:
                msg += 'Нет доступных тонеров'
            
            # Проверка аудита склада
            audit_ref = self.db.collection('inventoryCheck')
            audit_docs = audit_ref.stream()
            
            audit_msg = '\nАудит склада сегодня не проводился'
            latest_audit = None
            
            for doc in audit_docs:
                data = doc.to_dict()
                date_val = data.get('date')
                
                if date_val:
                    # Обработка Firebase Timestamp
                    if hasattr(date_val, 'timestamp'):
                        date_obj = datetime.fromtimestamp(date_val.timestamp())
                    else:
                        date_obj = datetime.strptime(str(date_val), '%Y-%m-%d %H:%M:%S')
                    
                    if not latest_audit or date_obj > latest_audit['date']:
                        latest_audit = {
                            'date': date_obj,
                            'userName': data.get('userName', 'Неизвестно')
                        }
            
            if latest_audit:
                today = datetime.now().date()
                if latest_audit['date'].date() == today:
                    audit_msg = f"\nАудит склада выполнен сегодня. Исполнитель: {latest_audit['userName']}"
            
            msg += audit_msg
            
            await context.bot.send_message(chat_id=chat_id, text=msg)
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса материалов: {e}")
            await context.bot.send_message(
                chat_id=chat_id, 
                text='Ошибка при получении статуса материалов'
            )
    
    def check_materials_job(self):
        """Задача для планировщика - проверка материалов"""
        logger.info("Запуск плановой проверки материалов в 22:00")
        
        # Создаем новый event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Создаем приложение для отправки сообщений
        app = Application.builder().token(self.bot_token).build()
        
        async def send_checks():
            async with app:
                for chat_id in self.chat_ids:
                    await self.check_materials(chat_id, app)
        
        try:
            loop.run_until_complete(send_checks())
        except Exception as e:
            logger.error(f"Ошибка в плановой проверке: {e}")
        finally:
            loop.close()
    
    def start_scheduler(self):
        """Запуск планировщика задач"""
        # Планируем проверку каждый день в 22:00
        schedule.every().day.at("22:00").do(self.check_materials_job)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
        
        # Запускаем планировщик в отдельном потоке
        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Планировщик запущен. Проверка материалов каждый день в 22:00")
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск SL Telegram Bot...")
        
        try:
            # Используем run_polling() для версии 20+
            self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise

def main():
    """Главная функция"""
    print("=" * 50)
    print("    SL Telegram Bot - Python Version")
    print("    Мониторинг склада материалов")
    print("    Обновлено: фильтр по статусу new")
    print("=" * 50)
    
    try:
        bot = SLBot()
        bot.run()
    except KeyboardInterrupt:
        print("\nОстановка бота...")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main() 