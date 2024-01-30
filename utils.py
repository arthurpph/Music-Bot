import asyncio

import discord
from discord import Embed
import yt_dlp as youtube_dl

ydl_opts = {
    "format": "bestaudio/best",
    "extract_flat": True,
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }
    ]
}


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
