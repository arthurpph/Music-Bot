import asyncio

import discord
from discord import Embed
from discord.ext import commands
import yt_dlp as youtube_dl

from config import ydl_opts
import utils


async def connect_to_channel(ctx, bot):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice:
        user_voice = ctx.user.voice
        if not user_voice:
            await ctx.response.send_message(
                embed=Embed(color=discord.Color.dark_purple(), description="Você não está em um canal de voz!"),
                ephemeral=True)
            return

        return await user_voice.channel.connect()

    return voice


def get_youtube_download_link(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info["url"]


async def execute_coroutine_threadsafe(coro, bot):
    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    return fut.result()

async def check_queue(ctx: commands.Context, asynchronously: bool, return_answer=None):
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
                              after=lambda e: asyncio.run(check_queue(ctx, False)))
            embed_temp = Embed(color=discord.Color.dark_purple(),
                               description=f"Tocando ** {title} ** no canal dos folgados :musical_note:")
            queuelist.pop(0)

            # solve the use of await on common and lambda functions
            if asynchronously:
                await bot.change_presence(
                    activity=discord.Activity(type=discord.ActivityType.listening, name=title))

                if return_answer:
                    return embed_temp
                else:
                    await ctx.channel.send(embed=embed_temp)

                return True

            coro_1 = bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=title))
            coro_2 = ctx.channel.send(embed=embed_temp)

            await utils.execute_coroutine_threadsafe(coro_1, bot)

            if return_answer:
                return embed_temp
            else:
                await utils.execute_coroutine_threadsafe(coro_2, bot)

            return True

    embed = Embed(color=discord.Color.dark_purple(),
                  description="Nenhuma música na fila, desconectado do canal de voz")

    if asynchronously:
        await bot.change_presence(activity=None)
        await voice_client.disconnect()

        if return_answer:
            return embed
        else:
            await ctx.channel.send(embed=embed)

        return False

    coro_1 = bot.change_presence(activity=None)
    coro_2 = voice_client.disconnect()
    coro_3 = ctx.channel.send(embed=embed)

    await utils.execute_coroutine_threadsafe(coro_1, bot)
    await utils.execute_coroutine_threadsafe(coro_2, bot)

    if return_answer:
        return embed
    else:
        await utils.execute_coroutine_threadsafe(coro_3, bot)

    return False

