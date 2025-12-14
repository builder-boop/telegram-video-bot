import asyncio
import os
import uuid
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL
from config import (
    BOT_TOKEN,
    OWNER_ID,
    DOWNLOAD_DIR,
    LIMIT_PUBLIC,
    LIMIT_UNLOCKED,
    MAX_PUBLIC_RES,
    MAX_UNLOCKED_RES
)

# --- INIT BOT ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- HELPER FUNCTIONS ---
def load_data():
    if not os.path.exists("data.json"):
        return {"unlocked_users": [], "stats": {"total_download":0, "video":0, "audio":0}}
    with open("data.json", "r") as f:
        return json.load(f)

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)

def is_owner(uid):
    return uid == OWNER_ID

def is_unlocked(uid, data):
    return uid in data.get("unlocked_users", [])

def can_download(uid, data):
    if is_owner(uid):
        return True
    data.setdefault("usage", {})
    today = str(uuid.uuid1().time)[:8]
    used = data["usage"].get(uid, {}).get(today, 0)
    limit = LIMIT_UNLOCKED if is_unlocked(uid, data) else LIMIT_PUBLIC
    if used >= limit:
        return False
    data["usage"].setdefault(uid, {})[today] = used + 1
    save_data(data)
    return True

def detect_platform(url):
    url = url.lower()
    if "youtube" in url or "youtu.be" in url:
        return "YouTube"
    if "tiktok" in url:
        return "TikTok"
    if "instagram" in url:
        return "Instagram"
    return "Unknown"

def quality_keyboard(uid, url):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="360p", callback_data=f"v|360|{url}"),
                InlineKeyboardButton(text="720p", callback_data=f"v|720|{url}")
            ],
            [
                InlineKeyboardButton(text="MP3", callback_data=f"a|0|{url}")
            ]
        ]
    )
    return keyboard

# --- COMMAND HANDLERS ---
@dp.message(CommandStart())
async def start(message: types.Message):
    uid = message.from_user.id
    data = load_data()
    role = "👑 Owner (Unlimited)" if is_owner(uid) else ("🔓 Unlocked (max 720p)" if is_unlocked(uid, data) else "👤 Public (max 360p)")
    await message.answer(
        f"📥 *Advanced Video Downloader*\n\nStatus kamu: {role}\n\nKirim link video untuk mulai download 🎬",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    data = load_data()
    s = data["stats"]
    await message.answer(
        f"📊 Statistik Bot\n\n"
        f"⬇ Total download: {s['total_download']}\n"
        f"🎬 Video: {s['video']}\n"
        f"🎵 Audio: {s['audio']}\n"
        f"👤 Unlocked user: {len(data['unlocked_users'])}"
    )

@dp.message(Command("unlock"))
async def unlock(message: types.Message):
    uid = message.from_user.id
    data = load_data()
    if uid not in data["unlocked_users"]:
        data["unlocked_users"].append(uid)
        save_data(data)
        await message.answer("✅ Kamu berhasil unlock! Maks resolusi 720p")
    else:
        await message.answer("ℹ️ Kamu sudah unlock sebelumnya")

# --- URL HANDLER ---
@dp.message()
async def handle_url(message: types.Message):
    uid = message.from_user.id
    url = message.text.strip()

    if url.startswith("/"):
        return

    platform = detect_platform(url)
    if platform == "Unknown":
        return await message.answer("❌ Platform tidak didukung.")

    data = load_data()
    if not can_download(uid, data):
        return await message.answer("⏱ Limit harian tercapai")

    keyboard = quality_keyboard(uid, url)
    await message.answer(f"🔎 Platform: *{platform}*\nPilih format:", parse_mode="Markdown", reply_markup=keyboard)

# --- CALLBACK HANDLER ---
@dp.callback_query()
async def callback_handler(call: types.CallbackQuery):
    mode, quality, url = call.data.split("|", 2)
    uid = call.from_user.id
    data = load_data()
    max_res = 9999 if is_owner(uid) else MAX_UNLOCKED_RES if is_unlocked(uid, data) else MAX_PUBLIC_RES

    if mode == "v" and int(quality) > max_res:
        return await call.answer(f"🔒 Max resolusi {max_res}p", show_alert=True)
    if not can_download(uid, data):
        return await call.message.answer("⏱ Limit harian tercapai")

    await call.message.edit_text("⏳ Sedang mengunduh...")
    uid_file = uuid.uuid4().hex
    filepath = f"{DOWNLOAD_DIR}/{uid_file}"

    ydl_opts = {
        "outtmpl": filepath + ".%(ext)s",
        "quiet": True,
        "proxy": PROXY,
        "noplaylist": True,
        "merge_output_format": "mp4"
    }
    if mode == "v":
        ydl_opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best"
    else:
        ydl_opts.update({
            "format": "bestaudio",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        final_file = f"{filepath}.{'mp3' if mode=='a' else 'mp4'}"

        if mode == "a":
            await call.message.answer_audio(types.FSInputFile(final_file))
        else:
            await call.message.answer_video(types.FSInputFile(final_file))

        data["stats"]["total_download"] += 1
        data["stats"]["video"] += 1 if mode=="v" else 0
        data["stats"]["audio"] += 1 if mode=="a" else 0
        save_data(data)
        os.remove(final_file)

    except Exception as e:
        await call.message.answer(f"❌ Error:\n`{e}`", parse_mode="Markdown")

# --- MAIN LOOP ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
