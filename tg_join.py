import asyncio
import json
import os
from datetime import datetime

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    InviteHashInvalidError,
    UserAlreadyParticipantError,
    UsernameInvalidError,
    ChannelPrivateError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# ==========================================
# НАСТРОЙКИ
# ==========================================

API_ID = 30888167
API_HASH = "18818dfeae3021fff280b45689190013"
PHONE = "79220773356"

SESSION_NAME = "telegram_session"

MAX_ACTIONS_PER_SESSION = 4
WAIT_BETWEEN_ACTIONS = 3
WAIT_BETWEEN_SESSIONS = 600

LOG_FILE = "telegram_join_log.json"

# ==========================================
# СТАТИСТИКА
# ==========================================

class Stats:
    def __init__(self):
        self.success = 0
        self.already_member = 0
        self.invalid = 0
        self.private = 0
        self.errors = 0
        self.total = 0
        self.start_time = datetime.now()

    def get_summary(self):
        elapsed = int(
            (datetime.now() - self.start_time).total_seconds()
        )

        return {
            "success": self.success,
            "already_member": self.already_member,
            "invalid": self.invalid,
            "private": self.private,
            "errors": self.errors,
            "total": self.total,
            "elapsed_seconds": elapsed,
        }


stats = Stats()

# ==========================================
# ЛОГИ
# ==========================================

def save_log(data):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(data, ensure_ascii=False)
            + "\n"
        )

# ==========================================
# ОБРАБОТКА ССЫЛОК
# ==========================================

def is_invite_link(link):
    return (
        "t.me/+" in link
        or "joinchat" in link
    )


def extract_invite_hash(link):
    if "+" in link:
        return (
            link.split("+")[-1]
            .strip("/")
            .strip()
        )

    return (
        link.split("/")[-1]
        .strip("/")
        .strip()
    )


def extract_username(link):
    username = link.strip()

    username = username.replace(
        "https://t.me/", ""
    )

    username = username.replace(
        "http://t.me/", ""
    )

    username = username.replace(
        "t.me/", ""
    )

    if username.startswith("@"):
        username = username[1:]

    return username.strip("/")

# ==========================================
# ВСТУПЛЕНИЕ
# ==========================================

async def join_chat(client, link):

    if is_invite_link(link):

        invite_hash = extract_invite_hash(link)

        await client(
            ImportChatInviteRequest(invite_hash)
        )

        return "joined_by_invite"

    username = extract_username(link)

    entity = await client.get_entity(username)

    await client(
        JoinChannelRequest(entity)
    )

    return "joined_channel"

# ==========================================
# ОСНОВНАЯ ЛОГИКА
# ==========================================

async def process_links(links):
    client = TelegramClient(session=SESSION_NAME, api_hash=API_HASH, api_id=API_ID, device_model = "iPhone 13 Pro Max", system_version = "14.8.1", app_version = "8.4", lang_code = "en", system_lang_code = "en-US")

    await client.start(phone=PHONE)

    me = await client.get_me()

    print(
        f"✅ Авторизован как "
        f"{me.first_name} ({me.id})"
    )

    actions_count = 0
    session_number = 1

    try:

        for index, link in enumerate(
            links,
            start=1
        ):

            if actions_count >= MAX_ACTIONS_PER_SESSION:

                print(
                    f"\n⏳ Лимит "
                    f"{MAX_ACTIONS_PER_SESSION} "
                    f"действий достигнут"
                )

                print(
                    f"⏰ Жду "
                    f"{WAIT_BETWEEN_SESSIONS} сек..."
                )

                await asyncio.sleep(
                    WAIT_BETWEEN_SESSIONS
                )

                actions_count = 0
                session_number += 1

                print(
                    f"\n🔄 Новая сессия "
                    f"#{session_number}"
                )

            print(
                f"\n[{index}/{len(links)}] "
                f"{link}"
            )

            try:

                result = await join_chat(
                    client,
                    link
                )

                print(
                    f"✅ Успешно: {result}"
                )

                stats.success += 1

                save_log({
                    "link": link,
                    "status": result,
                    "timestamp":
                        datetime.now().isoformat()
                })

            except UserAlreadyParticipantError:

                print(
                    "ℹ️ Уже участник"
                )

                stats.already_member += 1

                save_log({
                    "link": link,
                    "status":
                        "already_member",
                    "timestamp":
                        datetime.now().isoformat()
                })

            except InviteHashInvalidError:

                print(
                    "❌ Неверная ссылка"
                )

                stats.invalid += 1

                save_log({
                    "link": link,
                    "status":
                        "invalid_invite",
                    "timestamp":
                        datetime.now().isoformat()
                })

            except UsernameInvalidError:

                print(
                    "❌ Неверный username"
                )

                stats.invalid += 1

                save_log({
                    "link": link,
                    "status":
                        "invalid_username",
                    "timestamp":
                        datetime.now().isoformat()
                })

            except ChannelPrivateError:

                print(
                    "🔒 Приватный канал"
                )

                stats.private += 1

                save_log({
                    "link": link,
                    "status":
                        "private_channel",
                    "timestamp":
                        datetime.now().isoformat()
                })

            except FloodWaitError as e:

                print(
                    f"🚫 FloodWait "
                    f"{e.seconds} сек"
                )

                await asyncio.sleep(
                    e.seconds + 5
                )

                continue

            except Exception as e:

                print(
                    f"❌ Ошибка: {e}"
                )

                stats.errors += 1

                save_log({
                    "link": link,
                    "status": "error",
                    "error": str(e),
                    "timestamp":
                        datetime.now().isoformat()
                })

            stats.total += 1
            actions_count += 1

            if index < len(links):
                await asyncio.sleep(
                    WAIT_BETWEEN_ACTIONS
                )

    finally:
        await client.disconnect()

# ==========================================
# MAIN
# ==========================================

async def main():

    links = []

    if os.path.exists("groups.txt"):

        with open(
            "groups.txt",
            "r",
            encoding="utf-8"
        ) as f:

            links = [
                line.strip()
                for line in f
                if line.strip()
            ]

    if not links:

        links = [
            "https://t.me/sportivnye_predprinimateli",
            "https://t.me/resto_business",
            "https://t.me/flowerclublive",
            "https://t.me/sewingtechnologist",
            "https://t.me/deepfoodtech",
            "https://t.me/arinkinaleksey",
            "https://t.me/avto_rx",
            "https://t.me/joinchat/VlCPa_0OIl4ECnT5",
            "https://t.me/joinchat/AAAAAA2jpapYiYrgQ4CmrQ",
            "https://t.me/+I1IKphaN4FxhY2Qy",
            "https://t.me/joinchat/Q-xVvGi8FXM3NDYy",
            "https://t.me/joinchat/aQjUfQYGHdNiMzFi",
            "https://t.me/joinchat/gQdUAVV-vSBmZmQy",
            "https://t.me/joinchat/3dKi-3pSHtU5Nzcy",
            "https://t.me/+VHxwbEi39jLXK8Ha",
            "https://t.me/+_45y-dw1Cxk5ODMy",
            "https://t.me/speakerclub_ru_bot",
            "https://t.me/joinchat/FwHveRHHQbE1TjkxXRifSQ",
            "https://t.me/+5j79JdAfEMU5ODYy",
            "https://t.me/+DvpYLYf54OZlZDky",
            "https://t.me/+OKqHkLvioC1mMGM6",
            "https://t.me/+3UBiNG7Grl1lYTdi",
            "https://t.me/joinchat/oMWA8zXV-sthOTEy",
            "https://t.me/marketingsmm01",
            "https://t.me/+STWXjPedKcDnESot",
            "https://t.me/water_all",
            "https://t.me/fromBerek",
            "https://t.me/drivemoscow_chat",
            "https://t.me/pinterestchat_21",

        ]

    print(
        f"🚀 Загружено ссылок: "
        f"{len(links)}"
    )

    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    await process_links(links)

    print("\n" + "=" * 50)
    print("СТАТИСТИКА")
    print("=" * 50)

    summary = stats.get_summary()

    for k, v in summary.items():
        print(f"{k}: {v}")

    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())