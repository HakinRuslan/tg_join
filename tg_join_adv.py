import asyncio
import time
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError, InviteHashInvalidError, UserAlreadyParticipantError
import json
import os
 
# ⚙️ НАСТРОЙКИ
api_id = "30888167"
hash_id = "18818dfeae3021fff280b45689190013"
PHONE = "79220773356"
 
MAX_JOINS_PER_SESSION = 4
WAIT_BETWEEN_JOINS = 2
WAIT_BETWEEN_SESSIONS = 3600
 
# Логирование
LOG_FILE = "telegram_join_log.json"
RESULTS_FILE = "results.txt"
 
# Статистика
class Stats:
    def __init__(self):
        self.successful = 0
        self.already_member = 0
        self.invalid_link = 0
        self.errors = 0
        self.total = 0
        self.start_time = datetime.now()
    
    def to_dict(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            "timestamp": self.start_time.isoformat(),
            "successful": self.successful,
            "already_member": self.already_member,
            "invalid_link": self.invalid_link,
            "errors": self.errors,
            "total": self.total,
            "success_rate": f"{(self.successful/self.total*100):.1f}%" if self.total > 0 else "0%",
            "elapsed_seconds": int(elapsed)
        }
 
stats = Stats()
 
async def join_chats(links):
    """Входит в список чатов с логированием"""
    client = TelegramClient(session=session_name, api_hash=hash_id, api_id=api_id, device_model = "iPhone 13 Pro Max", system_version = "14.8.1", app_version = "8.4", lang_code = "en", system_lang_code = "en-US")
    
    try:
        await client.start(phone=PHONE)
        user = await client.get_me()
        print(f"✅ Авторизирован как {user.first_name}")
        
        joins_count = 0
        session_count = 0
        results = []
        
        for i, link in enumerate(links, 1):
            try:
                # Проверка лимита
                if joins_count >= MAX_JOINS_PER_SESSION:
                    print(f"\n⏳ Достигнут лимит {MAX_JOINS_PER_SESSION} входов")
                    print(f"⏰ Ожидаю {WAIT_BETWEEN_SESSIONS} сек перед новой сессией...")
                    
                    # Сохраняю лог перед ожиданием
                    save_log(results)
                    
                    await asyncio.sleep(WAIT_BETWEEN_SESSIONS)
                    joins_count = 0
                    session_count += 1
                    print(f"🔄 Сессия #{session_count + 1}\n")
                
                # Извлекаю хеш из ссылки
                try:
                    hash_link = link.split('/')[-1]
                except:
                    print(f"[{i}/{len(links)}] ❌ Неверный формат ссылки: {link}")
                    stats.invalid_link += 1
                    results.append({
                        "link": link,
                        "status": "invalid_format",
                        "timestamp": datetime.now().isoformat()
                    })
                    stats.total += 1
                    continue
                
                print(f"[{i}/{len(links)}] 🔗 Обработка: {link[:50]}...")
                
                try:
                    result = await client(
                        __import__('telethon').functions.messages.ImportChatInviteRequest(
                            hash=hash_link
                        )
                    )
                    print(f"  ✅ Успешно!")
                    stats.successful += 1
                    results.append({
                        "link": link,
                        "status": "success",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except UserAlreadyParticipantError:
                    print(f"  ℹ️  Уже в чате")
                    stats.already_member += 1
                    results.append({
                        "link": link,
                        "status": "already_member",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except InviteHashInvalidError:
                    print(f"  ❌ Неверная/истекшая ссылка")
                    stats.invalid_link += 1
                    results.append({
                        "link": link,
                        "status": "invalid_hash",
                        "timestamp": datetime.now().isoformat()
                    })
                
                joins_count += 1
                stats.total += 1
                
                # Пауза перед следующим
                if i < len(links):
                    await asyncio.sleep(WAIT_BETWEEN_JOINS)
                    
            except FloodWaitError as e:
                print(f"  🚫 Лимит Telegram. Жди {e.seconds} сек...")
                stats.errors += 1
                results.append({
                    "link": link,
                    "status": "flood_wait",
                    "wait_seconds": e.seconds,
                    "timestamp": datetime.now().isoformat()
                })
                stats.total += 1
                await asyncio.sleep(e.seconds + 5)
                
            except Exception as e:
                print(f"  ❌ Ошибка: {str(e)}")
                stats.errors += 1
                results.append({
                    "link": link,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                stats.total += 1
        
        # Финальный лог
        save_log(results)
        print_summary(stats)
        
    finally:
        await client.disconnect()
 
def save_log(results):
    """Сохраняет результаты в JSON"""
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"💾 Лог сохранён в {LOG_FILE}")
 
def print_summary(stats):
    """Выводит итоговую статистику"""
    data = stats.to_dict()
    print("\n" + "="*50)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*50)
    print(f"✅ Успешных входов: {data['successful']}")
    print(f"ℹ️  Уже в чатах: {data['already_member']}")
    print(f"❌ Неверных ссылок: {data['invalid_link']}")
    print(f"⚠️  Ошибок: {data['errors']}")
    print(f"📈 Всего обработано: {data['total']}")
    print(f"💯 Успешность: {data['success_rate']}")
    print(f"⏱️  Время выполнения: {data['elapsed_seconds']} сек")
    print("="*50 + "\n")
 
async def main():
    # Загружаю ссылки
    links = []
    
    # Или из кода
    if not links:
        links = [
            "https://t.me/+AbCdEfGhIjKlMn",
            "https://t.me/+XyZaBcDeFgHiJk",
            "https://t.me/sdam_prodam_Moskva",
            "https://t.me/commercial_apex_realty",
            "https://t.me/moskvartira",
            "https://t.me/realtmart_chat",
            "https://t.me/arenda_msk_collife",
            "https://t.me/+G6aoIiXnhKozZTVi",
            "https://t.me/gladston_ru",
            "https://t.me/nedvizhimosti_moskva",
            "https://t.me/Kommerch",
            "https://t.me/nedvizmos",
            "https://t.me/mediarealty_chat",
            "https://t.me/realtorussia"
        ]
    
    if not links:
        print("❌ Нет ссылок!")
        return
    
    print(f"🚀 TELEGRAM JOIN BOT")
    print(f"{'='*50}")
    print(f"📝 Ссылок к обработке: {len(links)}")
    print(f"⚙️  Батч-размер: {MAX_JOINS_PER_SESSION}")
    print(f"⏰ Пауза между батчами: {WAIT_BETWEEN_SESSIONS} сек ({WAIT_BETWEEN_SESSIONS//60} мин)")
    print(f"{'='*50}\n")
    
    # Удаляю старый лог
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    await join_chats(links)
 
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Скрипт остановлен пользователем")
        print_summary(stats)
