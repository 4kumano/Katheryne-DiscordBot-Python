import os
import discord
import json
import platform
import random
import sys

from discord.ext import tasks
from discord.ext.commands import Bot
from utils import default
from utils.data import Bot, HelpFormat

config = default.config()
#print("Logging in...")

# The code in this even is executed when the bot is ready

bot = Bot(
    command_prefix=config["prefix"], prefix=config["prefix"],
    owner_ids=config["owners"], command_attrs=dict(hidden=True), help_command=HelpFormat(),
    allowed_mentions=discord.AllowedMentions(roles=False, users=True, everyone=False),
    intents=discord.Intents(  # kwargs found at https://discordpy.readthedocs.io/en/latest/api.html?highlight=intents#discord.Intents
        guilds=True, members=True, messages=True, reactions=True, presences=True
    )
)
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print(f"Discord.py API version: {discord.__version__}")
    print(f"Python version: {platform.python_version()}")
    print(f"Running on: {platform.system()} {platform.release()} ({os.name})")
    print("-------------------")
    #status_task.start()


if __name__ == "__main__":
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            name = file[:-3]
            try:
                bot.load_extension(f"cogs.{name}")
                print(f"Loaded extension '{name}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                print(f"Failed to load extension {name}\n{exception}")


try:
    bot.run(config["token"])
except Exception as e:
    print(f"Error when logging in: {e}")
