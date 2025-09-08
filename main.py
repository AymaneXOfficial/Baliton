import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import random  # ✅ Added for random.choice()

# Load token from .env file
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# Setup logging
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Bot ready event
@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

# Handle messages
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Ketchup response
    if "ketchup" in message.content.lower():
        await message.channel.send(f"{message.author.mention} - SAUCCCE!!!")

    if "your wish?" in message.content.lower():
        await message.channel.send("I want to rule the sauce kindgom, and I will consume everyone who stand in my way!")
    if "why???" in message.content.lower():
        await message.channel.send("Because... It's late, imma go back to sleep...")

    # Random hello response
    if "hello" in message.content.lower():
        responses = [
            "Hey there! 👋",
            "Hello friend 😊",
            "What's up?",
            "Yo! How are you?",
            "Hi hi hi! 🚀"
        ]
        reply = random.choice(responses)
        await message.channel.send(reply)

    # ✅ Needed to keep commands working
    await bot.process_commands(message)

# Run bot
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
