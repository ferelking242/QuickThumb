import os
import shutil
import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message

# -- CONFIG --
API_ID = "23992653"
API_HASH = "ef7ad3a6a3e88b487108cd5242851ed4"
BOT_TOKEN = "7634028476:AAHDjeRCagDKlxtVmRV3SoBBRgAG4nG0tbw"

app = Client("thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# -- VARIABLES --
user_thumbnails = {}       # user_id: list of thumbnail paths
user_seq_files = {}        # user_id: list of file messages
seq_active = {}            # user_id: bool
paused_users = {}          # user_id: bool

MAX_CONCURRENT_TASKS = 3   # Nombre de fichiers traités en parallèle

# -- SETUP DOSSIER --
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# -- COMMANDES BOT --

@app.on_message(filters.command("set_thumb") & filters.private)
async def set_thumbnail(client, message: Message):
    if message.reply_to_message and message.reply_to_message.photo:
        thumb_dir = f"downloads/thumbs_{message.from_user.id}"
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = await message.reply_to_message.download(file_name=f"{thumb_dir}/{random.randint(1,99999)}.jpg")
        user_thumbnails.setdefault(message.from_user.id, []).append(thumb_path)
        await message.reply("✅ Miniature enregistrée avec succès !")
    else:
        await message.reply("❌ Réponds à une photo avec /set_thumb.")

@app.on_message(filters.command("del_thumb") & filters.private)
async def delete_thumbnails(client, message: Message):
    thumb_dir = f"downloads/thumbs_{message.from_user.id}"
    if os.path.exists(thumb_dir):
        shutil.rmtree(thumb_dir)
    user_thumbnails.pop(message.from_user.id, None)
    await message.reply("✅ Toutes les miniatures supprimées.")

@app.on_message(filters.command("seq_start") & filters.private)
async def start_seq(client, message: Message):
    seq_active[message.from_user.id] = True
    user_seq_files[message.from_user.id] = []
    paused_users[message.from_user.id] = False
    await message.reply("🚀 Mode Séquence activé ! Envoie tes fichiers.")

@app.on_message(filters.command("seq_stop") & filters.private)
async def stop_seq(client, message: Message):
    user_id = message.from_user.id
    if seq_active.get(user_id):
        await message.reply("🛠️ Traitement en cours...")

        files = user_seq_files.get(user_id, [])
        total_files = len(files)

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        tasks = []
        progress_message = await message.reply(f"⏳ 0/{total_files} fichiers traités...")

        for idx, msg in enumerate(files):
            tasks.append(process_file(client, message, msg, idx + 1, total_files, progress_message, semaphore))

        await asyncio.gather(*tasks)

        # Nettoyage
        seq_active.pop(user_id, None)
        user_seq_files.pop(user_id, None)
        await progress_message.edit("✅ Tous les fichiers traités avec succès !")
    else:
        await message.reply("❌ Aucun mode Séquence actif.")

@app.on_message(filters.command("pause") & filters.private)
async def pause_processing(client, message: Message):
    paused_users[message.from_user.id] = True
    await message.reply("⏸️ Traitement en pause.")

@app.on_message(filters.command("resume") & filters.private)
async def resume_processing(client, message: Message):
    paused_users[message.from_user.id] = False
    await message.reply("▶️ Traitement relancé.")

@app.on_message(filters.private & (filters.video | filters.document))
async def collect_files(client, message: Message):
    if seq_active.get(message.from_user.id):
        user_seq_files[message.from_user.id].append(message)
        await message.reply("✅ Fichier enregistré pour traitement.")
    else:
        await message.reply("❗ Utilise /seq_start avant d'envoyer des fichiers.")

# -- PROCESSUS PRINCIPAL --

async def process_file(client, command_message, file_message, counter, total_files, progress_message, semaphore):
    user_id = command_message.from_user.id
    async with semaphore:
        while paused_users.get(user_id, False):
            await asyncio.sleep(1)

        file_path = await file_message.download(file_name=f"downloads/file_{random.randint(1,99999)}")
        thumb_list = user_thumbnails.get(user_id, [])
        thumb_path = thumb_list[(counter - 1) % len(thumb_list)] if thumb_list else None

        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        new_file_name = f"fichier_{counter}{ext}"
        output_path = f"downloads/{new_file_name}"

        if thumb_path:
            cmd = f'ffmpeg -i "{file_path}" -i "{thumb_path}" -map 0 -map 1 -c copy -disposition:1 attached_pic "{output_path}" -y'
            os.system(cmd)
        else:
            shutil.copy(file_path, output_path)

        await command_message.reply_document(output_path, caption=f"🎬 {new_file_name}")

        await progress_message.edit(f"⏳ {counter}/{total_files} fichiers traités...")

        # Nettoyage
        os.remove(file_path)
        os.remove(output_path)

# -- LANCEMENT --
app.run()
