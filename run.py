#!/usr/bin/env python3
import discord, json, lib
from bot import WriterBot
from discord.ext import commands
from pprint import pprint

# As of 1.5 we now need to specify the intent to get the members list, otherwise we can't access it.
intents = discord.Intents.default()
intents.members = True

# Load the settings for initial setup
config = lib.get('./settings.json')

# Load the Bot object
status = discord.Game( 'Booting up...' )
bot = WriterBot(command_prefix=WriterBot.load_prefix, activity=status, intents=intents)

# Load all commands
bot.load_commands()

# Start the bot
bot.run(config.token)