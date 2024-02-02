import asyncio

import discord
from discord import Embed
from discord.ext import commands
import yt_dlp as youtube_dl

from config import ydl_opts


"""
Connects to the voice channel that the user who executed the command is connected to

:param ctx: Command context
:type ctx: commands.Context

:param bot: Bot instance
:type bot: commands.Bot

:returns: The voice channel object that the bot connected or None if the user isn't connected to a voice channel
:rtype: VoiceProtocol or None
"""
async def connect_to_channel(ctx: commands.Context, bot: commands.Bot):
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


"""
Get the download url of a youtube video

:param url: Url of the youtube video
:type url: str

:returns: The download url of the youtube video provided
:rtype: str
"""
def get_youtube_download_link(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info["url"]


"""
Executes a asynchronously function on a different thread than the main thread (threadsafe)

:param coro: Function to be executed asynchronously
:type coro: Union[Coroutine[Any, Any, Any], Awaitable[Any]] 

:param bot: Bot instance
:type bot: commands.Bot

:returns The return of the asynchronous function
"""
async def execute_coroutine_threadsafe(coro, bot):
    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    return fut.result()


