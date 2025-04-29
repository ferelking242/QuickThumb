import io
import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyromod import listen

# Paramètres d'authentification Telegram
BOT_TOKEN = "7634028476:AAHDjeRCagDKlxtVmRV3SoBBRgAG4nG0tbw"
API_ID = "23992653"
API_HASH = "ef7ad3a6a3e88b487108cd5242851ed4"

# Initialisation du bot avec Pyrogram
Bot = Client(
    "Thumb-Bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
    workdir=".",
    in_memory=True,
)

# Texte de démarrage du bot
START_TXT = """
👋 Hi {}, I am a Thumbnail Setter and File Renamer Bot.

📥 Send me a **photo** to set as your thumbnail.
📂 Then send me **videos/files** and I will apply your thumbnail!
"""

# Bouton source du code
START_BTN = InlineKeyboardMarkup(
    [[InlineKeyboardButton('Source Code', url='https://github.com/soebb/thumb-change-bot')]]
)

# Chemin global pour le thumbnail
thumb_path = ""

# Mode séquence et fichiers dans la séquence
sequence_mode = {}  # {user_id: True/False}
sequence_files = {}  # {user_id: [messages]}


def human_readable(size):
    return f"{size / (1024 * 1024):.2f} MB"


# Fonction pour afficher une barre de progression lors du téléchargement ou de l'upload
async def progress_bar(current, total, message, task="Uploading"):
    done = int(20 * current / total)
    percentage = (current / total) * 100
    speed = current / (time.time() - message.c_time)
    eta = (total - current) / speed if speed != 0 else 0

    bar = '█' * done + '░' * (20 - done)

    text = f"""╭━━━━❰ {task} ❱━➣
┣⪼ 🗃️ Taille : {human_readable(current)} / {human_readable(total)}
┣⪼ ⏳️ Progression : {percentage:.2f}%
┣⪼ 🚀 Vitesse : {human_readable(speed)}/s
┣⪼ ⏰️ Reste : {int(eta)}s
╰━━━━━━━━━━━━━━━➣
`{bar}`
"""
    try:
        await message.edit(text)
    except:
        pass


# Commande de démarrage du bot
@Bot.on_message(filters.command(["start"]))
async def start(bot, update):
    text = START_TXT.format(update.from_user.mention)
    await update.reply_text(text=text, disable_web_page_preview=True, reply_markup=START_BTN)


# Commande pour définir un thumbnail
@Bot.on_message(filters.private & filters.photo)
async def set_thumb(bot, m):
    global thumb_path
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)
    thumb_path = await m.download()
    await m.reply_text("✅ Thumbnail has been set successfully!\nNow send me a video or document.")


# Commande pour démarrer une séquence de fichiers
@Bot.on_message(filters.command(["seq_start"]))
async def seq_start(bot, m):
    user_id = m.from_user.id
    sequence_mode[user_id] = True
    sequence_files[user_id] = []
    await m.reply_text("✅ Séquence démarrée ! Envoyez tous vos fichiers.\nQuand vous avez fini, tapez `/seq_stop`.")


# Commande pour arrêter une séquence de fichiers
@Bot.on_message(filters.command(["seq_stop"]))
async def seq_stop(bot, m):
    user_id = m.from_user.id
    if not sequence_mode.get(user_id):
        await m.reply_text("⚠️ Vous n'avez pas démarré de séquence. Tapez `/seq_start` d'abord.")
        return

    files = sequence_files.get(user_id, [])
    if not files:
        await m.reply_text("⚠️ Aucun fichier à traiter.")
        sequence_mode[user_id] = False
        sequence_files[user_id] = []
        return

    await m.reply_text(f"🚀 Traitement de {len(files)} fichier(s)...")

    for file_message in files:
        await handle_individual_file(bot, file_message)

    # Réinitialiser
    sequence_mode[user_id] = False
    sequence_files[user_id] = []
    await m.reply_text("✅ Tous les fichiers ont été traités !")


# Traitement des fichiers envoyés (en dehors de la séquence)
@Bot.on_message(filters.private & (filters.video | filters.document))
async def handle_file(bot, m):
    user_id = m.from_user.id

    # Si on est en mode séquence, on stocke seulement
    if sequence_mode.get(user_id):
        sequence_files[user_id].append(m)
        await m.reply_text("📥 Fichier ajouté à la séquence.")
    else:
        # Sinon, traiter immédiatement
        await handle_individual_file(bot, m)


# Fonction pour traiter un fichier individuellement
async def handle_individual_file(bot, m):
    global thumb_path
    if not thumb_path:
        await m.reply_text("⚠️ Please set a thumbnail first by sending a photo.")
        return

    msg = await m.reply("📥 **Downloading Started...**")
    msg.c_time = time.time()

    # Télécharger le fichier et afficher la barre de progression
    file_dl_path = await bot.download_media(
        message=m,
        progress=progress_bar,
        progress_args=(msg, "Downloading")
    )

    await msg.edit("🚀 Uploading file... Please wait!")
    msg.c_time = time.time()

    # Envoyer le fichier téléchargé
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

    # Supprimer le fichier après l'envoi
    await msg.delete()
    os.remove(file_dl_path)


# Fonction principale sans synchronisation de l'heure
async def main():
    print("🚀 Démarrage du bot...")
    await Bot.start()
    await Bot.idle()  # <-- Cette ligne permet au bot de rester en vie

if __name__ == "__main__":
    asyncio.run(main())
