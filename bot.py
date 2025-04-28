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
user_seq_files = {}        # user_id: dict of {seq_name: file messages}
seq_active = {}            # user_id: seq_name
paused_users = {}          # user_id: bool
cancelled_users = {}       # user_id: bool
MAX_CONCURRENT_TASKS = 3   # Nombre de fichiers traités en parallèle
replace_rules = {}         # user_id: list of (search, replace)

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
    seq_name = message.text.split(" ", 1)[1] if len(message.text.split()) > 1 else "default_seq"
    user_id = message.from_user.id

    seq_active[user_id] = seq_name
    user_seq_files.setdefault(user_id, {}).setdefault(seq_name, [])

    await message.reply(f"🚀 Séquence '{seq_name}' démarrée ! Envoie tes fichiers à traiter.")

@app.on_message(filters.command("seq_stop") & filters.private)
async def stop_seq(client, message: Message):
    user_id = message.from_user.id
    seq_name = seq_active.get(user_id)

    if seq_name:
        files = user_seq_files[user_id].get(seq_name, [])
        total_files = len(files)
        
        await message.reply(f"📋 Séquence '{seq_name}' enregistrée avec {total_files} fichier(s).")
        
        # Sauvegarder la séquence et préparer les fichiers pour traitement ultérieur
        seq_active.pop(user_id, None)
    else:
        await message.reply("❌ Aucune séquence active pour l'utilisateur.")

@app.on_message(filters.command("view_seqs") & filters.private)
async def view_seqs(client, message: Message):
    user_id = message.from_user.id
    seqs = user_seq_files.get(user_id, {})

    if seqs:
        seq_list = "\n".join([f"{seq}: {len(files)} fichier(s)" for seq, files in seqs.items()])
        await message.reply(f"📋 Séquences enregistrées :\n{seq_list}")
    else:
        await message.reply("❌ Aucune séquence trouvée.")

@app.on_message(filters.command("exec") & filters.private)
async def exec_seq(client, message: Message):
    seq_name = message.text.split(" ", 1)[1] if len(message.text.split()) > 1 else None
    user_id = message.from_user.id

    if seq_name:
        seq_files = user_seq_files.get(user_id, {}).get(seq_name, [])
        if seq_files:
            for idx, file_message in enumerate(seq_files):
                # Traiter le fichier ici (ajouter la miniature, renommer, etc.)
                await file_message.edit(f"📦 Traitement du fichier {idx + 1}/{len(seq_files)}...")
            
            await message.reply(f"✅ Séquence '{seq_name}' exécutée.")
        else:
            await message.reply(f"❌ Aucune séquence trouvée avec le nom '{seq_name}'.")
    else:
        await message.reply("❌ Veuillez fournir un nom de séquence.")

@app.on_message(filters.document | filters.video | filters.photo & filters.private)
async def handle_files(client, message: Message):
    user_id = message.from_user.id
    seq_name = seq_active.get(user_id)

    if seq_name:
        # Ajouter le fichier à la séquence active
        user_seq_files[user_id][seq_name].append(message)
        await message.reply(f"✅ Fichier ajouté à la séquence '{seq_name}'.")

@app.on_message(filters.command("pause") & filters.private)
async def pause_processing(client, message: Message):
    paused_users[message.from_user.id] = True
    await message.reply("⏸️ Traitement en pause.")

@app.on_message(filters.command("resume") & filters.private)
async def resume_processing(client, message: Message):
    paused_users[message.from_user.id] = False
    await message.reply("▶️ Traitement relancé.")

@app.on_message(filters.command("cancel") & filters.private)
async def cancel_processing(client, message: Message):
    cancelled_users[message.from_user.id] = True
    await message.reply("❌ Traitement annulé.")

@app.on_message(filters.command("replace_rule") & filters.private)
async def replace_rule(client, message: Message):
    rule = message.text.split(" ", 2)[1:]
    if len(rule) == 2:
        search, replace = rule
        replace_rules.setdefault(message.from_user.id, []).append((search, replace))
        await message.reply(f"✅ Règle de remplacement ajoutée : {search} → {replace}")
    else:
        await message.reply("❌ Format incorrect. Utilise : /replace_rule <mot_a_remplacer> <remplacement>.")

@app.on_message(filters.command("view_rules") & filters.private)
async def view_rules(client, message: Message):
    rules = replace_rules.get(message.from_user.id, [])
    if rules:
        rules_list = "\n".join([f"{rule[0]} → {rule[1]}" for rule in rules])
        await message.reply(f"📝 Règles de remplacement :\n{rules_list}")
    else:
        await message.reply("❌ Aucune règle de remplacement définie.")

@app.on_message(filters.command("delete_rule") & filters.private)
async def delete_rule(client, message: Message):
    rule = message.text.split(" ", 2)[1:]
    if len(rule) == 2:
        search, replace = rule
        rules = replace_rules.get(message.from_user.id, [])
        replace_rules[message.from_user.id] = [(s, r) for s, r in rules if not (s == search and r == replace)]
        await message.reply(f"✅ Règle de remplacement supprimée : {search} → {replace}")
    else:
        await message.reply("❌ Format incorrect. Utilise : /delete_rule <mot_a_supprimer> <remplacement>.")

# -- PROCESSUS PRINCIPAL --

# Processus principal de traitement du fichier
async def process_file(client, command_message, file_message, counter, total_files, progress_message, semaphore):
    user_id = command_message.from_user.id
    async with semaphore:
        while paused_users.get(user_id, False) or cancelled_users.get(user_id, False):
            await asyncio.sleep(1)

        # Télécharger le fichier
        file_path = await file_message.download(file_name=f"downloads/file_{random.randint(1, 99999)}")
        thumb_list = user_thumbnails.get(user_id, [])
        thumb_path = thumb_list[(counter - 1) % len(thumb_list)] if thumb_list else None

        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)

        # Remplacer les mots dans le nom
        for search, replace in replace_rules.get(user_id, []):
            name = name.replace(search, replace)

        new_name = f"downloads/{name}{ext}"
        os.rename(file_path, new_name)

        # Envoi d'un nouveau message de progression si nécessaire
        progress_message = await command_message.reply(f"📦 Traitement du fichier {counter}/{total_files}... ({int(counter / total_files * 100)}%)")

        # Process (ajouter la miniature, etc)
        await asyncio.sleep(1)  # Simuler le traitement

        # Mettre à jour le message de progression à chaque fichier traité
        await progress_message.edit(f"⏳ {counter}/{total_files} fichiers traités...")

# -- LANCER LE BOT --

app.run()
