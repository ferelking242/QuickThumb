import os
import shutil
import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

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
send_location = {}         # user_id: "me" or "channel"
user_channels = {}         # user_id: channel_id

# -- SETUP DOSSIER --
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# -- COMMANDES BOT --

@app.on_message(filters.command("set_send_location") & filters.private)
async def set_send_location(client, message: Message):
    # Create the buttons to select where the files should be sent
    buttons = [
        [InlineKeyboardButton("Me", callback_data="send_me")],
        [InlineKeyboardButton("Channel", callback_data="send_channel")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply("Choisis où envoyer les fichiers :", reply_markup=reply_markup)

@app.on_callback_query()
async def callback_set_send_location(client, callback_query):
    user_id = callback_query.from_user.id
    action = callback_query.data

    if action == "send_me":
        send_location[user_id] = "me"
        await callback_query.answer("Les fichiers seront envoyés à toi.")
    elif action == "send_channel":
        send_location[user_id] = "channel"
        await callback_query.answer("Les fichiers seront envoyés au canal.")
    else:
        await callback_query.answer("Option invalide.")

@app.on_message(filters.command("set_channel") & filters.private)
async def set_channel(client, message: Message):
    # On vérifie que l'utilisateur donne un canal valide
    if len(message.text.split()) > 1:
        channel_id = message.text.split()[1]  # on récupère l'ID du canal
        user_id = message.from_user.id
        user_channels[user_id] = channel_id
        await message.reply(f"✅ Canal défini pour l'envoi des fichiers : {channel_id}")
    else:
        await message.reply("❌ Tu dois spécifier l'ID du canal après la commande. Exemple : /set_channel @MonCanal")

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
    seq_name = message.text.split(" ", 1)[1] if len(message.text.split()) > 1 else "FK"
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
    user_id = message.from_user.id
    seqs = user_seq_files.get(user_id, {})

    if seqs:
        buttons = [
            [InlineKeyboardButton(seq_name, callback_data=f"exec_{seq_name}")]
            for seq_name in seqs.keys()
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply("Choisis la séquence à exécuter :", reply_markup=reply_markup)
    else:
        await message.reply("❌ Aucune séquence trouvée.")

@app.on_callback_query()
async def callback_exec_seq(client, callback_query):
    # Vérifier que le callback_data contient le bon format
    if callback_query.data.startswith("exec_"):
        seq_name = callback_query.data.split("_")[1]
        user_id = callback_query.from_user.id
        seq_files = user_seq_files.get(user_id, {}).get(seq_name, [])

        if seq_files:
            progress_message = await callback_query.message.reply(f"📦 Début du traitement de la séquence '{seq_name}'...")

            for idx, file_message in enumerate(seq_files):
                # Envoie un nouveau message pour chaque fichier
                progress_msg = await callback_query.message.reply(f"📦 Traitement du fichier {idx + 1}/{len(seq_files)}...")

                await process_file(client, callback_query.message, file_message, idx + 1, len(seq_files), progress_msg, asyncio.Semaphore(MAX_CONCURRENT_TASKS))

            await progress_message.edit(f"✅ Séquence '{seq_name}' exécutée avec succès.")
        else:
            await callback_query.message.reply(f"❌ Aucune séquence trouvée avec le nom '{seq_name}'.")
    else:
        await callback_query.message.reply("❌ Option invalide.")

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

async def process_file(client, command_message, file_message, counter, total_files, progress_message, semaphore):
    user_id = command_message.from_user.id
    async with semaphore:
        while paused_users.get(user_id, False) or cancelled_users.get(user_id, False):
            await asyncio.sleep(1)

        # Télécharger le fichier
        try:
            file_path = await file_message.download(file_name=f"downloads/file_{random.randint(1, 99999)}")
            print(f"[DEBUG] Fichier téléchargé : {file_path}")
            new_name = f"downloads/file_{random.randint(1000,9999)}.jpg"
            shutil.move(file_path, new_name)

            # Appliquer les règles de remplacement
            if user_id in replace_rules:
                with open(new_name, "r") as file:
                    content = file.read()
                    for search, replace in replace_rules[user_id]:
                        content = content.replace(search, replace)
                with open(new_name, "w") as file:
                    file.write(content)

            # Envoi du fichier
            if user_id in send_location:
                location = send_location[user_id]
                print(f"[DEBUG] Envoi du fichier à {location}...")

                if location == "me":
                    await client.send_document(user_id, new_name, caption=f"Fichier modifié avec succès.")
                elif location == "channel":
                    channel_id = user_channels.get(user_id)
                    if channel_id:
                        await client.send_document(channel_id, new_name, caption="Fichier modifié avec succès.")
                    else:
                        await client.send_message(user_id, "❌ Canal non défini. Utilise /set_channel pour définir un canal.")

            # Supprimer le fichier après envoi
            os.remove(new_name)

            # Mettre à jour la progression
            await progress_message.edit(f"📦 Traitement du fichier {counter}/{total_files} terminé.")

        except Exception as e:
            print(f"[ERROR] Erreur pendant le traitement du fichier : {str(e)}")

# -- LANCER LE BOT --

app.run()
