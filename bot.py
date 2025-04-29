import io
import os
import time
import asyncio
import requests

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyromod import listen

# --------------------------
# Paramètres d'authentification Telegram
BOT_TOKEN = "7634028476:AAHDjeRCagDKlxtVmRV3SoBBRgAG4nG0tbw"
API_ID = "23992653"
API_HASH = "ef7ad3a6a3e88b487108cd5242851ed4"

# --------------------------
# Initialisation du bot
Bot = Client(
    "Thumb-Bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
    workdir=".",
    in_memory=True,
)

# --------------------------
# Variables globales
thumb_path = ""
sequence_mode = {}  # {user_id: True/False}
sequence_files = {}  # {user_id: [messages]}

# --------------------------
# Textes et boutons
START_TXT = """
👋 Hi {}, I am a Thumbnail Setter and File Renamer Bot.

📥 Send me a **photo** to set as your thumbnail.
📂 Then send me **videos/files** and I will apply your thumbnail!
"""

START_BTN = InlineKeyboardMarkup(
    [[InlineKeyboardButton('Source Code', url='https://github.com/soebb/thumb-change-bot')]]
)

# --------------------------
# Fonctions utilitaires
def human_readable(size):
    return f"{size / (1024 * 1024):.2f} MB"

async def progress_bar(current, total, message, task="Uploading"):
    if not hasattr(message, "c_time"):
        return

    elapsed_time = time.time() - message.c_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    done = int(20 * current / total)
    percentage = (current / total) * 100
    bar = '█' * done + '░' * (20 - done)

    text = f"""╭━━━━❰ {task} ❱━➣
┣⪼ 🗃️ Taille : {human_readable(current)} / {human_readable(total)}
┣⪼ ⏳ Progression : {percentage:.2f}%
┣⪼ 🚀 Vitesse : {human_readable(speed)}/s
┣⪼ ⏰️ Reste : {int(eta)}s
╰━━━━━━━━━━━━━━━➣
`{bar}`
"""
    try:
        await message.edit(text)
    except:
        pass

def sync_time():
    try:
        response = requests.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
        if response.status_code == 200:
            utc_datetime = response.json()["utc_datetime"]
            print(f"Horloge synchronisée à {utc_datetime}")
    except Exception as e:
        print(f"Erreur de synchronisation de l'heure : {e}")

# --------------------------
# Gestion des commandes

@Bot.on_message(filters.command(["start"]))
async def start(bot, update):
    text = START_TXT.format(update.from_user.mention)
    await update.reply_text(text=text, disable_web_page_preview=True, reply_markup=START_BTN)

@Bot.on_message(filters.private & filters.photo)
async def set_thumb(bot, m):
    global thumb_path
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)
    thumb_path = await m.download()
    await m.reply_text("✅ Thumbnail has been set successfully!\nNow send me a video or document.")

@Bot.on_message(filters.command(["seq_start"]))
async def seq_start(bot, m):
    user_id = m.from_user.id
    sequence_mode[user_id] = True
    sequence_files[user_id] = []
    await m.reply_text("✅ Séquence démarrée ! Envoyez tous vos fichiers.\nQuand vous avez fini, tapez `/seq_stop`.")

@Bot.on_message(filters.command(["seq_stop"]))
async def seq_stop(bot, m):
    user_id = m.from_user.id
    if not sequence_mode.get(user_id):
        await m.reply_text("⚠️ Vous n'avez pas démarré de séquence. Tapez `/seq_start` d'abord.")
        return

    files = sequence_files.get(user_id, [])
    if not files:
        await m.reply_text("⚠️ Aucun fichier à traiter.")
    else:
        await m.reply_text(f"🚀 Traitement de {len(files)} fichier(s)...")
        for file_message in files:
            await handle_individual_file(bot, file_message)
        await m.reply_text("✅ Tous les fichiers ont été traités !")

    # Reset
    sequence_mode[user_id] = False
    sequence_files[user_id] = []

@Bot.on_message(filters.private & (filters.video | filters.document))
async def handle_file(bot, m):
    user_id = m.from_user.id
    if sequence_mode.get(user_id):
        sequence_files[user_id].append(m)
        await m.reply_text("📥 Fichier ajouté à la séquence.")
    else:
        await handle_individual_file(bot, m)

async def handle_individual_file(bot, m):
    if not thumb_path:
        await m.reply_text("⚠️ Please set a thumbnail first by sending a photo.")
        return

    msg = await m.reply("📥 **Downloading Started...**")
    msg.c_time = time.time()

    file_dl_path = await bot.download_media(
        message=m,
        progress=progress_bar,
        progress_args=(msg, "Downloading")
    )

    await msg.edit("🚀 Uploading file... Please wait!")
    msg.c_time = time.time()

    if m.document:
        await bot.send_document(
            chat_id=m.chat.id,
            document=file_dl_path,
            thumb=thumb_path,
            caption=m.caption if m.caption else None,
            progress=progress_bar,
            progress_args=(msg, "Uploading")
        )
    elif m.video:
        await bot.send_video(
            chat_id=m.chat.id,
            video=file_dl_path,
            thumb=thumb_path,
            caption=m.caption if m.caption else None,
            supports_streaming=True,
            progress=progress_bar,
            progress_args=(msg, "Uploading")
        )

    await msg.delete()
    os.remove(file_dl_path)

# --------------------------
# Lancement du bot
async def main():
    print("🚀 Démarrage du bot...")
    sync_time()
    await Bot.start()
    await Bot.idle()

if __name__ == "__main__":
    asyncio.run(main())
