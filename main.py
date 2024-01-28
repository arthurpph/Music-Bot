import asyncio
import os
from typing import Final

import nest_asyncio
import discord
from discord import app_commands, Embed
from discord.ext import commands
import yt_dlp as youtube_dl

from dotenv import load_dotenv

load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

intents: discord.Intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

queuelist = []
musics_to_delete = []


@bot.event
async def on_ready():
    print(f'{bot.user} está online')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comando(s)")
    except Exception as e:
        print(f"Exceção ocorreu durante a inicialização do bot: {e}")


@bot.tree.command(name="join", description="Se conecta ao seu canal de voz")
async def join(ctx):
    user_voice = ctx.user.voice
    if not user_voice:
        await ctx.response.send_message(
            embed=Embed(color=discord.Color.dark_purple(), description="Você não está em um canal de voz!"),
            ephemeral=True)
        return

    channel = user_voice.channel
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        try:
            await channel.connect()
        except Exception as e:
            print(e)

    await ctx.response.send_message("Conectado", ephemeral=True)


@bot.tree.command(name="play", description="Reproduz a música selecionada")
@app_commands.describe(musica="Escreva o nome da música")
async def play(ctx: commands.Context, musica: str):
    ydl_opts = {}
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice:
        user_voice = ctx.user.voice
        if not user_voice:
            await ctx.response.send_message(
                embed=Embed(color=discord.Color.dark_purple(), description="Você não está em um canal de voz!"),
                ephemeral=True)
            return

        try:
            voice = await user_voice.channel.connect()
        except Exception as e:
            print(e)

    await ctx.response.send_message(embed=Embed(color=discord.Color.dark_purple(), description="Baixando música..."),
                                    ephemeral=True)

    if musica.startswith("http") or musica.startswith("www"):
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(musica, download=False)
            title = info["title"]
            url = musica
    else:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{musica}", download=False)["entries"][0]
            title = info["title"]
            url = info["webpage_url"]

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{title}",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }
        ]
    }

    def download(url):
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, download, url)

    if voice.is_playing():
        queuelist.append(title)
        embed = Embed(color=discord.Color.dark_purple(), description=f"Adicionado a fila: ** {title} **")
        embed.set_author(name=ctx.user.name, icon_url=ctx.user.avatar)
        await ctx.channel.send(embed=embed)
    else:
        voice.play(discord.FFmpegPCMAudio(f"{title}.mp3"), after=lambda e: asyncio.run(check_queue()))
        embed = Embed(color=discord.Color.dark_purple(),
                      description=f"Tocando ** {title} ** no canal dos folgados :musical_note:")
        embed.set_author(name=ctx.user.name, icon_url=ctx.user.avatar)
        await ctx.channel.send(embed=embed)
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=title))
        musics_to_delete.append(title)

    async def check_queue():
        for music in musics_to_delete:
            os.remove(f"{music}.mp3")
        musics_to_delete.clear()

        if len(queuelist) > 0:
            if queuelist[0] is not None:
                voice.play(discord.FFmpegPCMAudio(f"{queuelist[0]}.mp3"), after=lambda e: asyncio.run(check_queue()))
                embed_temp = Embed(color=discord.Color.dark_purple(),
                                   description=f"Tocando ** {queuelist[0]} ** no canal dos folgados :musical_note:")

                coro = bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=title))
                fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
                fut.result()

                coro_2 = ctx.channel.send(embed=embed_temp)
                fut_2 = asyncio.run_coroutine_threadsafe(coro_2, bot.loop)
                fut_2.result()

                queuelist.pop(0)
                musics_to_delete.append(queuelist[0])
        else:
            coro = ctx.channel.send(embed=Embed(color=discord.Color.dark_purple(),
                                                description="Nenhuma música na fila, desconectado do canal de voz"))
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            fut.result()

            coro_2 = bot.change_presence(activity=None)
            fut_2 = asyncio.run_coroutine_threadsafe(coro_2, bot.loop)
            fut_2.result()


@bot.tree.command(name="pause", description="Pausa a reprodução")
async def pause(ctx: commands.Context):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.response.send_message(
            embed=Embed(color=discord.Color.dark_purple(), description="Reprodução pausada"))
        return

    await ctx.response.send_message(
        embed=Embed(color=discord.Color.dark_purple(), description="O folgado não está reproduzindo nada no momento"))


@bot.tree.command(name="stop", description="Para a reprodução")
async def stop(ctx: commands.Context):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await voice_client.disconnect()
        await ctx.response.send_message(
            embed=Embed(color=discord.Color.dark_purple(), description="Desconectado do canal de voz"))
        return

    await ctx.response.send_message(
        embed=Embed(color=discord.Color.dark_purple(), description="O folgado não está reproduzindo nada no momento"))


@bot.tree.command(name="resume", description="Continua a reprodução")
async def resume(ctx: commands.Context):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and not voice_client.is_playing():
        voice_client.resume()
        await ctx.response.send_message(
            embed=Embed(color=discord.Color.dark_purple(), description="Reprodução retomada"))
        return

    await ctx.response.send_message(
        embed=Embed(color=discord.Color.dark_purple(), description="O folgado não está reproduzindo áudio no momento"))


@bot.tree.command(name="show_queue", description="Mostra a fila de músicas")
async def show_queue(ctx: commands.Context):
    embed = Embed(title="Fila", color=discord.Color.dark_purple())
    for music in queuelist:
        embed.add_field(name=music, value="\u200b")

    if len(embed.fields) == 0:
        await ctx.response.send_message(embed=Embed(color=discord.Color.dark_purple(), description="A fila está vazia"))

    await ctx.response.send_message(embed=embed)


async def main():
    for file in os.listdir(os.getcwd()):
        if file.endswith(".mp3"):
            os.remove(file)

    async with bot:
        await bot.start(TOKEN)


nest_asyncio.apply()
asyncio.run(main())
