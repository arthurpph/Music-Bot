import asyncio

import discord
from discord import app_commands, Embed
from discord.ext import commands
import yt_dlp as youtube_dl

from config import ydl_opts, FFMPEG_OPTIONS
import utils


queuelist = []
stop_signal = False


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
        if musica.startswith("http") and (not musica.startswith("https://www.youtube.com") and not musica.startswith("https://youtu.be")):
            await ctx.response.send_message(embed=Embed(color=discord.Color.dark_purple(),
                                                        description="Eu só aceito áudios do youtube, por favor insira um link válido"),
                                            ephemeral=True)
            return

        voice = await utils.connect_to_channel(ctx, self.bot)

        if not voice:
            return

        await ctx.response.defer(thinking=True)

        if musica.startswith("http") or musica.startswith("www"):
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(musica, download=False)

                if "entries" in info:
                    for entry in info["entries"][1:]:
                        queuelist.append({"title": entry["title"], "url": entry["url"]})

                    title = info["entries"][0]["title"]
                    url = info["entries"][0]["url"]
                else:
                    title = info["title"]
                    url = info["url"]
        else:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{musica}", download=False)["entries"][0]

                if "entries" in info:
                    for entry in info["entries"][1:]:
                        queuelist.append(entry["url"])

                    title = info["entries"][0]["title"]
                    url = info["entries"][0]["url"]
                else:
                    title = info["title"]
                    url = info["url"]

        if url.startswith("https://www.youtube.com"):
            url = utils.get_youtube_download_link(url)

        if voice.is_playing():
            queuelist.append({"title": title, "url": url})
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
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=title))

    @app_commands.command(name="skip", description="Pula pra próxima música")
    async def skip(self, ctx: commands.Context):
        if len(queuelist) == 0:
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

        queuelist = []
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            stop_signal = True

            voice_client.stop()
            await voice_client.disconnect()

            await ctx.response.send_message(
                embed=Embed(color=discord.Color.dark_purple(), description="Desconectado do canal de voz"))
            await self.bot.change_presence(activity=None)
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

        num_songs_to_display = min(len(queuelist), 10)
        for music in queuelist[:num_songs_to_display]:
            embed.add_field(name="\u200b", value=music["title"])

        if len(embed.fields) == 0:
            await ctx.response.send_message(
                embed=Embed(color=discord.Color.dark_purple(), description="A fila está vazia"))
            return

        if len(queuelist) > num_songs_to_display:
            embed.set_footer(text=f"+{len(queuelist) - num_songs_to_display} músicas na fila")

        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="clear_queue", description="Limpa a fila")
    async def clear_queue(self, ctx: commands.Context):
        global queuelist

        queuelist = []

        await ctx.response.send_message(embed=Embed(color=discord.Color.dark_purple(), description="Fila limpa"))


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

    if stop_signal:
        stop_signal = False
        return

    voice_client = await utils.connect_to_channel(ctx, bot)

    if not voice_client:
        return

    if len(queuelist) > 0:
        if queuelist[0] is not None:
            if voice_client.is_playing():
                stop_signal = True
                voice_client.stop()

            url = queuelist[0]["url"]
            if url.startswith("https://www.youtube.com"):
                url = utils.get_youtube_download_link(url)
            else:
                await asyncio.sleep(3)

            title = queuelist[0]['title']
            voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS),
                              after=lambda e: asyncio.run(check_queue(ctx, bot)))
            embed_temp = Embed(color=discord.Color.dark_purple(),
                               description=f"Tocando ** {title} ** no canal dos folgados :musical_note:")
            queuelist.pop(0)

            if asynchronously:
                await bot.change_presence(
                    activity=discord.Activity(type=discord.ActivityType.listening, name=title))

                if return_answer:
                    return embed_temp

                await ctx.channel.send(embed=embed_temp)

                return True

            coro_1 = bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=title))
            coro_2 = ctx.channel.send(embed=embed_temp)

            await utils.execute_coroutine_threadsafe(coro_1, bot)

            if return_answer:
                return embed_temp

            await utils.execute_coroutine_threadsafe(coro_2, bot)

            return True

    embed = Embed(color=discord.Color.dark_purple(),
                  description="Nenhuma música na fila, desconectado do canal de voz")

    if asynchronously:
        await bot.change_presence(activity=None)
        await voice_client.disconnect()

        if return_answer:
            return embed

        await ctx.channel.send(embed=embed)

        return False

    coro_1 = bot.change_presence(activity=None)
    coro_2 = voice_client.disconnect()
    coro_3 = ctx.channel.send(embed=embed)

    await utils.execute_coroutine_threadsafe(coro_1, bot)
    await utils.execute_coroutine_threadsafe(coro_2, bot)

    if return_answer:
        return embed

    await utils.execute_coroutine_threadsafe(coro_3, bot)

    return False


async def setup(bot):
    await bot.add_cog(Commands(bot))
