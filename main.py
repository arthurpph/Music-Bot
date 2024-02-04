import asyncio
import os
from typing import Final

import nest_asyncio
import discord
from discord.ext import commands

from dotenv import load_dotenv

from logger import load_logger

load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

intents: discord.Intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

extensions = ["commands.py"]

load_logger()


@bot.event
async def on_ready():
    print(f'{bot.user} está online')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comando(s)")
    except Exception as e:
        print(f"Exceção ocorreu durante a inicialização do bot: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        if before.channel and not after.channel:
            voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
            if voice_client:
                voice_client.stop()


async def load_extensions():
    for filename in os.listdir("./"):
        if filename in extensions:
            await bot.load_extension(filename[:-3])


async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


nest_asyncio.apply()
asyncio.run(main())
