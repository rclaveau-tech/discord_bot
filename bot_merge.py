import os
import shutil
import time

import pydub  # pip install pydub==0.25.1

import discord
from discord.sinks import MP3Sink

import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)

log_file_path = 'bot_debug.log'
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

bot = discord.Bot()

discord.opus.load_opus("libopus.so")
if not discord.opus.is_loaded():
    raise RunTimeError('Opus failed to load')

recording_start_time: str
recording_stop_time: str


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")

TEMP_RECORDINGS_DIR = "temp_recordings"

if not os.path.exists(TEMP_RECORDINGS_DIR):
    os.makedirs(TEMP_RECORDINGS_DIR)

FINAL_RECORDINGS_DIR = os.getenv('FINAL_RECORDINGS_DIR')

if not os.path.exists(FINAL_RECORDINGS_DIR):
    os.makedirs(FINAL_RECORDINGS_DIR)

DOWNLOAD_URL = os.getenv('DOWNLOAD_URL')

async def finished_callback(sink: MP3Sink, channel: discord.TextChannel):
    await channel.send("Je prépare les fichiers de l'enregistrement")
    mention_strs = []
    audio_segs: list[pydub.AudioSegment] = []
    files = []

    longest = pydub.AudioSegment.empty()

    for user_id, audio in sink.audio_data.items():
        mention_strs.append(f"<@{user_id}>")

        seg = pydub.AudioSegment.from_file(audio.file, format="mp3")

        # Determine the longest audio segment
        if len(seg) > len(longest):
            audio_segs.append(longest)
            longest = seg
        else:
            audio_segs.append(seg)

        audio.file.seek(0)
        individual_filename = f"{recording_start_time}_{recording_stop_time}_{user_id}.mp3"
        tmp_filename = os.path.join(
            TEMP_RECORDINGS_DIR, individual_filename
        )
        with open(tmp_filename, "wb") as f:
            f.write(audio.file.read())
        files.append((user_id, individual_filename))

    for seg in audio_segs:
        longest = longest.overlay(seg)

    combined_filename = f"{recording_start_time}_{recording_stop_time}_enregistrement-complet.mp3"
    tmp_combined_filename = os.path.join(
        TEMP_RECORDINGS_DIR, combined_filename
    )
    longest.export(tmp_combined_filename, format="mp3")
    files.append(("complet", combined_filename))

    message_parts = [f"Terminé! Enregistrement audio de: {', '.join(mention_strs)}."]

    for identifier, path in files:
        shutil.move(os.path.join(TEMP_RECORDINGS_DIR, path), os.path.join(FINAL_RECORDINGS_DIR, path))
        if identifier == "complet":
            message_parts.append(f"Enregistrement combiné : {DOWNLOAD_URL}{path}")
        else: message_parts.append(f"<@{identifier}> : {DOWNLOAD_URL}{path}")

    await channel.send("\n".join(message_parts))


@bot.command()
async def rejoindre(ctx: discord.ApplicationContext):
    """Rejoindre le salon vocal!"""
    voice = ctx.author.voice

    if not voice:
        return await ctx.respond("Tu n'es pas dans un salon vocal actuellement")

    await voice.channel.connect()

    await ctx.respond("Je suis arrivé dans le salon!")
    return None


@bot.command()
async def enregistrer(ctx: discord.ApplicationContext):
    """Enregistrer le salon vocal!"""
    voice = ctx.author.voice

    if not voice:
        return await ctx.respond("Tu n'es pas dans un salon vocal actuellement")

    vc: discord.VoiceClient = ctx.voice_client

    if not vc:
        return await ctx.respond(
            "Je ne suis pas dans un salon. Utiliser `/rejoindre` pour me faire venir!"
        )

    vc.start_recording(
        MP3Sink(),
        finished_callback,
        ctx.channel,
        sync_start=True,
    )

    global recording_start_time
    recording_start_time = time.strftime("%d%m%y-%H%M%S")

    await ctx.respond(f"L'enregistrement a démarré à {recording_start_time} !")
    return None


@bot.command()
async def stop(ctx: discord.ApplicationContext):
    """Stopper l'enregistrement"""
    vc: discord.VoiceClient = ctx.voice_client

    if not vc:
        return await ctx.respond("Il n'y a pas d'enregistrement en cours")

    await ctx.respond("J'arrête l'enregistrement ...")

    vc.stop_recording()

    global recording_stop_time
    recording_stop_time = time.strftime("%d%m%y-%H%M%S")

    await ctx.respond(f"L'enregistrement est arrêté à {recording_stop_time} !")
    return None


@bot.command()
async def quitter(ctx: discord.ApplicationContext):
    """Quitter le salon vocal!"""
    vc: discord.VoiceClient = ctx.voice_client

    if not vc:
        return await ctx.respond("Je ne suis pas dans un salon vocal")

    await vc.disconnect()

    await ctx.respond("Parti!")
    return None


bot.run(os.getenv('BOT_TOKEN'))
