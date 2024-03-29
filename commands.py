import asyncio

import discord
from discord import app_commands, Embed
from discord.ext import commands
import yt_dlp as youtube_dl

from config import ydl_opts, FFMPEG_OPTIONS
from logger import get_logger
import utils

logger = get_logger()

queuelist = {}
stop_signal = {}


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="join", description="Se conecta ao seu canal de voz")
    async def join(self, ctx):
        user_voice = ctx.user.voice
        if not user_voice:
            await ctx.response.send_message(
                embed=Embed(color=discord.Color.dark_purple(), description="Você não está em um canal de voz!"),
                ephemeral=True)
            return

        channel = user_voice.channel
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            try:
                await channel.connect()
            except Exception as e:
                print(e)

        await ctx.response.send_message("Conectado", ephemeral=True)

    @app_commands.command(name="play", description="Reproduz a música selecionada")
    @app_commands.describe(musica="Escreva o nome da música")
    async def play(self, ctx: commands.Context, musica: str):
        logger.info(f"Command: /play {musica} by {ctx.user.name}")

        if musica.startswith("http") and (
                not musica.startswith("https://www.youtube.com") and not musica.startswith("https://youtu.be")):
            await ctx.response.send_message(embed=Embed(color=discord.Color.dark_purple(),
                                                        description="Eu só aceito áudios do youtube, por favor insira "
                                                                    "um link válido"),
                                            ephemeral=True)
            return

        if ctx.guild not in queuelist:
            queuelist[ctx.guild] = []

        voice = await utils.connect_to_channel(ctx, self.bot)

        if not voice:
            return

        await ctx.response.defer(thinking=True)

        if musica.startswith("http") or musica.startswith("www"):
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(musica, download=False)

                if "entries" in info:
                    for entry in info["entries"][1:]:
                        queuelist[ctx.guild].append({"title": entry["title"], "url": entry["url"]})

                    title = info["entries"][0]["title"]
                    url = info["entries"][0]["url"]
                else:
                    title = info["title"]
                    url = info["url"]
        else:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{musica}", download=False)["entries"][0]

                title = info["title"]
                url = info["url"]

        if url.startswith("https://www.youtube.com"):
            url = utils.get_youtube_download_link(url)

        if voice.is_playing():
            queuelist[ctx.guild].append({"title": title, "url": url})
            embed = Embed(color=discord.Color.dark_purple(), description=f"Adicionado a fila: ** {title} **")
            embed.set_author(name=ctx.user.name, icon_url=ctx.user.avatar)

            await ctx.followup.send(embed=embed)
        else:
            voice.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS),
                       after=lambda e: asyncio.run(check_queue(ctx, self.bot)))

            embed = Embed(color=discord.Color.dark_purple(),
                          description=f"Tocando ** {title} ** no canal dos folgados :musical_note:")
            embed.set_author(name=ctx.user.name, icon_url=ctx.user.avatar)

            await ctx.followup.send(embed=embed)

    @app_commands.command(name="skip", description="Pula pra próxima música")
    async def skip(self, ctx: commands.Context):
        if ctx.guild not in queuelist or len(queuelist[ctx.guild]) == 0:
            await ctx.followup.send(embed=Embed(color=discord.Color.dark_purple(), description="A fila está vazia"))
            return

        await ctx.response.defer(thinking=True, ephemeral=False)

        check_queue_return = await check_queue(ctx, self.bot, True, True)
        check_queue_return.set_author(name=ctx.user.name, icon_url=ctx.user.avatar)

        await ctx.followup.send(embed=check_queue_return)

    @app_commands.command(name="pause", description="Pausa a reprodução")
    async def pause(self, ctx: commands.Context):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await ctx.response.send_message(
                embed=Embed(color=discord.Color.dark_purple(), description="Reprodução pausada"))
            return

        await ctx.response.send_message(
            embed=Embed(color=discord.Color.dark_purple(),
                        description="O folgado não está reproduzindo nada no momento"))

    @app_commands.command(name="stop", description="Para a reprodução")
    async def stop(self, ctx: commands.Context):
        global queuelist, stop_signal

        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client:
            if voice_client.is_playing():
                if not isinstance(stop_signal, dict):
                    stop_signal = {}

                stop_signal[ctx.guild] = True

            if ctx.guild in queuelist:
                del queuelist[ctx.guild]

            if voice_client.is_connected():
                await voice_client.disconnect()

            await ctx.response.send_message(
                embed=Embed(color=discord.Color.dark_purple(), description="Desconectado do canal de voz"))
            return

        await ctx.response.send_message(
            embed=Embed(color=discord.Color.dark_purple(),
                        description="O folgado não está reproduzindo nada no momento"))

    @app_commands.command(name="resume", description="Continua a reprodução")
    async def resume(self, ctx: commands.Context):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and not voice_client.is_playing():
            voice_client.resume()
            await ctx.response.send_message(
                embed=Embed(color=discord.Color.dark_purple(), description="Reprodução retomada"))
            return

        await ctx.response.send_message(
            embed=Embed(color=discord.Color.dark_purple(),
                        description="O folgado não está reproduzindo áudio no momento"))

    @app_commands.command(name="show_queue", description="Mostra a fila de músicas")
    async def show_queue(self, ctx: commands.Context):
        embed = Embed(title="Fila", color=discord.Color.dark_purple())
        queue_is_empty_embed = Embed(color=discord.Color.dark_purple(), description="A fila está vazia")

        if ctx.guild not in queuelist:
            await ctx.response.send_message(embed=queue_is_empty_embed)
            return

        queue = queuelist[ctx.guild]

        num_songs_to_display = min(len(queue), 10)
        for music in queue[:num_songs_to_display]:
            embed.add_field(name="\u200b", value=music["title"])

        if len(embed.fields) == 0:
            await ctx.response.send_message(embed=queue_is_empty_embed)
            return

        if len(queue) > num_songs_to_display:
            embed.set_footer(text=f"+{len(queue) - num_songs_to_display} músicas na fila")

        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="clear_queue", description="Limpa a fila")
    async def clear_queue(self, ctx: commands.Context):
        global queuelist

        if ctx.guild in queuelist:
            del queuelist[ctx.guild]

        await ctx.response.send_message(embed=Embed(color=discord.Color.dark_purple(), description="Fila limpa"))

    async def cog_app_command_error(self, ctx: commands.Context, error: Exception) -> None:
        logger.error(error)

        try:
            await ctx.response.defer()
        except Exception:
            pass

        if isinstance(error, app_commands.CommandInvokeError):
            if isinstance(error.original, youtube_dl.utils.DownloadError):
                await ctx.followup.send(embed=Embed(color=discord.Color.dark_purple(),
                                                    description="Não foi possível encontrar o conteúdo, por favor verifique se você não inseriu uma url inválida"))
                return

            await ctx.followup.send(embed=Embed(color=discord.Color.dark_purple(), title="Erro",
                                                description=f"{error.original}\n\n Por favor reporte para shauuu\_"))
        else:
            await ctx.followup.send(embed=Embed(color=discord.Color.dark_purple(), title="Erro",
                                                description=f"{error.original}\n\n Por favor reporte para shauuu\_"))


"""
Checks the current queue and update the environment accordingly 

:param ctx: Command context
:type ctx: commands.Context

:param bot: Bot instance
:type bot: commands.Bot

:param asynchronously: Solve the use of await on common and lambda functions, being set to False on lambda
:type asynchronously: bool

:param return_answer: Returns the answer instead of sending it so that the function that called it can send it on his own Context
:type return_answer: bool

:returns: The answer or a boolean value saying if a new music started to play or not
:rtype: str or bool
"""
async def check_queue(ctx: commands.Context, bot: commands.Bot, asynchronously=False, return_answer=False):
    global stop_signal

    if isinstance(stop_signal, dict) and ctx.guild in stop_signal:
        del stop_signal[ctx.guild]
        return

    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_client:
        return

    if ctx.guild in queuelist and len(queuelist[ctx.guild]) > 0:
        queue = queuelist[ctx.guild]
        if voice_client.is_playing():
            stop_signal = True
            voice_client.stop()

        url = queue[0]["url"]
        if url.startswith("https://www.youtube.com"):
            url = utils.get_youtube_download_link(url)
        else:
            await asyncio.sleep(3)

        title = queue[0]['title']
        voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS),
                          after=lambda e: asyncio.run(check_queue(ctx, bot)))
        embed_temp = Embed(color=discord.Color.dark_purple(),
                           description=f"Tocando ** {title} ** no canal dos folgados :musical_note:")
        queue.pop(0)

        if asynchronously:
            if return_answer:
                return embed_temp

            await ctx.channel.send(embed=embed_temp)

            return True

        coro_1 = ctx.channel.send(embed=embed_temp)

        if return_answer:
            return embed_temp

        await utils.execute_coroutine_threadsafe(coro_1, bot)

        return True

    embed = Embed(color=discord.Color.dark_purple(),
                  description="Nenhuma música na fila, desconectado do canal de voz")

    if asynchronously:
        await voice_client.disconnect()

        if return_answer:
            return embed

        await ctx.channel.send(embed=embed)

        return False

    coro_1 = voice_client.disconnect()
    coro_2 = ctx.channel.send(embed=embed)

    await utils.execute_coroutine_threadsafe(coro_1, bot)

    if return_answer:
        return embed

    await utils.execute_coroutine_threadsafe(coro_2, bot)

    return False


async def setup(bot):
    await bot.add_cog(Commands(bot))
