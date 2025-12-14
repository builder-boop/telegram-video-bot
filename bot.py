# =========================
# TELEGRAM VIDEO BOT (AIROGRAM v3) - FIXED
# =========================

import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# =========================
# CONFIG
# =========================
BOT_TOKEN = "ISI_TOKEN_BOT_KAMU_DI_SINI"  # TANPA SPASI
OWNER_ID = 123456789  # ganti dengan ID telegram kamu (angka)

DOWNLOAD_DIR = "downloads"

LIMIT_PUBLIC = 5
LIMIT_UNLOCKED = 50

MAX_PUBLIC_RES = 720
MAX_UNLOCKED_RES = 2160

# =========================
# GLOBAL DATA (SIMPLE)
# =========================
user_usage = {}
unlocked_users = set()

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =========================
# HELPER FUNCTIONS
# =========================

def is_unlocked(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in unlocked_users


def check_limit(user_id: int) -> bool:
    limit = LIMIT_UNLOCKED if is_unlocked(user_id) else LIMIT_PUBLIC
    return user_usage.get(user_id, 0) < limit


def increase_usage(user_id: int):
    user_usage[user_id] = user_usage.get(user_id, 0) + 1


def detect_platform(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    if "tiktok.com" in url:
        return "TikTok"
    if "instagram.com" in url:
        return "Instagram"
    return "Unknown"


def quality_keyboard(uid: int, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="360p", callback_data=f"q|360|{url}"),
                InlineKeyboardButton(text="720p", callback_data=f"q|720|{url}"),
            ],
            [
                InlineKeyboardButton(text="1080p", callback_data=f"q|1080|{url}"),
            ]
        ]
    )

# =========================
# BOT SETUP
# =========================
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# =========================
# COMMANDS
# =========================
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "👋 <b>Video Downloader Bot</b>\n\n"
        "Kirim link YouTube / TikTok / Instagram untuk download video."
    )


@dp.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer(
        f"📊 <b>Stats</b>\n"
        f"Users: {len(user_usage)}\n"
        f"Unlocked: {len(unlocked_users)}"
    )

# =========================
# HANDLE URL
# =========================
@dp.message()
async def handle_url(message: types.Message):
    try:
        uid = message.from_user.id
        url = message.text.strip()

        if url.startswith("/"):
            return

        platform = detect_platform(url)
        if platform == "Unknown":
            await message.answer("❌ Platform tidak didukung")
            return

        if not check_limit(uid):
            await message.answer("🚫 Limit harian tercapai")
            return

        keyboard = quality_keyboard(uid, url)
        await message.answer(
            f"📥 <b>{platform}</b> terdeteksi\nPilih kualitas:",
            reply_markup=keyboard
        )

    except Exception as e:
        await message.answer(f"⚠️ Error: {e}")

# =========================
# CALLBACK
# =========================
@dp.callback_query()
async def handle_quality(callback: types.CallbackQuery):
    try:
        data = callback.data.split("|")
        if data[0] != "q":
            return

        quality = data[1]
        url = data[2]
        uid = callback.from_user.id

        increase_usage(uid)

        await callback.message.edit_text(
            f"⏬ Download dimulai\nKualitas: <b>{quality}p</b>"
        )

        # SIMULASI DOWNLOAD
        await asyncio.sleep(2)

        await callback.message.answer("✅ Download selesai (dummy)")
        await callback.answer()

    except Exception as e:
        await callback.answer("Error", show_alert=True)

# =========================
# MAIN
# =========================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
