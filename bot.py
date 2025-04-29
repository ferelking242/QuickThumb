import os
import re
import time
import asyncio
from pyrogram.enums import ChatAction
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

API_ID = "23992653"
API_HASH = "ef7ad3a6a3e88b487108cd5242851ed4"
BOT_TOKEN = "7634028476:AAHDjeRCagDKlxtVmRV3SoBBRgAG4nG0tbw"

app = Client("rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

SEQUENCE_MODE = False
RECEIVED_FILES = []
CURRENT_THUMB = None
RENAME_MODE = False
RENAME_INFO = {}
PENDING_FILE = None
SEND_AS_VIDEO = False

THUMBNAIL_DIR = "thumbnail"
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

async def progress_bar(current, total, message, status="Uploading"):
    now = time.time()
    percentage = current * 100 / total
    progress = round(20 * current / total)
    bar = "█" * progress + "░" * (20 - progress)

    speed = current / (now - message.date.timestamp() + 1)
    eta = (total - current) / (speed + 1)

    text = f"""╭━━━━❰ ᴘʀᴏɢʀᴇss ʙᴀʀ ❱━➣
┣⪼ {status}
┣⪼ 🗃️ Sɪᴢᴇ: {round(current / 1024 / 1024, 2)} MB | {round(total / 1024 / 1024, 2)} MB
┣⪼ ⏳️ Dᴏɴᴇ : {round(percentage, 1)}%
┣⪼ 🚀 Sᴩᴇᴇᴅ: {round(speed / 1024 / 1024, 2)} MB/s
┣⪼ ⏰️ Eᴛᴀ: {int(eta)}s
╰━━━━━━━━━━━━━━━➣
{bar}"""

    try:
        await message.edit(text)
    except:
        pass

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "👋 Bienvenue sur le Bot de renommage !\n\n📦 Version : 1.2\n\nEnvoyez une image pour définir une miniature.\nUtilisez /seq_start pour commencer une séquence, /seq_stop pour l'arrêter, /info pour voir les infos d'un fichier, /show_thumb pour voir la miniature actuelle."
    )

@app.on_message(filters.command("seq_start"))
async def start_sequence(client, message):
    global SEQUENCE_MODE, RECEIVED_FILES
    SEQUENCE_MODE = True
    RECEIVED_FILES = []
    await message.reply("✅ Séquence démarrée. Envoyez vos fichiers maintenant.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Stop", callback_data="stop_seq")]]))

@app.on_message(filters.command("seq_stop"))
async def stop_sequence(client, message):
    global SEQUENCE_MODE, RENAME_MODE
    SEQUENCE_MODE = False
    RENAME_MODE = True
    await message.reply("🛑 Séquence arrêtée. Envoyez le nom souhaité. Exemple :\nExemple : baby {1} VF")

@app.on_message(filters.command("stop"))
async def stop_copy(client, message):
    global SEQUENCE_MODE, RECEIVED_FILES, RENAME_MODE
    SEQUENCE_MODE = False
    RECEIVED_FILES = []
    RENAME_MODE = False
    await message.reply("🛑 Copie interrompue.")

@app.on_message(filters.command("info"))
async def info_file(client, message):
    target = message.reply_to_message
    if target and (target.document or target.video):
        media = target.document or target.video
        text = (
            f"📄 **Nom :** `{media.file_name}`\n"
            f"📦 **Taille :** {round(media.file_size / 1024 / 1024, 2)} MB\n"
            f"🎬 **Type :** {'Vidéo' if target.video else 'Document'}"
        )
        await message.reply(text)
    else:
        await message.reply("❌ Répondez à un fichier vidéo/document pour voir ses informations.")

@app.on_message(filters.command("show_thumb"))
async def show_thumb(client, message):
    path = os.path.join(THUMBNAIL_DIR, "thumbnail.jpg")
    if os.path.exists(path):
        await message.reply_photo(photo=path, caption="🖼️ Miniature actuelle")
    else:
        await message.reply("❌ Aucune miniature définie.")

@app.on_message(filters.photo)
async def set_thumbnail(client, message):
    global CURRENT_THUMB
    path = os.path.join(THUMBNAIL_DIR, "thumbnail.jpg")
    CURRENT_THUMB = await message.download(file_name=path)
    await message.reply("✅ Miniature définie pour tous les fichiers.")

@app.on_callback_query()
async def handle_buttons(client, callback_query):
    global PENDING_FILE, SEQUENCE_MODE, RENAME_MODE, SEND_AS_VIDEO
    data = callback_query.data

    if data == "stop_seq":
        SEQUENCE_MODE = False
        RENAME_MODE = True
        await callback_query.message.edit_text("🛑 Séquence arrêtée. Envoyez le nom souhaité. Exemple :\nExemple : baby {1} VF")
        return

    if not PENDING_FILE:
        await callback_query.message.edit_text("❌ Aucun fichier en attente.")
        return

    if data == "rename_no":
        await send_with_progress(client, PENDING_FILE, None)
        await callback_query.message.edit_text("📤 Fichier envoyé sans modification de nom.")
        PENDING_FILE = None
    elif data == "rename_yes_doc":
        SEND_AS_VIDEO = False
        await callback_query.message.edit_text("✏️ Entrez le nom final. Exemple :\nMon super film {1}")
    elif data == "rename_yes_vid":
        SEND_AS_VIDEO = True
        await callback_query.message.edit_text("✏️ Entrez le nom final. Exemple :\nMon super film {1}")

@app.on_message(filters.document | filters.video)
async def receive_files(client, message):
    global SEQUENCE_MODE, RECEIVED_FILES, PENDING_FILE
    if SEQUENCE_MODE:
        RECEIVED_FILES.append(message)
        await message.reply("📥 Fichier reçu.")
    else:
        PENDING_FILE = message
        buttons = InlineKeyboardMarkup([ 
            [InlineKeyboardButton("✅ Renommer comme Vidéo", callback_data="rename_yes_vid"),
             InlineKeyboardButton("✅ Renommer comme Document", callback_data="rename_yes_doc")],
            [InlineKeyboardButton("❌ Ne pas renommer", callback_data="rename_no")]
        ])
        await message.reply("📥 Fichier reçu, que souhaitez-vous faire ?", reply_markup=buttons)

@app.on_message(filters.text & ~filters.command([]))
async def process_rename(client, message):
    global RENAME_MODE, RECEIVED_FILES, PENDING_FILE, RENAME_INFO, SEND_AS_VIDEO

    template = message.text.strip()
    
    if RECEIVED_FILES:
        # Séquence multiple
        if "{1}" in template:
            RENAME_INFO = {"template": template, "ep": 1}
            await process_files(client, message)
        else:
            await message.reply("❌ Format invalide. Ajoutez {1} pour les fichiers en séquence.\nEx : Film S01 EP{1}")
        return

    if PENDING_FILE:
        # Un seul fichier
        media = PENDING_FILE.document or PENDING_FILE.video
        ext = os.path.splitext(media.file_name)[1]
        if not template.endswith(ext):
            template += ext

        await process_file(client, message, PENDING_FILE, manual=True)
        PENDING_FILE = None
        return

    await message.reply("❌ Aucun fichier à traiter ou format invalide.")

async def send_with_progress(client, msg, filename=None):
    media = msg.document or msg.video
    original_ext = os.path.splitext(media.file_name)[1]
    name_to_send = filename if filename else media.file_name
    if not name_to_send.endswith(original_ext):
        name_to_send += original_ext

    path = await msg.download(progress=lambda c, t: None)

    # Choisir l'envoi selon le type de fichier
    if SEND_AS_VIDEO and msg.video:
        send_func = client.send_video
    else:
        send_func = client.send_document

    progress_msg = await msg.reply("⬇️ Téléchargement...")
    await client.send_chat_action(msg.chat.id, ChatAction.UPLOAD_DOCUMENT)
    
    # Fonction pour afficher la progression du téléchargement
    async def download_progress(current, total):
        await progress_bar(current, total, progress_msg, status="Downloading")

    # Envoi du fichier
    if msg.video:
        await send_func(
            chat_id=msg.chat.id,
            video=path,
            file_name=name_to_send,
            thumb=CURRENT_THUMB,
            progress=download_progress
        )
    elif msg.document:
        await send_func(
            chat_id=msg.chat.id,
            document=path,
            file_name=name_to_send,
            thumb=CURRENT_THUMB,
            progress=download_progress
        )

    await progress_msg.edit_text("✅ Fichier envoyé.")
    os.remove(path)

async def process_files(client, message):
    """Processing multiple files in sequence"""
    global RECEIVED_FILES  # Ajoutez cette ligne pour accéder à la variable globale
    for idx, msg in enumerate(RECEIVED_FILES):
        file_name = RENAME_INFO['template'].replace("{1}", str(RENAME_INFO["ep"]))
        await send_with_progress(client, msg, file_name)
        RENAME_INFO["ep"] += 1
    RECEIVED_FILES = []  # Réinitialisation de la liste après traitement

async def process_file(client, message, file, manual=False):
    """Process a single file with renaming"""
    if manual:
        await send_with_progress(client, file)

# Exécution de l'application (la boucle principale)
if __name__ == "__main__":
    app.run()
