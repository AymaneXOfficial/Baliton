import discord
from discord.ext import commands, tasks
import sqlite3
import asyncio
import random
import math
import datetime
from typing import Dict, List, Tuple
import aiohttp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration with proper intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix='-', intents=intents, help_command=None)

# Database setup
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # Users table - UPDATED with server-specific XP
    c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
              planks INTEGER DEFAULT 0, stone INTEGER DEFAULT 0, iron INTEGER DEFAULT 0,
              silver INTEGER DEFAULT 0, gold INTEGER DEFAULT 0, diamonds INTEGER DEFAULT 0,
              emerald INTEGER DEFAULT 0,
              aura INTEGER DEFAULT 0, last_daily TEXT, last_aura_given TEXT, last_weekly TEXT,
                  last_box_used TEXT, last_collection_time TEXT, daily_streak INTEGER DEFAULT 0, 
                  last_daily_date TEXT, commands_used INTEGER DEFAULT 0, drops_caught INTEGER DEFAULT 0, 
                  pass_completed INTEGER DEFAULT 0, total_boxes_opened INTEGER DEFAULT 0, 
                  total_messages INTEGER DEFAULT 0, golden_xp INTEGER DEFAULT 0, 
                  fractional_diamonds REAL DEFAULT 0, last_boost_claim TEXT, bling INTEGER DEFAULT 0,
                  stricks INTEGER DEFAULT 0, last_strick_reset TEXT, last_income_claim TEXT,
                  copper INTEGER DEFAULT 0, magic_keys INTEGER DEFAULT 0, battles_won INTEGER DEFAULT 0,
                  last_income_amount INTEGER DEFAULT 0)''') 
    
    # Server-specific XP table (NEW)
    c.execute('''CREATE TABLE IF NOT EXISTS server_xp
                 (user_id INTEGER, guild_id INTEGER, xp INTEGER DEFAULT 0, 
                  PRIMARY KEY (user_id, guild_id))''')
    
    # City buildings table (replaces house system)
    c.execute('''CREATE TABLE IF NOT EXISTS city_buildings
                 (user_id INTEGER, building_type TEXT, level INTEGER DEFAULT 0, 
                  last_collected TEXT, UNIQUE(user_id, building_type))''')
    
    # Inventory tables
    c.execute('''CREATE TABLE IF NOT EXISTS user_characters
                 (user_id INTEGER, character_name TEXT, rarity TEXT, UNIQUE(user_id, character_name))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_skins
                 (user_id INTEGER, skin_name TEXT, rarity TEXT, UNIQUE(user_id, skin_name))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_artifacts
                 (user_id INTEGER, artifact_name TEXT, rarity TEXT, UNIQUE(user_id, artifact_name))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_badges
                 (user_id INTEGER, badge_name TEXT, UNIQUE(user_id, badge_name))''')
    
    # User boxes table
    c.execute('''CREATE TABLE IF NOT EXISTS user_boxes
                 (user_id INTEGER, box_type TEXT, quantity INTEGER DEFAULT 1, UNIQUE(user_id, box_type))''')
    
    # Server config
    c.execute('''CREATE TABLE IF NOT EXISTS server_config
                 (guild_id INTEGER PRIMARY KEY, art_channel INTEGER, clip_channel INTEGER,
                  spawn_channel INTEGER, boost1_role INTEGER, boost2_role INTEGER, boost3_role INTEGER,
                  master_badge_role INTEGER, ultra_badge_role INTEGER, ultimate_badge_role INTEGER,
                  announcement_channel INTEGER, popup_ping_role INTEGER, sauce_role INTEGER)''')
    
    # Weekly leaderboard
    c.execute('''CREATE TABLE IF NOT EXISTS weekly_xp
                 (user_id INTEGER, week TEXT, xp_gained INTEGER)''')
    
    # Level roles
    c.execute('''CREATE TABLE IF NOT EXISTS level_roles
                 (guild_id INTEGER, level INTEGER, role_id INTEGER)''')
    
    # Pop-up config
    c.execute('''CREATE TABLE IF NOT EXISTS popup_config
                 (guild_id INTEGER PRIMARY KEY, popup_channel INTEGER, 
                  popup_cooldown INTEGER DEFAULT 5, popup_enabled INTEGER DEFAULT 1)''')
    
    # Daily quests
    c.execute('''CREATE TABLE IF NOT EXISTS daily_quests
                 (user_id INTEGER, date TEXT, quest1_progress INTEGER DEFAULT 0, 
                  quest2_progress INTEGER DEFAULT 0, quest3_progress INTEGER DEFAULT 0,
                  quest4_progress INTEGER DEFAULT 0, quest5_progress INTEGER DEFAULT 0,
                  quests_completed INTEGER DEFAULT 0)''')  # UPDATED: Added quest4 and quest5
    
    # Event system
    c.execute('''CREATE TABLE IF NOT EXISTS active_events
                 (guild_id INTEGER, event_type TEXT, multiplier REAL, 
                  end_time TEXT, reward_item TEXT, reward_amount INTEGER)''')
    
    # Mystery box claims
    c.execute('''CREATE TABLE IF NOT EXISTS mystery_claims
                 (user_id INTEGER, level_claimed INTEGER)''')
    
    # Mystery boxes inventory
    c.execute('''CREATE TABLE IF NOT EXISTS user_mystery_boxes
                 (user_id INTEGER, quantity INTEGER DEFAULT 0)''')
    
        # Sauce items table (NEW)
    c.execute('''CREATE TABLE IF NOT EXISTS sauce_items
                 (user_id INTEGER, item_name TEXT, quantity INTEGER DEFAULT 1, 
                  UNIQUE(user_id, item_name))''')
    
    conn.commit()
 # Ensure new columns exist (for older databases where table schema may be missing columns)
    def ensure_column(table, column, definition):
        c.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in c.fetchall()]
        if column not in cols:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                print(f"Added missing column: {table}.{column}")
            except Exception as e:
                print(f"Failed to add column {column} to {table}: {e}")
    
    ensure_column('users', 'copper', 'INTEGER DEFAULT 0')
    ensure_column('users', 'magic_keys', 'INTEGER DEFAULT 0')
    ensure_column('users', 'bling', 'INTEGER DEFAULT 0')
    ensure_column('users', 'stricks', 'INTEGER DEFAULT 0')
    ensure_column('users', 'battles_won', 'INTEGER DEFAULT 0')
    ensure_column('users', 'last_income_amount', 'INTEGER DEFAULT 0')
    ensure_column('users', 'emerald', 'INTEGER DEFAULT 0')

    ensure_column('users', 'last_income_claim', 'TEXT DEFAULT NULL')
    ensure_column('users', 'last_income_amount', 'INTEGER DEFAULT 0')
    
    ensure_column('server_config', 'sauce_role', 'INTEGER DEFAULT NULL')
    ensure_column('daily_quests', 'quest4_progress', 'INTEGER DEFAULT 0')
    ensure_column('daily_quests', 'quest5_progress', 'INTEGER DEFAULT 0')

    ensure_column('users', 'last_sugarrush', 'TEXT DEFAULT NULL')
    ensure_column('users', 'sugarrush_active', 'INTEGER DEFAULT 0')
    ensure_column('users', 'sugarrush_expires', 'TEXT DEFAULT NULL')
    conn.commit()

    conn.close()

# Emoji configuration - UPDATED: Added copper and artifact box emojis
EMOJIS = {
    'xp': '<:xp:1424481970745770205>',
    'planks': '<:planks:1424503794254741686>',
    'stone': '<:stone:1424504056122179655>',
    'iron': '<:iron:1424473688274895080>',
    'copper': '<:copper:1426229582637568031>',  # NEW: Copper emoji
    'silver': '<:silver:1424502369076646009>',
    'gold': '<:gold:1424473679483637780>',
    'diamonds': '<a:diamond:1424473731450929185>',
    'levelbadge': '<:levelbadge:1424496577132757012>',
    'artifactbadge': '<:artifactbadge:1424496572720484432>',
    'emerald': '<:emerald:1433208103989547258>',
    'skinbadge': '<:skinbadge:1424499599112011900>',
    'characterbadge': '<:characterbadge:1424498247514329139>',
    'citybadge': '<:housebadge:1424496568056283317>',
    'aura': '<a:aura:1424473681891033108>',
    'pop': '<:pop:1424505306997854370>',
    'boost1': '<a:boost1:1424505149988012052>',
    'boost2': '<a:boost2:1424473689898094602>',
    'boost3': '<a:boost3:1424473694427939067>',
    'alert': '<a:alert:1424473684348768317>',
    'raredrop': '<:raredrop:1424466169795973201>',
    'superraredrop': '<:superraredrop:1424466648580100299>',
    'epicdrop': '<:epicdrop:1424466674652020837>',
    'mythicdrop': '<:mythicdrop:1424466698639118356>',
    'legendarydrop': '<:legendarydrop:1424466747561480243>',
    'ultradrop': '<:ultradrop:1424467733847736374>',
    'small_box': '<:smallbox:1424481985916698665>',
    'regular_box': '<:regularbox:1424481982112600074>',
    'big_box': '<:bigbox:1424481980283883721>',
    'mega_box': '<:megabox:1424481972612235474>',
    'omega_box': '<:omegabox:1424481975049388204>',
    'ultra_box': '<:ultrabox:1424481977943462060>',
    'rareskin': '<:rareskin:1424501370882490428>',
    'superrareskin': '<:superrareskin:1424501309091876884>',
    'epicskin': '<:epicskin:1424501301173157919>',
    'mythicskin': '<:mythicskin:1424501305703137320>',
    'legendaryskin': '<:legendaryskin:1424501303782150307>',
    'ultralegendaryskin': '<:ultraskin:1424501247209373786>',
    'mysterybox': '<:mysterybox:1424793170943938643>',
    'goldenxp': '<:goldenxp:1424794733942931568>',
    'pass': '<:pass:1424793168507043890>',
    'commandbadge': '<:commandbadge:1424800285750198272>',
    'passbadge': '<:passbadge:1424800276124012586>',
    'dailybadge': '<:dailybadge:1424800290397487144>',
    'dropbadge': '<:dropbadge:1424800266842148974>',
    'boostbadge': '<:boostbadge:1424801119263002685>',
    'master': '<:master:1424798376754675793>',
    'ultra': '<:ultra:1424798375110250598>',
    'ultimate': '<:ultimate:1424798372836937778>',
    'message': '<:message:1424793173338624188>',
    'tier0': '<:tier0:1424797590599241883>',
    'tier3': '<:tier3:1424797008971174049>',
    'tier5': '<:tier5:1424797048946954280>',
    'tier10': '<:tier10:1424797495845720255>',
    'tier20': '<:tier20:1424797011252744243>',
    'tier35': '<:tier35:1424797046371651605>',
    'tier50': '<:tier50:1424797013861597338>',
    'pin': '<:pin:1424796994236321792>',
    'mapmaker': '<:mapmaker:1424796997948412005>',
    'daily': '<:daily:1424797945768968306>',
    'levelup': '<:levelup:1424798059547856947>',
    'quests': '<:quests:1424798317451280454>',
    'lumbermill': '🏭',
    'quarry': '⛏️',
    'mine': '⚒️',
    'silver_mine': '🏦',
    'gold_mine': '💰',
    'diamond_mine': '💎',
    'bank': '🏛️',
    'castle': '🏰',
    'farm': '🌾',
    'sawmill': '🪵',
    'foundry': '🔥',
    'market': '🏪',
    'temple': '🛕',
    'library': '📚',
    'workshop': '🛠️',
    'bling': '<:bling:1210960115121791036>',
    'strick': '⚡️',
    'copper_mine': '🔶',  # NEW: Copper mine emoji
    'artifact_box': '<:boombox:1426230580160233628>',  # NEW: Artifact box emoji
    'magic_key': '<:magickey:1426872351294750783>'  # FIXED: Magic key emoji
}

# Box images - UPDATED: Added artifact box image
BOX_IMAGES = {
    'small_box': 'https://cdn.discordapp.com/attachments/1424048048811540523/1425912886173110342/New_Project_7.jpg',
    'regular_box': 'https://media.discordapp.net/attachments/1424048048811540523/1425912886911307776/New_Project_10.jpg',
    'big_box': 'https://media.discordapp.net/attachments/1424048048811540523/1425912885032386750/New_Project_12.jpg',
    'mega_box': 'https://media.discordapp.net/attachments/1424048048811540523/1425912885426655443/New_Project_6.jpg',
    'omega_box': 'https://media.discordapp.net/attachments/1424048048811540523/1425912884625543304/New_Project_11.jpg',
    'ultra_box': 'https://media.discordapp.net/attachments/1424048048811540523/1425912886533951570/New_Project_8.jpg',
    'mystery_box': 'https://cdn.discordapp.com/attachments/1424048048811540523/1425914552129687602/New_Project_13.jpg',  # FIXED: Mystery box image
    'artifact_box': 'https://cdn.discordapp.com/attachments/1424048048811540523/1426230190358528111/New_Project_14.jpg'  # NEW: Artifact box image
}

# Starr Drop images
STARR_DROP_IMAGES = {
    'Rare': 'https://media.discordapp.net/attachments/1424048048811540523/1424518297369575554/OIP.jpeg',
    'Super Rare': 'https://cdn.discordapp.com/attachments/1424048048811540523/1424518297076109322/OIP_1.webp',
    'Epic': 'https://media.discordapp.net/attachments/1424048048811540523/1424518296384045168/maxresdefault.jpg',
    'Mythic': 'https://media.discordapp.net/attachments/1424048048811540523/1424518295993847958/mythic-star-dropp-scaled.jpg',
    'Legendary': 'https://media.discordapp.net/attachments/1424048048811540523/1424518296773857340/OIP_2.webp',
    'Ultra Legendary': 'https://media.discordapp.net/attachments/1424048048811540523/1424518247759220747/IMG_0211.png'
}

# Level system - progressive difficulty
def calculate_level(xp):
    if xp <= 0:
        return 1, 100, 0
    
    levels = {
        (1, 10): lambda l: 100 * l,
        (11, 25): lambda l: 250 * (l - 10) + 1000,
        (26, 50): lambda l: 500 * (l - 25) + 4750,
        (51, 75): lambda l: 1000 * (l - 50) + 17000,
        (76, 100): lambda l: 2500 * (l - 75) + 42000
    }
    
    total_xp = 0
    current_level = 1
    
    for level in range(1, 101):
        for level_range, formula in levels.items():
            start, end = level_range
            if start <= level <= end:
                xp_needed = formula(level)
                if total_xp + xp_needed > xp:
                    return current_level, xp_needed, total_xp
                total_xp += xp_needed
                current_level = level + 1
                break
    
    return 100, 0, total_xp

# Golden XP Pass system
def calculate_golden_level(golden_xp):
    # Golden XP progression - easier than regular levels
    base_xp = 100
    level = 1
    
    while golden_xp >= base_xp and level < 50:
        golden_xp -= base_xp
        level += 1
        base_xp = int(base_xp * 1.1)  # 10% increase per level
    
    if level >= 50:
        # Infinite tiers after 50
        infinite_levels = (golden_xp // 3000)  # Hard as level 30
        level = 50 + infinite_levels
        xp_needed = 3000
        xp_current = golden_xp % 3000
    else:
        xp_needed = base_xp
        xp_current = golden_xp
    
    return level, xp_needed, xp_current

# Character data
CHARACTERS = {
    'KermitTheFrog': {'rarity': 'Rare', 'description': 'The famous green frog who loves to sing and dance in the swamp.'},
    'Haaland': {'rarity': 'Rare', 'description': 'A goal-scoring machine with incredible strength and precision.'},
    'MollyTheRat': {'rarity': 'Rare', 'description': 'A clever rat who always finds the cheesiest solutions.'},
    'BobbyBanana': {'rarity': 'Super Rare', 'description': 'A fruity fellow who slips and slides his way to victory.'},
    'WallyWalrus': {'rarity': 'Super Rare', 'description': 'The tusked titan of the arctic with a heart of gold.'},
    'PippinPenguin': {'rarity': 'Super Rare', 'description': 'A chilly champion who waddles with style and grace.'},
    'ZiggyZebra': {'rarity': 'Epic', 'description': 'Striped speedster who races through the savannah with flair.'},
    'GizmoGecko': {'rarity': 'Epic', 'description': 'A sticky-fingered genius who climbs to new heights.'},
    'FizzFlamingo': {'rarity': 'Epic', 'description': 'The pink poser who balances elegance and power.'},
    'MysticMoose': {'rarity': 'Mythic', 'description': 'Ancient antlered guardian of the northern forests.'},
    'BlazePhoenix': {'rarity': 'Mythic', 'description': 'Reborn from ashes with fiery determination and grace.'},
    'ThunderTurtle': {'rarity': 'Mythic', 'description': 'Slow but steady, carrying ancient wisdom on his shell.'},
    'CosmicKoala': {'rarity': 'Legendary', 'description': 'Starry-eyed dreamer who naps among the constellations.'},
    'NeoNinja': {'rarity': 'Legendary', 'description': 'Silent shadow warrior mastering ancient techniques.'},
    'QuantumQuokka': {'rarity': 'Legendary', 'description': 'Smiling scientist who bends reality with joy.'},
    'ChuckChimp': {'rarity': 'Rare', 'description': 'Banana-loving acrobat who swings through challenges.'},
    'StellarSeal': {'rarity': 'Super Rare', 'description': 'Lunar guardian who swims through starry oceans.'},
    'PixelPanda': {'rarity': 'Epic', 'description': 'Digital bear who codes his way to bamboo bliss.'},
    'Mist': {'rarity': 'Ultra Legendary', 'description': 'The controller of the Sauce cooperation, pulling strings from the shadows.'},
    'AymaneX': {'rarity': 'Ultra Legendary', 'description': 'The Bot\'s Boss who is behind everything, the master architect.'}
}

# Skin data with updated prices and increased count to 30
SKINS = {
    # Rare (8 skins)
    'Forest Camo': {'rarity': 'Rare', 'price_silver': 200},
    'Ocean Blue': {'rarity': 'Rare', 'price_silver': 200},
    'Desert Sand': {'rarity': 'Rare', 'price_silver': 200},
    'Arctic White': {'rarity': 'Rare', 'price_silver': 200},
    'Jungle Green': {'rarity': 'Rare', 'price_silver': 200},
    'Volcano Red': {'rarity': 'Rare', 'price_silver': 200},
    'Sky Blue': {'rarity': 'Rare', 'price_silver': 200},
    'Midnight Black': {'rarity': 'Rare', 'price_silver': 200},
    
    # Super Rare (6 skins)
    'Neon Glow': {'rarity': 'Super Rare', 'price_silver': 500, 'price_gold': 30},
    'Crystal Shard': {'rarity': 'Super Rare', 'price_silver': 500, 'price_gold': 30},
    'Volcanic Rock': {'rarity': 'Super Rare', 'price_silver': 500, 'price_gold': 30},
    'Galaxy Dust': {'rarity': 'Super Rare', 'price_silver': 500, 'price_gold': 30},
    'Electric Storm': {'rarity': 'Super Rare', 'price_silver': 500, 'price_gold': 30},
    'Rainbow Pulse': {'rarity': 'Super Rare', 'price_silver': 500, 'price_gold': 30},
    
    # Epic (6 skins)
    'Dragon Scale': {'rarity': 'Epic', 'price_silver': 750, 'price_gold': 50},
    'Phoenix Feather': {'rarity': 'Epic', 'price_silver': 750, 'price_gold': 50},
    'Unicorn Horn': {'rarity': 'Epic', 'price_silver': 750, 'price_gold': 50},
    'Mermaid Tail': {'rarity': 'Epic', 'price_silver': 750, 'price_gold': 50},
    'Griffin Wing': {'rarity': 'Epic', 'price_silver': 750, 'price_gold': 50},
    'Hydra Scale': {'rarity': 'Epic', 'price_silver': 750, 'price_gold': 50},
    
    # Mythic (5 skins)
    'Cosmic Void': {'rarity': 'Mythic', 'price_silver': 1500, 'price_gold': 100, 'price_diamond': 5},
    'Time Traveler': {'rarity': 'Mythic', 'price_silver': 1500, 'price_gold': 100, 'price_diamond': 5},
    'Quantum Flux': {'rarity': 'Mythic', 'price_silver': 1500, 'price_gold': 100, 'price_diamond': 5},
    'Celestial Being': {'rarity': 'Mythic', 'price_silver': 1500, 'price_gold': 100, 'price_diamond': 5},
    'Ancient Guardian': {'rarity': 'Mythic', 'price_silver': 1500, 'price_gold': 100, 'price_diamond': 5},
    
    # Legendary (3 skins)
    'Solar Flare': {'rarity': 'Legendary', 'price_silver': 3500, 'price_gold': 250, 'price_diamond': 25},
    'Lunar Eclipse': {'rarity': 'Legendary', 'price_silver': 3500, 'price_gold': 250, 'price_diamond': 25},
    'Stellar Nova': {'rarity': 'Legendary', 'price_silver': 3500, 'price_gold': 250, 'price_diamond': 25},
    
    # Ultra Legendary (2 skins)
    'Infinity Gauntlet': {'rarity': 'Ultra Legendary', 'price_silver': 10000, 'price_gold': 500, 'price_diamond': 50},
    'Omnipotent Crown': {'rarity': 'Ultra Legendary', 'price_silver': 10000, 'price_gold': 500, 'price_diamond': 50}
}

# Artifact data
ARTIFACTS = {
    'Bibi\'s Bat': 35.0,
    'Poco\'s Guitar': 20.0,
    'Kenji\'s Sword': 12.0,
    'Charlie\'s Spider': 8.1,
    'Brock\'s Sunglasses': 5.5,
    'Bonnie\'s Canon': 4.0,
    'Gus\'s Balloon': 3.0,
    'Max\'s Energy Drink': 2.7,
    'Meeple\'s Dice': 2.1,
    'Colette\'s Book': 1.8,
    'Byron\'s Potion': 1.6,
    'Tara\'s Card': 1.2,
    'Hank\'s Tank': 1.0,
    'Finx\'s Staff': 0.9,
    'Doug\'s Wiener': 0.1
}

# City Building System - UPDATED: Increased copper and planks requirements by 80% and 100% respectively
CITY_BUILDINGS = {
    'lumbermill': {
        'name': 'Lumbermill',
        'emoji': EMOJIS['lumbermill'],
        'max_level': 3,
        'costs': {
            1: {'planks': 20000, 'stone': 600, 'iron': 70, 'copper': 50},  
            2: {'planks': 75000, 'stone': 2950, 'iron': 270, 'silver': 50, 'copper': 270}, 
            3: {'planks': 800000, 'stone': 35850, 'iron': 2810, 'silver': 300, 'gold': 30, 'copper': 1810} 
        },
        'outputs': {
            1: {'planks': 100},  
            2: {'planks': 3500}, 
            3: {'planks': 10000}  
        },
        'collection_hours': 1,
        'description': 'Produces planks for your city development',
        'requirements': {}
    },
    'quarry': {
        'name': 'Quarry',
        'emoji': EMOJIS['quarry'],
        'max_level': 3,
        'costs': {
            1: {'planks': 50000, 'stone': 3900, 'iron': 135, 'copper': 135},  
            2: {'planks': 350000, 'stone': 7700, 'iron': 405, 'silver': 175, 'copper': 405},  
            3: {'planks': 5000000, 'stone': 50100, 'iron': 3215, 'silver': 1225, 'gold': 90, 'copper': 2215}  
        },
        'outputs': {
            1: {'stone': 500}, 
            2: {'stone': 2450},  
            3: {'stone': 5350}  
        },
        'collection_hours': 1,
        'description': 'Mines stone for construction projects',
        'requirements': {}
    },
    'mine': {
        'name': 'Iron Mine',
        'emoji': EMOJIS['mine'],
        'max_level': 3,
        'costs': {
            1: {'planks': 100000, 'stone': 5200, 'iron': 1800, 'copper': 180}, 
            2: {'planks': 300000, 'stone': 15600, 'iron': 11400, 'silver': 100, 'copper': 540},  
            3: {'planks': 900000, 'stone': 56800, 'iron': 26200, 'silver': 300, 'gold': 20, 'copper': 3620}  
        },
        'outputs': {
            1: {'iron': 100},
            2: {'iron': 300},
            3: {'iron': 800}   
        },
        'collection_hours': 2,
        'description': 'Extracts iron for tools and buildings',
        'requirements': {}
    },
    'copper_mine': {
        'name': 'Copper Mine',
        'emoji': EMOJIS['copper_mine'],
        'max_level': 3,
        'costs': {
            1: {'planks': 50000, 'stone': 3500, 'iron': 400, 'copper': 2000}, 
            2: {'planks': 160000, 'stone': 19500, 'iron': 2700, 'silver': 50, 'copper': 5000}, 
            3: {'planks': 680000, 'stone': 58500, 'iron': 8100, 'silver': 150, 'gold': 5, 'copper': 15000}  
        },
        'outputs': {
            1: {'copper': 100},
            2: {'copper': 350},
            3: {'copper': 750}
        },
        'collection_hours': 3,
        'description': 'Mines copper for advanced construction and artifacts',
        'requirements': {'mine': 1}
    },
    'silver_mine': {
        'name': 'Silver Mine',
        'emoji': EMOJIS['silver_mine'],
        'max_level': 3,
        'costs': {
            1: {'planks': 25000, 'stone': 10400, 'iron': 3600, 'silver': 350, 'copper': 450}, 
            2: {'planks': 75000, 'stone': 31200, 'iron': 10800, 'silver': 1000, 'gold': 25, 'copper': 1350}, 
            3: {'planks': 300000, 'stone': 93600, 'iron': 32400, 'silver': 6000, 'gold': 75, 'copper': 4050}
        },
        'outputs': {
            1: {'silver': 20},  
            2: {'silver': 50},  
            3: {'silver': 300}  
        },
        'collection_hours': 4,
        'description': 'Mines precious silver for trading',
        'requirements': {'mine': 1, 'copper_mine': 1}
    },
    'gold_mine': {
        'name': 'Gold Mine',
        'emoji': EMOJIS['gold_mine'],
        'max_level': 3,
        'costs': {
            1: {'planks': 50000, 'stone': 19500, 'iron': 7200, 'silver': 2000, 'gold': 70, 'copper': 900},  # Increased planks by 100%, copper by 80%
            2: {'planks': 150000, 'stone': 58500, 'iron': 21600, 'silver': 6000, 'gold': 200, 'copper': 2700},  # Increased planks by 100%, copper by 80%
            3: {'planks': 1000000, 'stone': 175500, 'iron': 64800, 'silver': 18000, 'gold': 1000, 'copper': 8100}  # Increased planks by 100%, copper by 80%
        },
        'outputs': {
            1: {'gold': 5},
            2: {'gold': 20},
            3: {'gold': 50}
        },
        'collection_hours': 8,
        'description': 'Extracts valuable gold for premium items',
        'requirements': {'silver_mine': 1}
    },
    'diamond_mine': {
        'name': 'Diamond Mine',
        'emoji': EMOJIS['diamond_mine'],
        'max_level': 3,
        'costs': {
            1: {'planks': 100000, 'stone': 31000, 'iron': 9500, 'silver': 3000, 'gold': 300, 'diamonds': 10, 'copper': 5000},
            2: {'planks': 300000, 'stone': 117000, 'iron': 30500, 'silver': 9000, 'gold': 1500, 'diamonds': 30, 'copper': 10000},
            3: {'planks': 1500000, 'stone': 451000, 'iron': 101500, 'silver': 30000, 'gold': 4000, 'diamonds': 90, 'copper': 26200} 
        },
        'outputs': {
            1: {'diamonds': 1},
            2: {'diamonds': 5},
            3: {'diamonds': 8}
        },
        'collection_hours': 48,
        'description': 'Mines extremely rare diamonds for ultimate items',
        'requirements': {'gold_mine': 1}
    },
    'bank': {
        'name': 'City Bank',
        'emoji': EMOJIS['bank'],
        'max_level': 3,
        'costs': {
            1: {'planks': 75000, 'stone': 13000, 'iron': 4500, 'silver': 2000, 'gold': 100, 'copper': 2675},  
            2: {'planks': 225000, 'stone': 39000, 'iron': 13500, 'silver': 9000, 'gold': 600, 'copper': 5025},  
            3: {'planks': 875000, 'stone': 117000, 'iron': 40500, 'silver': 27000, 'gold': 1800, 'copper': 10075}  
        },
        'outputs': {
            1: {'silver': 35, 'gold': 2},  # 100% increase for silver
            2: {'silver': 200, 'gold': 10},  # 100% increase for silver
            3: {'silver': 350, 'gold': 20}  # 100% increase for silver
        },
        'collection_hours': 12,
        'description': 'Generates silver and gold through city commerce',
        'requirements': {'silver_mine': 1}
    },
    'castle': {
        'name': 'Royal Castle',
        'emoji': EMOJIS['castle'],
        'max_level': 3,
        'costs': {
            1: {'planks': 250000, 'stone': 52000, 'iron': 18000, 'silver': 10000, 'gold': 1000, 'diamonds': 50, 'copper': 2250},  # Increased planks by 100%, copper by 80%
            2: {'planks': 2750000, 'stone': 156000, 'iron': 54000, 'silver': 30000, 'gold': 3000, 'diamonds': 150, 'copper': 6750},  # Increased planks by 100%, copper by 80%
            3: {'planks': 9250000, 'stone': 468000, 'iron': 162000, 'silver': 90000, 'gold': 9000, 'diamonds': 450, 'copper': 20250}  # Increased planks by 100%, copper by 80%
        },
        'outputs': {
            1: {'planks': 8000, 'stone': 640, 'iron': 320, 'silver': 160, 'gold': 5, 'diamonds': 1, 'copper': 110},
            2: {'planks': 240000, 'stone': 1920, 'iron': 960, 'silver': 480, 'gold': 15, 'diamonds': 3, 'copper': 530},
            3: {'planks': 1000000, 'stone': 5760, 'iron': 1880, 'silver': 1440, 'gold': 30, 'diamonds': 5, 'copper': 990}
        },
        'collection_hours': 24,
        'description': 'The ultimate building that produces all resources',
        'requirements': {'bank': 2, 'diamond_mine': 1}
    },
    'farm': {
        'name': 'Farm',
        'emoji': EMOJIS['farm'],
        'max_level': 3,
        'costs': {
            1: {'planks': 10000, 'stone': 1300, 'copper': 545},  
            2: {'planks': 70000, 'stone': 3900, 'iron': 90, 'copper': 2135}, 
            3: {'planks': 1000000, 'stone': 11700, 'iron': 270, 'silver': 50, 'copper': 5405} 
        },
        'outputs': {
            1: {'planks': 240, 'stone': 120},  
            2: {'planks': 720, 'stone': 360},  
            3: {'planks': 2160, 'stone': 1080} 
        },
        'collection_hours': 2,
        'description': 'Produces basic resources through farming',
        'requirements': {}
    },
    'sawmill': {
        'name': 'Sawmill',
        'emoji': EMOJIS['sawmill'],
        'max_level': 3,
        'costs': {
            1: {'planks': 200000, 'stone': 2600, 'iron': 180, 'copper': 180},  
            2: {'planks': 600000, 'stone': 7800, 'iron': 540, 'silver': 25, 'copper': 540},  
            3: {'planks': 3000000, 'stone': 33400, 'iron': 3620, 'silver': 75, 'gold': 5, 'copper': 2620}  
        },
        'outputs': {
            1: {'planks': 640}, 
            2: {'planks': 1920},
            3: {'planks': 8760} 
        },
        'collection_hours': 1,
        'description': 'Advanced wood production facility',
        'requirements': {'lumbermill': 1}
    },
    'foundry': {
        'name': 'Foundry',
        'emoji': EMOJIS['foundry'],
        'max_level': 3,
        'costs': {
            1: {'planks': 150000, 'stone': 6500, 'iron': 2700, 'copper': 135},  
            2: {'planks': 450000, 'stone': 19500, 'iron': 8100, 'silver': 75, 'copper': 405}, 
            3: {'planks': 1350000, 'stone': 58500, 'iron': 24300, 'silver': 225, 'gold': 10, 'copper': 1215}  
        },
        'outputs': {
            1: {'iron': 80, 'stone': 160},   
            2: {'iron': 240, 'stone': 480},  
            3: {'iron': 500, 'stone': 2000} 
        },
        'collection_hours': 3,
        'description': 'Produces refined metals and stone',
        'requirements': {'mine': 1}
    },
    'market': {
        'name': 'Marketplace',
        'emoji': EMOJIS['market'],
        'max_level': 3,
        'costs': {
            1: {'planks': 40000, 'stone': 5200, 'iron': 900, 'silver': 200, 'copper': 360},  
            2: {'planks': 120000, 'stone': 15600, 'iron': 2700, 'silver': 600, 'gold': 15, 'copper': 1080},  
            3: {'planks': 1360000, 'stone': 46800, 'iron': 8100, 'silver': 1800, 'gold': 45, 'copper': 5240} 
        },
        'outputs': {
            1: {'silver': 16, 'gold': 1},  
            2: {'silver': 48, 'gold': 2},  
            3: {'silver': 144, 'gold': 5} 
        },
        'collection_hours': 6,
        'description': 'Trading hub that generates silver and gold',
        'requirements': {'bank': 1}
    },
    'temple': {
        'name': 'Ancient Temple',
        'emoji': EMOJIS['temple'],
        'max_level': 3,
        'costs': {
            1: {'planks': 300000, 'stone': 19500, 'iron': 3600, 'silver': 800, 'gold': 150, 'copper': 540},  # Increased planks by 100%, copper by 80%
            2: {'planks': 880000, 'stone': 58500, 'iron': 10800, 'silver': 2400, 'gold': 350, 'diamonds': 7, 'copper': 5620},  # Increased planks by 100%, copper by 80%
            3: {'planks': 1540000, 'stone': 175500, 'iron': 32400, 'silver': 7200, 'gold': 550, 'diamonds': 30, 'copper': 14860}  # Increased planks by 100%, copper by 80%
        },
        'outputs': {
            1: {'gold': 2, 'diamonds': 1},
            2: {'gold': 10, 'diamonds': 2},
            3: {'gold': 30, 'diamonds': 3}
        },
        'collection_hours': 36,
        'description': 'Sacred place that generates gold and diamonds',
        'requirements': {'bank': 2}
    },
    'library': {
        'name': 'Grand Library',
        'emoji': EMOJIS['library'],
        'max_level': 3,
        'costs': {
            1: {'planks': 500000, 'stone': 9400, 'iron': 1000, 'silver': 350, 'copper': 450},  # Increased planks by 100%, copper by 80%
            2: {'planks': 150000, 'stone': 31200, 'iron': 5400, 'silver': 1500, 'gold': 25, 'copper': 2350},  # Increased planks by 100%, copper by 80%
            3: {'planks': 750000, 'stone': 93600, 'iron': 16200, 'silver': 4500, 'gold': 75, 'copper': 9050}  # Increased planks by 100%, copper by 80%
        },
        'outputs': {
            1: {'planks': 48000, 'stone': 320, 'iron': 160, 'silver': 10},  # 800% for planks, 800% for stone, 800% for iron, 100% for silver
            2: {'planks': 144000, 'stone': 960, 'iron': 480, 'silver': 30}, # 800% for planks, 800% for stone, 800% for iron, 100% for silver
            3: {'planks': 432000, 'stone': 2880, 'iron': 1440, 'silver': 90} # 800% for planks, 800% for stone, 800% for iron, 100% for silver
        },
        'collection_hours': 8,
        'description': 'Center of knowledge that produces multiple resources',
        'requirements': {'market': 1}
    },
    'workshop': {
        'name': 'Master Workshop',
        'emoji': EMOJIS['workshop'],
        'max_level': 3,
        'costs': {
            1: {'planks': 75000, 'stone': 9600, 'iron': 3400, 'silver': 700, 'gold': 55, 'copper': 875},  # Increased planks by 100%, copper by 80%
            2: {'planks': 225000, 'stone': 46800, 'iron': 16200, 'silver': 3000, 'gold': 225, 'diamonds': 8, 'copper': 2025},  # Increased planks by 100%, copper by 80%
            3: {'planks': 675000, 'stone': 140400, 'iron': 48600, 'silver': 9000, 'gold': 675, 'diamonds': 24, 'copper': 6075}  # Increased planks by 100%, copper by 80%
        },
        'outputs': {
            1: {'planks': 56000, 'stone': 400, 'iron': 240, 'silver': 16, 'gold': 1},  # 800% for planks, 800% for stone, 800% for iron, 100% for silver
            2: {'planks': 168000, 'stone': 1200, 'iron': 720, 'silver': 48, 'gold': 3}, # 800% for planks, 800% for stone, 800% for iron, 100% for silver
            3: {'planks': 704000, 'stone': 3600, 'iron': 2160, 'silver': 144, 'gold': 9} # 800% for planks, 800% for stone, 800% for iron, 100% for silver
        },
        'collection_hours': 12,
        'description': 'Advanced facility that produces all basic resources',
        'requirements': {'foundry': 2, 'sawmill': 2}
    }
}

# New Pop-up System - Brawl Stars Themed
POPUP_QUESTIONS = {
    'two_truths_lie': [
        {
            'question': "**2 Truths & 1 Lie**\n\n• Chester's description contains the word 'Hate'\n• Chester has 5 different supers\n• One chester super heals 2500 HP at Power 1",
            'answer': '3',
            'difficulty': 'Easy',
            'type': 'two_truths_lie'
        },
        # Add more questions here in the same format
    ],
    'guess_brawler': [
        {
            'question': "**Guess the Brawler**\n\n• Brawler has unique super icons\n• Brawler's reload speed is normal\n• Brawler's rarity is legendary",
            'answer': 'chester',
            'difficulty': 'Easy',
            'type': 'guess_brawler'
        },
        # Add more questions here in the same format
    ],
    'trivia': [
        {
            'question': "**Trivia**\n\nWhat's the strongest released brawler in 2018?",
            'answer': 'rosa',
            'difficulty': 'Easy',
            'type': 'trivia'
        },
        # Add more questions here in the same format
    ],
    'free_xp': {
        'question': "**FREE XP!**\n\nQuick! Type anything in the next 60 seconds to claim your reward!",
        'answer': 'any',
        'difficulty': 'Free',
        'type': 'free_xp'
    }
}

# Boost rewards
BOOST_REWARDS = {
    1: {'planks': 500000, 'stone': 20000, 'iron': 3000, 'silver': 1000, 'gold': 250, 'diamonds': 10, 'copper': 3000},
    2: {'planks': 750000, 'stone': 50000, 'iron': 5000, 'silver': 3000, 'gold': 500, 'diamonds': 25, 'copper': 5000},
    3: {'planks': 1000000, 'stone': 120000, 'iron': 10000, 'silver': 5000, 'gold': 1000, 'diamonds': 50, 'copper': 8000}
}

# Bling income types - UPDATED: New tier system 1-7
BLING_INCOME = {
    '1': 20,   # A reply - Brainrot Post - 2-10 words posts...
    '2': 100,  # A post with no graphic, OSTs, youtube video with no edits...
    '3': 150,  # A post with ultra basic graphic, youtube video with very low edits...
    '4': 250,  # A post with decent graphics, small thread with no graphics & youtube video with below average edit...
    '5': 350,  # A post with multiple decent graphics, a long thread, decent edited youtube video...
    '6': 500,  # A long thread with multiple graphics, well edited videos above 3 minutes.
    '7': 800   # Hosting an event with a prize, youtube videos above 7 minutes and very well edited...
}

# Bling shop items - UPDATED: Rebalanced prices
BLING_SHOP = {
    'strick_removal': {'name': 'Strick Removal', 'price': 2500, 'description': 'Remove one strick from your account'},
    'strick_shield': {'name': 'Strick Shield (7 Days)', 'price': 2000, 'description': 'Protection from stricks for 7 days'},
    'brawl_pass': {'name': 'Brawl Pass Giveaway Ticket', 'price': 1200, 'description': 'Enter Brawl Pass giveaways'}
}

# FIXED: Golden Pass rewards - progressive rewards with big chunks
def get_golden_pass_rewards(boost_tier, tier):
    """Get rewards for specific tier with progression - big chunks instead of same each tier"""
    if tier <= 50:
        # Main pass tiers 1-50 with progression - bigger chunks
        progression_factor = 1 + (tier / 50)  # 1 to 2 progression
        
        # Define which resource to give at each tier (rotating pattern)
        resource_pattern = [
            'planks', 'stone', 'iron', 'copper', 'silver', 'gold', 'diamonds',
            'planks', 'stone', 'iron', 'copper', 'silver'
        ]
        resource = resource_pattern[(tier - 1) % len(resource_pattern)]
        
        # Base amounts that scale with tier
        base_amounts = {
            'planks': 2500,
            'stone': 500,
            'iron': 250,
            'copper': 125,
            'silver': 100,
            'gold': 25,
            'diamonds': 2
        }
        
        # Calculate amount with progression
        base_amount = base_amounts[resource]
        amount = int(base_amount * progression_factor)
        
        # Apply boost multipliers
        if boost_tier == 'boost1':
            amount = int(amount * 1.5)
        elif boost_tier == 'boost2':
            amount = int(amount * 2.0)
        elif boost_tier == 'boost3':
            amount = int(amount * 2.5)
        
        # Special rewards every 10 tiers
        if tier % 10 == 0:
            if boost_tier == 'free':
                return {resource: amount, 'gold': 10, 'diamonds': 1}
            elif boost_tier == 'boost1':
                return {resource: amount, 'gold': 25, 'diamonds': 3}
            elif boost_tier == 'boost2':
                return {resource: amount, 'gold': 50, 'diamonds': 6}
            elif boost_tier == 'boost3':
                return {resource: amount, 'gold': 75, 'diamonds': 10}
        
        return {resource: amount}
    else:
        # Infinite tiers after 50 - only gold
        base_gold = 5
        if boost_tier == 'free':
            return {'gold': base_gold}
        elif boost_tier == 'boost1':
            return {'gold': base_gold * 2}
        elif boost_tier == 'boost2':
            return {'gold': base_gold * 3}
        elif boost_tier == 'boost3':
            return {'gold': base_gold * 4}
    
    return {}

def get_box_reward(user_id=None):
    """Get box reward with optional Sugar Rush multiplier"""
    reward_roll = random.random() * 100
    
    if reward_roll < 35.9:  # 35.9% chance - Planks
        base_amount = random.randint(200, 700)
        return f"{base_amount} Planks"
    elif reward_roll < 60.9:  # 25% chance (35.9-60.9)
        base_amount = random.randint(40, 90)
        return f"{base_amount} Stone"
    elif reward_roll < 80.9:  # 20% chance (60.9-80.9)
        base_amount = random.randint(12, 30)
        return f"{base_amount} Iron"
    elif reward_roll < 93.1:  # 12.2% chance (80.9-93.1)
        base_amount = random.randint(30, 90)
        return f"{base_amount} Copper"
    elif reward_roll < 97.1:  # 4% chance (93.1-97.1)
        base_amount = random.randint(5, 10)
        return f"{base_amount} Silver"
    elif reward_roll < 99.1:  # 2% chance (97.1-99.1)
        base_amount = random.randint(1, 3)
        return f"{base_amount} Gold"
    elif reward_roll < 99.2:  # 0.1% chance (99.1-99.2)
        return "1 Diamond"
    elif reward_roll < 99.3:  # 0.1% chance (99.2-99.3)
        return "Mystery Box"
    elif reward_roll < 99.4:  # 0.1% chance (99.3-99.4)
        return "Magic Key"
    elif reward_roll < 99.5:  # 0.1% chance (99.4-99.5)
        return "Ultra Box"
    else:  # 0.5% chance (99.5-100)
        return "1 Emerald"

# UPDATED: Mystery box reward distribution
def get_mystery_box_reward():
    mystery_roll = random.random() * 100
    
    if mystery_roll < 20:  # 20% chance
        # Ultra Box + 3 diamonds
        return {'type': 'ultra_box_diamonds', 'ultra_boxes': 1, 'diamonds': 1}
    elif mystery_roll < 50:  # 30% chance (20-50) - Characters
        character_roll = random.random()
        if character_roll < 0.6:  # 60% of character chance - Epic
            epic_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Epic']
            return {'type': 'character', 'character': random.choice(epic_chars), 'rarity': 'Epic'}
        elif character_roll < 0.9:  # 30% of character chance - Mythic
            mythic_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Mythic']
            return {'type': 'character', 'character': random.choice(mythic_chars), 'rarity': 'Mythic'}
        else:  # 10% of character chance - Legendary
            legendary_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Legendary']
            return {'type': 'character', 'character': random.choice(legendary_chars), 'rarity': 'Legendary'}
    elif mystery_roll < 60: 
        return {'type': 'gold', 'amount': 100}
    elif mystery_roll < 61:  # 1% chance (60-61) - 20 Diamonds
        return {'type': 'diamonds', 'amount': 5}
    elif mystery_roll < 90:  # 29% chance (61-90) - 1000 Iron
        return {'type': 'iron', 'amount': 1000}
    else:  # 10% chance (90-100) - Magic Key
        return {'type': 'magic_key', 'amount': 5}

class StarrDropView(discord.ui.View):
    def __init__(self, rarity):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.rarity = rarity
        self.claimed = False
    
    @discord.ui.button(label='Catch!', style=discord.ButtonStyle.green, emoji='⭐')
    async def catch_drop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            await interaction.response.send_message("This Starr Drop has already been caught!", ephemeral=True)
            return
        
        # Check if drop expired
        drop_data = active_starr_drops.get(interaction.channel.id)
        if not drop_data or datetime.datetime.now() > drop_data['expires']:
            await interaction.response.send_message("This Starr Drop has expired!", ephemeral=True)
            return
        
        self.claimed = True
        drop_data['claimed'] = True
        button.disabled = True
        button.label = 'Caught!'
        button.style = discord.ButtonStyle.gray
        
        # Update daily quest progress
        quests = db.get_daily_quests(interaction.user.id)
        if quests and quests['quest3_progress'] < 1:
            db.update_daily_quest(interaction.user.id, 'quest3_progress', 1)
        
        # Track drops caught
        c = db.conn.cursor()
        c.execute("UPDATE users SET drops_caught = drops_caught + 1 WHERE user_id = ?", (interaction.user.id,))
        db.conn.commit()
        
        # Get reward
        reward = get_starr_drop_reward(self.rarity)
        
        # Update embed to show who caught it
        embed = interaction.message.embeds[0]
        embed.color = 0x00ff00  # Change to green
        embed.add_field(
            name="🎉 CAUGHT!",
            value=f"Caught by {interaction.user.mention}",
            inline=False
        )
        
        if 'character' in reward:
            char_name = reward['character']
            char_rarity = CHARACTERS[char_name]['rarity']
            
            # Add character to user's collection
            c = db.conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO user_characters (user_id, character_name, rarity) VALUES (?, ?, ?)",
                (interaction.user.id, char_name, char_rarity)
            )
            db.conn.commit()
            
            embed.add_field(
                name="🎭 CHARACTER UNLOCKED!",
                value=f"**{char_name}** ({char_rarity})\n{CHARACTERS[char_name]['description']}",
                inline=False
            )
        else:
            currency, amount = reward['currency'], reward['amount']
            # Double silver rewards
            if currency == 'silver':
                amount = amount * 2
            db.update_user_currency(interaction.user.id, currency, amount)
            
            embed.add_field(
                name="💰 REWARD",
                value=f"{EMOJIS[currency]} {amount} {currency.capitalize()}",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Remove from active drops
        if interaction.channel.id in active_starr_drops:
            del active_starr_drops[interaction.channel.id]
    
    async def on_timeout(self):
        # Disable button when timeout occurs
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                item.label = 'Expired!'
                item.style = discord.ButtonStyle.gray
        
        # Get the message to update it
        message = self.message
        if message:
            embed = message.embeds[0]
            embed.color = 0xff0000  # Change to red
            embed.add_field(
                name="⏰ EXPIRED",
                value="No one caught this Starr Drop in time!",
                inline=False
            )
            await message.edit(embed=embed, view=self)
        
        # Remove from active drops
        channel_id = message.channel.id if message else None
        if channel_id and channel_id in active_starr_drops:
            del active_starr_drops[channel_id]

class BotDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    
    def get_user(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        if result:
            return dict(result)  # Convert to regular dict to avoid attribute issues
        return None
    
    def create_user(self, user_id):
        c = self.conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        self.conn.commit()
    
    # NEW: Server-specific XP methods
    def get_server_user_xp(self, user_id, guild_id):
        c = self.conn.cursor()
        c.execute("SELECT xp FROM server_xp WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        result = c.fetchone()
        return result['xp'] if result else 0
    
    def update_server_user_xp(self, user_id, guild_id, xp_gained):
        c = self.conn.cursor()
        current_xp = self.get_server_user_xp(user_id, guild_id)
        new_xp = current_xp + xp_gained
        c.execute("INSERT OR REPLACE INTO server_xp (user_id, guild_id, xp) VALUES (?, ?, ?)",
                 (user_id, guild_id, new_xp))
        
        # Update weekly XP
        week = datetime.datetime.now().strftime("%Y-%W")
        c.execute("INSERT OR REPLACE INTO weekly_xp (user_id, week, xp_gained) VALUES (?, ?, COALESCE((SELECT xp_gained FROM weekly_xp WHERE user_id = ? AND week = ?), 0) + ?)",
                 (user_id, week, user_id, week, xp_gained))
        
        self.conn.commit()
        return new_xp
    
    def update_user_currency(self, user_id, currency, amount):
        self.create_user(user_id)
        c = self.conn.cursor()
        c.execute(f"UPDATE users SET {currency} = {currency} + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def get_user_currency(self, user_id, currency):
        user = self.get_user(user_id)
        return user.get(currency, 0) if user else 0

    def get_popup_config(self, guild_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM popup_config WHERE guild_id = ?", (guild_id,))
        config = c.fetchone()
        if not config:
            # Create default config
            c.execute("INSERT INTO popup_config (guild_id) VALUES (?)", (guild_id,))
            self.conn.commit()
            c.execute("SELECT * FROM popup_config WHERE guild_id = ?", (guild_id,))
            config = c.fetchone()
        return dict(config) if config else None
    
    def update_popup_config(self, guild_id, channel_id=None, cooldown=None, enabled=None):
        c = self.conn.cursor()
        updates = []
        params = []
        
        if channel_id is not None:
            updates.append("popup_channel = ?")
            params.append(channel_id)
        if cooldown is not None:
            updates.append("popup_cooldown = ?")
            params.append(cooldown)
        if enabled is not None:
            updates.append("popup_enabled = ?")
            params.append(enabled)
        
        if updates:
            params.append(guild_id)
            query = f"UPDATE popup_config SET {', '.join(updates)} WHERE guild_id = ?"
            c.execute(query, params)
            self.conn.commit()

    def get_server_config(self, guild_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM server_config WHERE guild_id = ?", (guild_id,))
        config = c.fetchone()
        if not config:
            # Create default config
            c.execute("INSERT INTO server_config (guild_id) VALUES (?)", (guild_id,))
            self.conn.commit()
            c.execute("SELECT * FROM server_config WHERE guild_id = ?", (guild_id,))
            config = c.fetchone()
        return dict(config) if config else None
    
    def update_server_config(self, guild_id, **kwargs):
        c = self.conn.cursor()
        updates = []
        params = []
        
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            params.append(value)
        
        if updates:
            params.append(guild_id)
            query = f"UPDATE server_config SET {', '.join(updates)} WHERE guild_id = ?"
            c.execute(query, params)
            self.conn.commit()

    def get_daily_quests(self, user_id):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        c = self.conn.cursor()
        c.execute("SELECT * FROM daily_quests WHERE user_id = ? AND date = ?", (user_id, today))
        quests = c.fetchone()
        if not quests:
            c.execute("INSERT INTO daily_quests (user_id, date) VALUES (?, ?)", (user_id, today))
            self.conn.commit()
            c.execute("SELECT * FROM daily_quests WHERE user_id = ? AND date = ?", (user_id, today))
            quests = c.fetchone()
        return dict(quests) if quests else None
    
    def update_daily_quest(self, user_id, quest_field, progress):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        c = self.conn.cursor()
        c.execute(f"UPDATE daily_quests SET {quest_field} = ? WHERE user_id = ? AND date = ?", 
                 (progress, user_id, today))
        self.conn.commit()
    
    def get_active_events(self, guild_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM active_events WHERE guild_id = ?", (guild_id,))
        results = c.fetchall()
        return [dict(row) for row in results]
    
    def add_active_event(self, guild_id, event_type, multiplier, duration_hours, reward_item=None, reward_amount=0):
        end_time = (datetime.datetime.now() + datetime.timedelta(hours=duration_hours)).isoformat()
        c = self.conn.cursor()
        c.execute("INSERT INTO active_events (guild_id, event_type, multiplier, end_time, reward_item, reward_amount) VALUES (?, ?, ?, ?, ?, ?)",
                 (guild_id, event_type, multiplier, end_time, reward_item, reward_amount))
        self.conn.commit()
    
    def clear_expired_events(self):
        now = datetime.datetime.now().isoformat()
        c = self.conn.cursor()
        c.execute("DELETE FROM active_events WHERE end_time < ?", (now,))
        self.conn.commit()
    
    def has_claimed_mystery_box(self, user_id, level):
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM mystery_claims WHERE user_id = ? AND level_claimed = ?", (user_id, level))
        return c.fetchone() is not None
    
    def add_mystery_claim(self, user_id, level):
        c = self.conn.cursor()
        c.execute("INSERT INTO mystery_claims (user_id, level_claimed) VALUES (?, ?)", (user_id, level))
        self.conn.commit()
    
    def add_box_to_user(self, user_id, box_type, quantity=1):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_boxes (user_id, box_type, quantity) VALUES (?, ?, COALESCE((SELECT quantity FROM user_boxes WHERE user_id = ? AND box_type = ?), 0) + ?)",
                 (user_id, box_type, user_id, box_type, quantity))
        self.conn.commit()
    
    def get_user_boxes(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT box_type, quantity FROM user_boxes WHERE user_id = ?", (user_id,))
        results = c.fetchall()
        return [(row[0], row[1]) for row in results]
        # Sauce Items Methods
    def get_user_sauce_items(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT item_name, quantity FROM sauce_items WHERE user_id = ?", (user_id,))
        results = c.fetchall()
        return [(row[0], row[1]) for row in results]
    
    def add_sauce_item(self, user_id, item_name, quantity=1):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO sauce_items (user_id, item_name, quantity) VALUES (?, ?, COALESCE((SELECT quantity FROM sauce_items WHERE user_id = ? AND item_name = ?), 0) + ?)",
                 (user_id, item_name, user_id, item_name, quantity))
        self.conn.commit()
    
    def remove_sauce_item(self, user_id, item_name, quantity=1):
        c = self.conn.cursor()
        c.execute("UPDATE sauce_items SET quantity = quantity - ? WHERE user_id = ? AND item_name = ? AND quantity >= ?",
                 (quantity, user_id, item_name, quantity))
        self.conn.commit()
        # Remove if quantity is 0
        c.execute("DELETE FROM sauce_items WHERE user_id = ? AND item_name = ? AND quantity <= 0", (user_id, item_name))
        self.conn.commit()

    def remove_box_from_user(self, user_id, box_type, quantity=1):
        c = self.conn.cursor()
        c.execute("UPDATE user_boxes SET quantity = quantity - ? WHERE user_id = ? AND box_type = ? AND quantity >= ?",
                 (quantity, user_id, box_type, quantity))
        self.conn.commit()
        # Remove if quantity is 0
        c.execute("DELETE FROM user_boxes WHERE user_id = ? AND box_type = ? AND quantity <= 0", (user_id, box_type))
        self.conn.commit()
    
    # City Building Methods
    def get_user_buildings(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM city_buildings WHERE user_id = ?", (user_id,))
        results = c.fetchall()
        return [dict(row) for row in results]
    
    def get_user_building(self, user_id, building_type):
        c = self.conn.cursor()
        c.execute("SELECT * FROM city_buildings WHERE user_id = ? AND building_type = ?", (user_id, building_type))
        result = c.fetchone()
        return dict(result) if result else None
    
    def upgrade_building(self, user_id, building_type, new_level):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO city_buildings (user_id, building_type, level) VALUES (?, ?, ?)",
                 (user_id, building_type, new_level))
        self.conn.commit()
    
    def update_building_collection(self, user_id, building_type):
        now = datetime.datetime.now().isoformat()
        c = self.conn.cursor()
        c.execute("UPDATE city_buildings SET last_collected = ? WHERE user_id = ? AND building_type = ?",
                 (now, user_id, building_type))
        self.conn.commit()
    
    # Mystery Box Inventory Methods
    def get_user_mystery_boxes(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT quantity FROM user_mystery_boxes WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        return result[0] if result else 0
    
    def add_mystery_box(self, user_id, quantity=1):
        c = self.conn.cursor()
        current = self.get_user_mystery_boxes(user_id)
        c.execute("INSERT OR REPLACE INTO user_mystery_boxes (user_id, quantity) VALUES (?, ?)",
                 (user_id, current + quantity))
        self.conn.commit()
    
    def remove_mystery_box(self, user_id, quantity=1):
        current = self.get_user_mystery_boxes(user_id)
        if current >= quantity:
            c = self.conn.cursor()
            c.execute("UPDATE user_mystery_boxes SET quantity = quantity - ? WHERE user_id = ?",
                     (quantity, user_id))
            self.conn.commit()
            return True
        return False
    
    # Sauce System Methods
    def update_user_bling(self, user_id, amount):
        self.create_user(user_id)
        c = self.conn.cursor()
        c.execute("UPDATE users SET bling = bling + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def update_user_stricks(self, user_id, amount):
        self.create_user(user_id)
        c = self.conn.cursor()
        c.execute("UPDATE users SET stricks = stricks + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def set_last_income_claim(self, user_id, amount=0):
        now = datetime.datetime.now().isoformat()
        c = self.conn.cursor()
        c.execute("UPDATE users SET last_income_claim = ?, last_income_amount = ? WHERE user_id = ?", (now, amount, user_id))
        self.conn.commit()

    def get_last_income_claim(self, user_id):
        user = self.get_user(user_id)
        return user.get('last_income_claim') if user else None
    
    def reset_monthly_stricks(self):
        # Reset stricks for users who earned enough bling this month
        c = self.conn.cursor()
        c.execute("UPDATE users SET stricks = 0 WHERE bling >= 200")
        # Reset bling for all sauce users
        c.execute("UPDATE users SET bling = 0")
        self.conn.commit()

# Initialize database
db = BotDatabase()
init_db()

# Active pop-up questions and Starr drops
active_popups = {}
active_starr_drops = {}

# NEW: Guess Number Game
active_guess_games = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    starr_drop_spawner.start()
    weekly_reset.start()
    cleanup_tasks.start()
    popup_spawner.start()
    golden_pass_reset.start()
    event_cleanup.start()
    sauce_monthly_reset.start() 
    guess_game_cleanup.start()
    sugarrush_cleanup.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild:
        server_activity[str(message.guild.id)] = datetime.datetime.now()
    
    # Track commands used
    if message.content.startswith('-'):
        db.create_user(message.author.id)
        c = db.conn.cursor()
        c.execute("UPDATE users SET commands_used = commands_used + 1 WHERE user_id = ?", (message.author.id,))
        db.conn.commit()
    
    # Handle XP gain - FIXED: Now server-specific
    old_level = await get_user_level(message.author.id, message.guild.id)
    await handle_xp_gain(message)
    new_level = await get_user_level(message.author.id, message.guild.id)
    
    # Check for level up
    if new_level > old_level:
        # Define the levels that give mystery boxes
        MYSTERY_BOX_LEVELS = [5, 10, 20, 35, 50, 75, 100]
    
        # Check level roles - FIXED: Properly handle the database query
        level_roles = None
        try:
            c = db.conn.cursor()
            level_roles = c.execute(
                "SELECT role_id FROM level_roles WHERE guild_id = ? AND level = ?", 
                (message.guild.id, new_level)
            ).fetchone()
        except Exception as e:
            print(f"Error checking level roles: {e}")
            level_roles = None
    
        role_mention = ""
        if level_roles:
            role = message.guild.get_role(level_roles[0])
            if role:
                role_mention = f" You've unlocked a new milestone role!"
    
        # Check if this level qualifies for a mystery box
        qualifies_for_box = new_level in MYSTERY_BOX_LEVELS
    
        # Send level up message
        if qualifies_for_box and not db.has_claimed_mystery_box(message.author.id, new_level):
            # FIX: Actually give the mystery box and mark as claimed
            db.add_box_to_user(message.author.id, 'mystery_box')
            db.add_mystery_claim(message.author.id, new_level)
        
            await message.channel.send(
                f"{EMOJIS['levelup']} **Level Up!** {message.author.mention} reached **Level {new_level}**!{role_mention}\n"
                f"{EMOJIS['mysterybox']} You've earned a Mystery Box! Use `-openbox mystery` to open it!"
            )
        else:
            await message.channel.send(
                f"{EMOJIS['levelup']} **Level Up!** {message.author.mention} reached **Level {new_level}**!{role_mention}"
            )
    
        # Handle Golden XP gain
    old_golden_level = await get_user_golden_level(message.author.id)
    await handle_golden_xp_gain(message)
    new_golden_level = await get_user_golden_level(message.author.id)
    
    # Check for golden tier up
    if new_golden_level > old_golden_level:
        await handle_golden_pass_reward(message.author, new_golden_level)
    
    # Handle pop-up responses (both user-specific and channel pop-ups)
    if message.author.id in active_popups:
        await handle_popup_response(message)
    
    # Handle channel pop-ups
    await handle_channel_popup_response(message)
    
    # Handle guess number game responses
    await handle_guess_game_response(message)
    
    # Check badges every 10 messages (to reduce load)
    if random.random() < 0.1:
        await check_badge_achievements(message.author.id)
    
    await bot.process_commands(message)

# FIXED: Server-specific level calculation
async def get_user_level(user_id, guild_id):
    xp = db.get_server_user_xp(user_id, guild_id)
    level, _, _ = calculate_level(xp)
    return level

async def get_user_golden_level(user_id):
    user_data = db.get_user(user_id)
    if not user_data:
        return 0
    # FIXED: Use golden_xp instead of golden_level
    level, _, _ = calculate_golden_level(user_data['golden_xp'])
    return level

# FIXED: Server-specific XP handling
async def handle_xp_gain(message):
    xp_gained = 10
    boost_multiplier = 1
    
    # Check for boost roles
    guild_config = db.get_server_config(message.guild.id)
    
    if guild_config:
        try:
            guild = message.guild
            member = guild.get_member(message.author.id)
            
            # Check boost roles with different multipliers
            if guild_config.get('boost3_role'):
                boost_role = guild.get_role(guild_config['boost3_role'])
                if boost_role and boost_role in member.roles:
                    boost_multiplier = 3.0
            elif guild_config.get('boost2_role'):
                boost_role = guild.get_role(guild_config['boost2_role'])
                if boost_role and boost_role in member.roles:
                    boost_multiplier = 2.5
            elif guild_config.get('boost1_role'):
                boost_role = guild.get_role(guild_config['boost1_role'])
                if boost_role and boost_role in member.roles:
                    boost_multiplier = 2.0
                    
        except:
            pass
    
    # Check for art or clip channels
    if guild_config:
        if message.channel.id == guild_config.get('art_channel'):
            xp_gained = 200
        elif message.channel.id == guild_config.get('clip_channel'):
            xp_gained = 100
    
    # Apply event multipliers
    active_events = db.get_active_events(message.guild.id)
    for event in active_events:
        if event['event_type'] == 'double_xp':
            xp_gained *= event['multiplier']
    
    xp_gained = int(xp_gained * boost_multiplier)
    db.update_server_user_xp(message.author.id, message.guild.id, xp_gained)
    
    # Track messages for stats
    db.create_user(message.author.id)
    c = db.conn.cursor()
    c.execute("UPDATE users SET total_messages = total_messages + 1 WHERE user_id = ?", (message.author.id,))
    db.conn.commit()

async def handle_golden_xp_gain(message):
    # Golden XP from messages (low amount)
    golden_xp_gained = 2
    
    # Update daily quest progress for sending messages (only if not completed)
    quests = db.get_daily_quests(message.author.id)
    if quests and quests['quest2_progress'] < 3 and quests['quest2_progress'] < 1000:
        new_progress = min(quests['quest2_progress'] + 1, 3)
        db.update_daily_quest(message.author.id, 'quest2_progress', new_progress)
    
    db.create_user(message.author.id)
    c = db.conn.cursor()
    c.execute("UPDATE users SET golden_xp = golden_xp + ? WHERE user_id = ?", (golden_xp_gained, message.author.id))
    db.conn.commit()

async def handle_golden_pass_reward(user, new_tier):
    # Determine user's boost tier
    boost_tier = 'free'
    guild_config = db.get_server_config(user.guild.id)
    
    if guild_config:
        member = user.guild.get_member(user.id)
        if guild_config.get('boost3_role'):
            boost_role = user.guild.get_role(guild_config['boost3_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost3'
        elif guild_config.get('boost2_role'):
            boost_role = user.guild.get_role(guild_config['boost2_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost2'
        elif guild_config.get('boost1_role'):
            boost_role = user.guild.get_role(guild_config['boost1_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost1'
    
    # Get rewards for this tier
    rewards = get_golden_pass_rewards(boost_tier, new_tier)
    
    # Apply rewards
    for currency, amount in rewards.items():
        if amount > 0:  # Only update if amount is positive
            db.update_user_currency(user.id, currency, amount)
    
    # Send reward message to announcement channel if set, otherwise use system channel
    announcement_channel = None
    if guild_config and guild_config.get('announcement_channel'):
        announcement_channel = user.guild.get_channel(guild_config['announcement_channel'])
    
    if not announcement_channel:
        announcement_channel = user.guild.system_channel or user.guild.text_channels[0]
    
    embed = discord.Embed(
        title=f"{EMOJIS['goldenxp']} NEW TIER REACHED! {EMOJIS['pass']}",
        description=f"**{user.display_name}** advanced to **Tier {new_tier}** in the Golden Pass!",
        color=0xffd700
    )
    
    reward_text = "\n".join([f"{EMOJIS[currency]} {amount} {currency.capitalize()}" 
                           for currency, amount in rewards.items() if amount > 0])
    embed.add_field(
        name="🎁 REWARDS RECEIVED",
        value=reward_text,
        inline=False
    )
    
    await announcement_channel.send(embed=embed)

# UPDATED: Pop-up response handler - 1% chance for mystery box instead of artifacts
async def handle_popup_response(message):
    popup_data = active_popups.get(message.author.id)
    if not popup_data:
        return
    
    # Check if popup expired
    if datetime.datetime.now() > popup_data['expires']:
        del active_popups[message.author.id]
        await message.channel.send("⏰ Time's up! The pop-up question has expired.")
        return
    
    user_answer = message.content.lower().strip()
    correct_answer = popup_data['answer'].lower().strip()
    
    if user_answer == correct_answer:
        # Give XP reward (increased to 500)
        db.update_server_user_xp(message.author.id, message.guild.id, 500)
        
        # 1% chance for mystery box (replaced 20% artifact chance)
        if random.random() < 0.01:
            db.add_box_to_user(message.author.id, 'mystery_box')
            await message.channel.send(
                f"{EMOJIS['pop']} **POP-UP COMPLETED!** {EMOJIS['pop']}\n"
                f"🎉 Correct! You earned 500 XP and found a **Mystery Box**! Use `-openbox mystery` to open it!"
            )
        else:
            await message.channel.send(
                f"{EMOJIS['pop']} **POP-UP COMPLETED!** {EMOJIS['pop']}\n"
                f"🎉 Correct! You earned 500 XP!"
            )
    else:
        await message.channel.send("❌ Wrong answer! Better luck next time.")
    
    del active_popups[message.author.id]

# UPDATED: Channel pop-up response handler - 1% chance for mystery box instead of artifacts
async def handle_channel_popup_response(message):
    """Handle responses to channel-wide pop-up questions"""
    popup_data = bot.active_channel_popups.get(message.channel.id)
    
    if not popup_data or popup_data['claimed']:
        return
    
    # Check if popup expired
    if datetime.datetime.now() > popup_data['expires']:
        del bot.active_channel_popups[message.channel.id]
        await message.channel.send("⏰ Time's up! The pop-up question has expired.")
        return
    
    user_answer = message.content.lower().strip()
    correct_answer = popup_data['answer'].lower().strip()
    
# Updated reward system for pop-ups
    if popup_type == 'free_xp' or user_answer == correct_answer:
        # Give XP reward
        db.update_server_user_xp(message.author.id, message.guild.id, 500)
    
        # New reward system - replaced 1% mystery box
        reward_roll = random.random() * 100
        reward_message = ""
    
        if reward_roll < 5:  # 5% chance for emerald
            db.update_user_currency(message.author.id, 'emerald', 1)
            reward_message = f"{EMOJIS['emerald']} **1 Emerald**"
        elif reward_roll < 10:  # 5% chance for magic key
            c = db.conn.cursor()
            c.execute("UPDATE users SET magic_keys = magic_keys + 1 WHERE user_id = ?", (message.author.id,))
            db.conn.commit()
            reward_message = f"{EMOJIS['magic_key']} **1 Magic Key**"
        elif reward_roll < 15:  # 5% chance for silver
            db.update_user_currency(message.author.id, 'silver', 200)
            reward_message = f"{EMOJIS['silver']} **200 Silver**"
        else:
            reward_message = "500 XP"
    
        if popup_type == 'free_xp':
            await message.channel.send(
                f"{EMOJIS['pop']} **POP-UP COMPLETED!** {EMOJIS['pop']}\n"
                f"🎉 {message.author.mention} claimed their reward: {reward_message}!"
            )
        else:
            await message.channel.send(
                f"{EMOJIS['pop']} **POP-UP COMPLETED!** {EMOJIS['pop']}\n"
                f"🎉 {message.author.mention} answered correctly and earned {reward_message}!"
            )
        
        # Mark as claimed
        popup_data['claimed'] = True
        del bot.active_channel_popups[message.channel.id]
    else:
        # Wrong answer - send error message
        await message.channel.send(f"❌ {message.author.mention} That's incorrect! Try again!", delete_after=5)

# NEW: Guess Number Game handler
async def handle_guess_game_response(message):
    """Handle responses to guess number games"""
    game_data = active_guess_games.get(message.channel.id)
    
    if not game_data or game_data['claimed']:
        return
    
    # Check if game expired
    if datetime.datetime.now() > game_data['expires']:
        del active_guess_games[message.channel.id]
        await message.channel.send("⏰ Time's up! The guess number game has expired.")
        return
    
    # Track guesses
    if 'guesses' not in game_data:
        game_data['guesses'] = {}
    
    user_id = message.author.id
    if user_id not in game_data['guesses']:
        game_data['guesses'][user_id] = 0
    
    # Check if user has exceeded maximum guesses
    if game_data['guesses'][user_id] >= 4:
        await message.channel.send(f"❌ {message.author.mention} You've used all 4 guesses!", delete_after=5)
        return
    
    try:
        user_guess = int(message.content.strip())
    except ValueError:
        return  # Not a number
    
    # Increment guess count
    game_data['guesses'][user_id] += 1
    
    target_number = game_data['number']
    
    if user_guess == target_number:
        # Give rewards to the winner
        xp_reward = 200
        # Random reward from the specified options
        reward_options = [
            {'type': 'silver', 'amount': 20},
            {'type': 'gold', 'amount': 2},
            {'type': 'iron', 'amount': random.randint(50, 60)},
            {'type': 'copper', 'amount': random.randint(60, 80)},
            {'type': 'stone', 'amount': 200},
            {'type': 'planks', 'amount': 2000}
        ]
        reward = random.choice(reward_options)
        
        db.update_server_user_xp(message.author.id, message.guild.id, xp_reward)
        db.update_user_currency(message.author.id, reward['type'], reward['amount'])
        
        await message.channel.send(
            f"🎉 **CORRECT!** {message.author.mention} guessed the number **{target_number}**!\n"
            f"🏆 Rewards: {xp_reward} XP + {reward['amount']} {reward['type'].capitalize()}!"
        )
        
        # Mark as claimed
        game_data['claimed'] = True
        del active_guess_games[message.channel.id]
    else:
        # Give hint
        hint = "🔻 Too low!" if user_guess < target_number else "🔺 Too high!"
        guesses_left = 4 - game_data['guesses'][user_id]
        await message.channel.send(f"{hint} {guesses_left} guesses left {message.author.mention}!", delete_after=5)

def get_random_artifact():
    rand = random.random() * 100
    cumulative = 0
    for artifact, chance in ARTIFACTS.items():
        cumulative += chance
        if rand <= cumulative:
            return artifact
    return "10 Silver"  # Fallback

async def add_artifact_to_user(user_id, artifact_name):
    if artifact_name == "10 Silver":
        db.update_user_currency(user_id, 'silver', 10)
    else:
        c = db.conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO user_artifacts (user_id, artifact_name, rarity) VALUES (?, ?, ?)",
            (user_id, artifact_name, 'Artifact')
        )
        db.conn.commit()

def process_box_reward(reward, user_id, sugarrush_active=False):
    """Process a box reward and return the display text"""
    try:
        # Add Sugar Rush emoji if active
        sugar_emoji = " 🍬" if sugarrush_active else ""
        
        if 'Planks' in reward:
            amount = int(reward.split()[0])
            db.update_user_currency(user_id, 'planks', amount)
            return f"{EMOJIS['planks']} {reward}{sugar_emoji}"
        elif 'Stone' in reward:
            amount = int(reward.split()[0])
            db.update_user_currency(user_id, 'stone', amount)
            return f"{EMOJIS['stone']} {reward}{sugar_emoji}"
        elif 'Iron' in reward:
            amount = int(reward.split()[0])
            db.update_user_currency(user_id, 'iron', amount)
            return f"{EMOJIS['iron']} {reward}{sugar_emoji}"
        elif 'Silver' in reward:
            amount = int(reward.split()[0])
            db.update_user_currency(user_id, 'silver', amount)
            return f"{EMOJIS['silver']} {reward}{sugar_emoji}"
        elif 'Gold' in reward:
            amount = int(reward.split()[0])
            db.update_user_currency(user_id, 'gold', amount)
            return f"{EMOJIS['gold']} {reward}{sugar_emoji}"
        elif 'Diamond' in reward:
            amount = int(reward.split()[0])
            db.update_user_currency(user_id, 'diamonds', amount)
            return f"{EMOJIS['diamonds']} {reward}{sugar_emoji}"
        elif 'Copper' in reward:
            amount = int(reward.split()[0])
            db.update_user_currency(user_id, 'copper', amount)
            return f"{EMOJIS['copper']} {reward}{sugar_emoji}"
        elif 'Emerald' in reward:
            amount = int(reward.split()[0])
            db.update_user_currency(user_id, 'emerald', amount)
            return f"{EMOJIS['emerald']} {reward}{sugar_emoji}"
        
        # For non-numeric rewards (Mystery Box, Magic Key, Ultra Box), just add the emoji
        elif 'Mystery Box' in reward:
            db.add_box_to_user(user_id, 'mystery_box')
            return f"{EMOJIS['mysterybox']} Mystery Box{sugar_emoji}"
        elif 'Magic Key' in reward:
            c = db.conn.cursor()
            c.execute("UPDATE users SET magic_keys = magic_keys + 1 WHERE user_id = ?", (user_id,))
            db.conn.commit()
            return f"{EMOJIS['magic_key']} Magic Key{sugar_emoji}"
        elif 'Ultra Box' in reward:
            db.add_box_to_user(user_id, 'ultra_box')
            return f"{EMOJIS['ultra_box']} Ultra Box{sugar_emoji}"
        
        return f"❓ {reward}"
    except Exception as e:
        print(f"Error processing reward '{reward}': {e}")
        return f"❌ Error"

# FIXED: Box opening with buttons - IMPROVED: Fixed the field value length issue
class BoxOpenView(discord.ui.View):
    def __init__(self, ctx, box_type, box_name, draws):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.box_type = box_type
        self.box_name = box_name
        self.draws = draws
        self.opened = False
    
    @discord.ui.button(label='Open', style=discord.ButtonStyle.green, emoji='🎁')
    async def open_box(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your box to open!", ephemeral=True)
            return
        
        if self.opened:
            await interaction.response.send_message("You already opened this box!", ephemeral=True)
            return
        
        self.opened = True
        button.disabled = True
        
        # Check for Sugar Rush activation
        user_data = db.get_user(self.ctx.author.id)
        sugarrush_active = False
        if user_data and user_data['sugarrush_active']:
            expires_time = datetime.datetime.fromisoformat(user_data['sugarrush_expires'])
            if datetime.datetime.now() < expires_time:
                sugarrush_active = True
        
        # Process box rewards with Sugar Rush multiplier
        rewards = []
        
        for _ in range(self.draws):
            try:
                reward = get_box_reward()
                
                # Apply Sugar Rush multiplier if active
                if sugarrush_active and any(char.isdigit() for char in reward):
                    # Triple the numeric amount in the reward
                    parts = reward.split()
                    if len(parts) >= 2 and parts[0].isdigit():
                        original_amount = int(parts[0])
                        tripled_amount = original_amount * 3
                        reward = f"{tripled_amount} {parts[1]}"
                
                display_text = process_box_reward(reward, self.ctx.author.id, sugarrush_active)
                rewards.append(display_text)
                
            except Exception as e:
                print(f"Error processing reward: {e}")
                rewards.append("❌ Error")
        
        # Update daily quest progress
        quests = db.get_daily_quests(self.ctx.author.id)
        if quests and quests['quest1_progress'] < 10:
            new_progress = min(quests['quest1_progress'] + 1, 10)
            db.update_daily_quest(self.ctx.author.id, 'quest1_progress', new_progress)
        
        # Track boxes opened
        c = db.conn.cursor()
        c.execute("UPDATE users SET total_boxes_opened = total_boxes_opened + 1 WHERE user_id = ?", (self.ctx.author.id,))
        db.conn.commit()
        
        # Create reward display
        embed = discord.Embed(
            title=f"🎁 {self.box_name.upper()} REWARDS 🎁",
            description=f"You got {self.draws} rewards:" + (" 🍬 **SUGAR RUSH ACTIVE!**" if sugarrush_active else ""),
            color=0xff69b4
        )
        
        # FIXED: Split rewards into multiple fields if the text is too long
        reward_text = "\n".join([f"• {reward}" for reward in rewards])
        
        # If the reward text is too long, split it into multiple fields
        if len(reward_text) > 1024:
            # Split into chunks of max 1024 characters
            chunks = []
            current_chunk = ""
            
            for reward_line in rewards:
                reward_display = f"• {reward_line}"
                if len(current_chunk) + len(reward_display) + 2 > 1024:
                    chunks.append(current_chunk)
                    current_chunk = reward_display
                else:
                    if current_chunk:
                        current_chunk += f"\n{reward_display}"
                    else:
                        current_chunk = reward_display
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # Add each chunk as a separate field
            for i, chunk in enumerate(chunks):
                embed.add_field(
                    name=f"Rewards Part {i+1}" if i > 0 else "Rewards",
                    value=chunk,
                    inline=False
                )
        else:
            embed.add_field(name="Rewards", value=reward_text, inline=False)
        
        # FIXED: Properly update the message
        await interaction.response.edit_message(embed=embed, view=self)

# UPDATED: Box command with button interface
@bot.command()
@commands.cooldown(1, 3, commands.BucketType.user)
async def box(ctx):
    try:
        # Simple cooldown check
        current_time = datetime.datetime.now()
        
        if hasattr(bot, 'last_box_usage'):
            if ctx.author.id in bot.last_box_usage:
                last_use = bot.last_box_usage[ctx.author.id]
                time_diff = (current_time - last_use).total_seconds()
                if time_diff < 3:
                    await ctx.send(f"⏰ Please wait {3 - int(time_diff)} seconds before using this command again!")
                    return
        
        if not hasattr(bot, 'last_box_usage'):
            bot.last_box_usage = {}
        
        bot.last_box_usage[ctx.author.id] = current_time
        
        # Box type distribution
        box_roll = random.random() * 100
        if box_roll < 50:
            box_name = "Small Box"
            box_type = "small_box"
            draws = 2
            chance = "50%"
        elif box_roll < 75:
            box_name = "Regular Box" 
            box_type = "regular_box"
            draws = 4
            chance = "25%"
        elif box_roll < 90:
            box_name = "Big Box"
            box_type = "big_box"
            draws = 7
            chance = "15%"
        elif box_roll < 95:
            box_name = "Mega Box"
            box_type = "mega_box"
            draws = 10
            chance = "5%"
        elif box_roll < 99:
            box_name = "Omega Box"
            box_type = "omega_box"
            draws = 20
            chance = "1%"
        else:
            box_name = "Ultra Box"
            box_type = "ultra_box"
            draws = 35
            chance = "0.1%"
        
        # Create embed with box image
        embed = discord.Embed(
            title=f"📦 {box_name.upper()} 📦",
            description=f"Click the button below to open your {box_name}!",
            color=0xff69b4
        )
        embed.add_field(
            name="Box Info",
            value=f"**Type:** {box_name}\n**Chance:** {chance}\n**Draws:** {draws}",
            inline=True
        )
        embed.set_image(url=BOX_IMAGES[box_type])
        
        view = BoxOpenView(ctx, box_type, box_name, draws)
        await ctx.send(embed=embed, view=view)
        
    except Exception as e:
        print(f"CRITICAL Box command error: {e}")
        import traceback
        traceback.print_exc()
        await ctx.send("🎁 **Box Opened!** (System recovered)")

@box.error
async def box_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"{EMOJIS['alert']} Please wait {error.retry_after:.1f} seconds before using this command again!")

# FIXED: SpecificBoxOpenView with improved error handling
class SpecificBoxOpenView(discord.ui.View):
    def __init__(self, ctx, box_type, box_name, draws):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.box_type = box_type
        self.box_name = box_name
        self.draws = draws
        self.opened = False
    
    @discord.ui.button(label='Open', style=discord.ButtonStyle.green, emoji='🎁')
    async def open_box(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your box to open!", ephemeral=True)
            return
        
        if self.opened:
            await interaction.response.send_message("You already opened this box!", ephemeral=True)
            return
        
        self.opened = True
        button.disabled = True
        
        # Check for Sugar Rush activation
        user_data = db.get_user(self.ctx.author.id)
        sugarrush_active = False
        if user_data and user_data['sugarrush_active']:
            expires_time = datetime.datetime.fromisoformat(user_data['sugarrush_expires'])
            if datetime.datetime.now() < expires_time:
                sugarrush_active = True
        
        # Process box rewards with Sugar Rush multiplier
        rewards = []
        
        for _ in range(self.draws):
            try:
                reward = get_box_reward()
                
                # Apply Sugar Rush multiplier if active
                if sugarrush_active and any(char.isdigit() for char in reward):
                    # Triple the numeric amount in the reward
                    parts = reward.split()
                    if len(parts) >= 2 and parts[0].isdigit():
                        original_amount = int(parts[0])
                        tripled_amount = original_amount * 3
                        reward = f"{tripled_amount} {parts[1]}"
                
                display_text = process_box_reward(reward, self.ctx.author.id, sugarrush_active)
                rewards.append(display_text)
            except Exception as e:
                print(f"Error processing reward: {e}")
                rewards.append("❌ Error")
        
        # Create reward display with emojis - FIXED: Split into multiple fields if too long
        embed = discord.Embed(
            title=f"🎁 {self.box_name.upper()} REWARDS 🎁",
            description=f"You got {self.draws} rewards:" + (" 🍬 **SUGAR RUSH ACTIVE!**" if sugarrush_active else ""),
            color=0xff69b4
        )
        
        # FIXED: Split rewards into multiple fields if the text is too long
        reward_text = "\n".join([f"• {reward}" for reward in rewards])
        
        # If the reward text is too long, split it into multiple fields
        if len(reward_text) > 1024:
            # Split into chunks of max 1024 characters
            chunks = []
            current_chunk = ""
            
            for reward_line in rewards:
                reward_display = f"• {reward_line}"
                if len(current_chunk) + len(reward_display) + 2 > 1024:
                    chunks.append(current_chunk)
                    current_chunk = reward_display
                else:
                    if current_chunk:
                        current_chunk += f"\n{reward_display}"
                    else:
                        current_chunk = reward_display
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # Add each chunk as a separate field
            for i, chunk in enumerate(chunks):
                embed.add_field(
                    name=f"Rewards Part {i+1}" if i > 0 else "Rewards",
                    value=chunk,
                    inline=False
                )
        else:
            embed.add_field(name="Rewards", value=reward_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)

# NEW: Mystery Box View with button interface
class MysteryBoxView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.opened = False
    
    @discord.ui.button(label='Open', style=discord.ButtonStyle.green, emoji=EMOJIS['mysterybox'])
    async def open_box(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your mystery box to open!", ephemeral=True)
            return
        
        if self.opened:
            await interaction.response.send_message("You already opened this mystery box!", ephemeral=True)
            return
        
        self.opened = True
        button.disabled = True
        
        # Get mystery box reward
        reward = get_mystery_box_reward()
        
        embed = discord.Embed(
            title=f"{EMOJIS['mysterybox']} MYSTERY BOX OPENED! {EMOJIS['mysterybox']}",
            description=f"You opened your Mystery Box!",
            color=0x9b59b6
        )
        
        if reward['type'] == 'ultra_box_diamonds':
            db.add_box_to_user(self.ctx.author.id, 'ultra_box', reward['ultra_boxes'])
            db.update_user_currency(self.ctx.author.id, 'diamonds', reward['diamonds'])
            embed.add_field(
                name="🎁 Rewards", 
                value=f"{EMOJIS['ultra_box']} {reward['ultra_boxes']} Ultra Box + {EMOJIS['diamonds']} {reward['diamonds']} Diamonds", 
                inline=False
            )
        
        elif reward['type'] == 'character':
            char_name = reward['character']
            char_rarity = reward['rarity']
            c = db.conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO user_characters (user_id, character_name, rarity) VALUES (?, ?, ?)",
                (self.ctx.author.id, char_name, char_rarity)
            )
            db.conn.commit()
            embed.add_field(
                name="🎭 CHARACTER UNLOCKED!",
                value=f"**{char_name}** ({char_rarity})\n{CHARACTERS[char_name]['description']}",
                inline=False
            )
        
        elif reward['type'] == 'gold':
            db.update_user_currency(self.ctx.author.id, 'gold', reward['amount'])
            embed.add_field(name="🎁 Rewards", value=f"{EMOJIS['gold']} {reward['amount']} Gold", inline=False)
        
        elif reward['type'] == 'diamonds':
            db.update_user_currency(self.ctx.author.id, 'diamonds', reward['amount'])
            embed.add_field(name="🎁 Rewards", value=f"{EMOJIS['diamonds']} {reward['amount']} Diamonds", inline=False)
        
        elif reward['type'] == 'iron':
            db.update_user_currency(self.ctx.author.id, 'iron', reward['amount'])
            embed.add_field(name="🎁 Rewards", value=f"{EMOJIS['iron']} {reward['amount']} Iron", inline=False)
        
        elif reward['type'] == 'magic_key':
            c = db.conn.cursor()
            c.execute("UPDATE users SET magic_keys = magic_keys + ? WHERE user_id = ?", (reward['amount'], self.ctx.author.id))
            db.conn.commit()
            embed.add_field(name="🎁 Rewards", value=f"{EMOJIS['magic_key']} {reward['amount']} Magic Key", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)

# NEW: Artifact Box View
class ArtifactBoxView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.unlocked = False
    
    @discord.ui.button(label='Unlock', style=discord.ButtonStyle.green, emoji=EMOJIS['artifact_box'])
    async def unlock_box(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your artifact box to unlock!", ephemeral=True)
            return
        
        if self.unlocked:
            await interaction.response.send_message("You already unlocked this artifact box!", ephemeral=True)
            return
        
        # Check if user has enough resources
        user_data = db.get_user(self.ctx.author.id)
        if not user_data:
            db.create_user(self.ctx.author.id)
            user_data = db.get_user(self.ctx.author.id)
        
        if user_data['copper'] < 1000:
            await interaction.response.send_message(
                f"{EMOJIS['alert']} You need 1000 {EMOJIS['copper']} Copper to unlock an artifact box! You only have {user_data['copper']}.",
                ephemeral=True
            )
            return
        
        if user_data['magic_keys'] < 1:
            await interaction.response.send_message(
                f"{EMOJIS['alert']} You need 1 {EMOJIS['magic_key']} Magic Key to unlock an artifact box! You have {user_data['magic_keys']}.",
                ephemeral=True
            )
            return
        
        # Deduct resources
        db.update_user_currency(self.ctx.author.id, 'copper', -1000)
        c = db.conn.cursor()
        c.execute("UPDATE users SET magic_keys = magic_keys - 1 WHERE user_id = ?", (self.ctx.author.id,))
        db.conn.commit()
        
        self.unlocked = True
        button.disabled = True
        
        # Get artifacts (1 or 2 artifacts)
        num_artifacts = random.choice([1, 2])
        artifacts = [get_random_artifact() for _ in range(num_artifacts)]
        
        # Add artifacts to user
        for artifact in artifacts:
            if artifact != "10 Silver":
                await add_artifact_to_user(self.ctx.author.id, artifact)
            else:
                db.update_user_currency(self.ctx.author.id, 'silver', 10)
        
        embed = discord.Embed(
            title=f"{EMOJIS['artifact_box']} ARTIFACT BOX UNLOCKED! {EMOJIS['artifact_box']}",
            description=f"You unlocked an artifact box and found {num_artifacts} artifact(s)!",
            color=0x9b59b6
        )
        
        artifact_names = ", ".join([f"**{a}**" for a in artifacts])
        embed.add_field(name="🎁 Artifacts Found", value=artifact_names, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)

# NEW: Artifacts Box Command
@bot.command()
async def artifactsbox(ctx):
    """Unlock an artifact box with 1000 copper and 1 magic key"""
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    embed = discord.Embed(
        title=f"{EMOJIS['artifact_box']} ARTIFACT BOX {EMOJIS['artifact_box']}",
        description="Unlock this special box to get 1-2 artifacts!",
        color=0x9b59b6
    )
    
    embed.add_field(
        name="Requirements",
        value=f"{EMOJIS['copper']} 1000 Copper\n{EMOJIS['magic_key']} 1 Magic Key",
        inline=False
    )
    
    embed.add_field(
        name="Your Resources",
        value=f"{EMOJIS['copper']} Copper: {user_data['copper']}\n{EMOJIS['magic_key']} Magic Keys: {user_data['magic_keys']}",
        inline=False
    )
    
    embed.add_field(
        name="Reward",
        value="Guaranteed 1-2 artifacts from the artifact pool!",
        inline=False
    )
    
    embed.set_image(url=BOX_IMAGES['artifact_box'])
    
    view = ArtifactBoxView(ctx)
    await ctx.send(embed=embed, view=view)

# UPDATED: Openbox command with buttons - FIXED: Mystery box integration with new rewards
@bot.command()
async def openbox(ctx, box_type: str = None):
    if not box_type:
        # Show user's boxes
        user_boxes = db.get_user_boxes(ctx.author.id)
        if not user_boxes:
            await ctx.send(f"{EMOJIS['alert']} You don't have any boxes! Use `-daily` or `-weekly` to get some.")
            return
        
        embed = discord.Embed(
            title=f"📦 YOUR BOXES 📦",
            description="Use `-openbox <type>` to open a specific box",
            color=0x7289da
        )
        
        for box_type_db, quantity in user_boxes:
            display_name = box_type_db.replace('_', ' ').title()
            box_emoji = EMOJIS.get(box_type_db, '📦')
            embed.add_field(
                name=f"{box_emoji} {display_name}",
                value=f"Quantity: {quantity}",
                inline=True
            )
        
        await ctx.send(embed=embed)
        return
    
    # Normalize box type input
    box_type = box_type.lower().replace(' ', '_')
    if not box_type.endswith('_box'):
        box_type = f"{box_type}_box"
    
    # Check if user has the box
    user_boxes = dict(db.get_user_boxes(ctx.author.id))
    
    if box_type not in user_boxes:
        await ctx.send(f"{EMOJIS['alert']} You don't have any {box_type.replace('_', ' ').title()} boxes!")
        return
    
    # Remove box from user
    db.remove_box_from_user(ctx.author.id, box_type)
    
    # Determine box properties
    if box_type == 'small_box':
        draws = 2
        box_name = "Small Box"
    elif box_type == 'regular_box':
        draws = 4
        box_name = "Regular Box"
    elif box_type == 'big_box':
        draws = 7
        box_name = "Big Box"
    elif box_type == 'mega_box':
        draws = 10
        box_name = "Mega Box"
    elif box_type == 'omega_box':
        draws = 20
        box_name = "Omega Box"
    elif box_type == 'ultra_box':
        draws = 35
        box_name = "Ultra Box"
    elif box_type == 'mystery_box':
        # FIXED: Handle mystery box with button interface
        embed = discord.Embed(
            title=f"{EMOJIS['mysterybox']} MYSTERY BOX {EMOJIS['mysterybox']}",
            description="Click the button below to open your Mystery Box!",
            color=0x9b59b6
        )
        embed.add_field(
            name="Box Info",
            value="**Type:** Mystery Box\n**Reward:** Special ultra-rare items!",
            inline=True
        )
        embed.set_image(url=BOX_IMAGES['mystery_box'])
        
        view = MysteryBoxView(ctx)
        await ctx.send(embed=embed, view=view)
        return
        
    elif box_type == 'artifact_box':
        # Show artifact box interface
        await ctx.invoke(bot.get_command('artifactsbox'))
        return
    else:
        await ctx.send(f"{EMOJIS['alert']} Unknown box type!")
        return
    
    # Create embed with box image
    embed = discord.Embed(
        title=f"📦 {box_name.upper()} 📦",
        description=f"Click the button below to open your {box_name}!",
        color=0xff69b4
    )
    embed.add_field(
        name="Box Info",
        value=f"**Type:** {box_name}\n**Draws:** {draws}",
        inline=True
    )
    embed.set_image(url=BOX_IMAGES[box_type])
    
    view = SpecificBoxOpenView(ctx, box_type, box_name, draws)
    await ctx.send(embed=embed, view=view)

# UPDATED: Income command with new tier system 1-7
@bot.command()
async def income(ctx, income_tier: str = None):
    # Check if user has sauce role
    guild_config = db.get_server_config(ctx.guild.id)
    if not guild_config or not guild_config.get('sauce_role'):
        await ctx.send(f"{EMOJIS['alert']} Sauce system is not configured on this server!")
        return
    
    sauce_role = ctx.guild.get_role(guild_config['sauce_role'])
    if not sauce_role or sauce_role not in ctx.author.roles:
        await ctx.send(f"{EMOJIS['alert']} You do not own a sauce role to use this command!")
        return
    
    # Check if user is blocked from earning bling
    user_data = db.get_user(ctx.author.id)
    if user_data and user_data['stricks'] >= 3:
        await ctx.send(f"{EMOJIS['alert']} You have 3 stricks and can no longer earn Bling!")
        return
    
    if not income_tier:
        # Show income tiers with detailed descriptions
        embed = discord.Embed(
            title=f"{EMOJIS['bling']} SAUCE INCOME TIERS {EMOJIS['bling']}",
            description="Claim your Bling income every 2 hours based on your effort level!",
            color=0xffd700
        )
        
        income_descriptions = {
            '1': "**20 Bling** - A reply, Brainrot Post, 2-10 words posts...",
            '2': "**100 Bling** - A post with no graphic, OSTs, YouTube video with no edits...",
            '3': "**150 Bling** - A post with ultra basic graphic, YouTube video with very low edits...", 
            '4': "**250 Bling** - A post with decent graphics, small thread with no graphics & YouTube video with below average edit...",
            '5': "**350 Bling** - A post with multiple decent graphics, a long thread, decent edited YouTube video...",
            '6': "**500 Bling** - A long thread with multiple graphics, well edited videos above 3 minutes.",
            '7': "**800 Bling** - Hosting an event with a prize (graphics, well organized), YouTube videos above 7 minutes very well edited..."
        }
        
        for tier, description in income_descriptions.items():
            embed.add_field(
                name=f"Tier {tier} - {BLING_INCOME[tier]} {EMOJIS['bling']}",
                value=f"{description}\n`-income {tier}`",
                inline=False
            )
        
        embed.add_field(
            name="⏰ Cooldown",
            value="You can claim income **every 2 hours**!",
            inline=False
        )
        
        embed.set_footer(text="Choose the tier that matches your contribution level!")
        await ctx.send(embed=embed)
        return
    
    income_tier = income_tier.lower()
    if income_tier not in BLING_INCOME:
        await ctx.send(f"{EMOJIS['alert']} Invalid income tier! Use `-income` to see available tiers (1-7).")
        return
    
    # Check cooldown (2 hours)
    last_claim = db.get_last_income_claim(ctx.author.id)
    if last_claim:
        last_claim_time = datetime.datetime.fromisoformat(last_claim)
        time_since_last = datetime.datetime.now() - last_claim_time
        if time_since_last.total_seconds() < 7200:  # 2 hours
            time_left = 7200 - time_since_last.total_seconds()
            hours_left = int(time_left // 3600)
            minutes_left = int((time_left % 3600) // 60)
            await ctx.send(f"{EMOJIS['alert']} You can claim income again in {hours_left}h {minutes_left}m!")
            return
    
    # Give bling
    bling_amount = BLING_INCOME[income_tier]
    db.update_user_bling(ctx.author.id, bling_amount)
    db.set_last_income_claim(ctx.author.id, bling_amount)
    
    embed = discord.Embed(
        title=f"{EMOJIS['bling']} INCOME CLAIMED! {EMOJIS['bling']}",
        description=f"You earned **{bling_amount} Bling** for your Tier {income_tier} contribution!",
        color=0x00ff00
    )
    
    # Add tier description
    tier_descriptions = {
        '1': "Reply / Brainrot Post (2-10 words)",
        '2': "Post with no graphic / Basic content", 
        '3': "Post with ultra basic graphic",
        '4': "Post with decent graphics / Small thread",
        '5': "Multiple graphics / Long thread / Decent edits",
        '6': "Long thread with graphics / Well edited video (3+ min)",
        '7': "Event hosting / High quality video (7+ min)"
    }
    
    embed.add_field(
        name=f"Tier {income_tier} Contribution",
        value=tier_descriptions.get(income_tier, "Content creation"),
        inline=False
    )
    
    embed.set_footer(text="You can claim income again in 2 hours")
    
    await ctx.send(embed=embed)

# FIXED: Bling Shop with proper error handling
# UPDATED: Blingshop command with progress bars
@bot.command()
async def blingshop(ctx):
    # Check if user has sauce role
    guild_config = db.get_server_config(ctx.guild.id)
    if not guild_config or not guild_config.get('sauce_role'):
        await ctx.send(f"{EMOJIS['alert']} Sauce system is not configured on this server!")
        return
    
    sauce_role = ctx.guild.get_role(guild_config['sauce_role'])
    if not sauce_role or sauce_role not in ctx.author.roles:
        await ctx.send(f"{EMOJIS['alert']} You do not own a sauce role to use the Bling Shop!")
        return
    
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    embed = discord.Embed(
        title=f"{EMOJIS['bling']} 🛍️ BLING SHOP 🛍️ {EMOJIS['bling']}",
        description=f"Your Bling: **{user_data['bling']}** {EMOJIS['bling']}",
        color=0xffd700
    )
    
    for item_id, item_data in BLING_SHOP.items():
        # Create progress bar
        progress = min(100, (user_data['bling'] / item_data['price']) * 100)
        bars = 10
        filled_bars = int((progress / 100) * bars)
        progress_bar = "█" * filled_bars + "░" * (bars - filled_bars)
        
        can_afford = "✅" if user_data['bling'] >= item_data['price'] else "❌"
        
        embed.add_field(
            name=f"{can_afford} {item_data['name']} - {item_data['price']} {EMOJIS['bling']}",
            value=f"{item_data['description']}\nProgress: `{progress_bar}` {progress:.1f}%\n`-buybling {item_id}`",
            inline=False
        )
    
    embed.add_field(
        name="💡 Shop Info",
        value="• Items reset monthly with Bling\n• Progress shows how close you are to affording each item\n• Use `-sauceitems` to see your purchased items",
        inline=False
    )
    
    await ctx.send(embed=embed)

# NEW: Sauce Items command
@bot.command()
async def sauceitems(ctx, user: discord.Member = None):
    target = user or ctx.author
    
    # Check if viewing other user's items (admin only)
    if user and not ctx.author.guild_permissions.administrator:
        await ctx.send(f"{EMOJIS['alert']} You can only view your own sauce items!")
        return
    
    # Check if target has sauce role when viewing own items
    if not user:
        guild_config = db.get_server_config(ctx.guild.id)
        if not guild_config or not guild_config.get('sauce_role'):
            await ctx.send(f"{EMOJIS['alert']} Sauce system is not configured on this server!")
            return
        
        sauce_role = ctx.guild.get_role(guild_config['sauce_role'])
        if not sauce_role or sauce_role not in ctx.author.roles:
            await ctx.send(f"{EMOJIS['alert']} You do not own a sauce role to view sauce items!")
            return
    
    # Get user's sauce items
    c = db.conn.cursor()
    user_items = c.execute("SELECT item_name, quantity FROM sauce_items WHERE user_id = ?", (target.id,)).fetchall()
    
    # Create title based on whether viewing self or others
    if user:
        title = f"{EMOJIS['bling']} {target.display_name}'s SAUCE ITEMS {EMOJIS['bling']}"
    else:
        title = f"{EMOJIS['bling']} YOUR SAUCE ITEMS {EMOJIS['bling']}"
    
    embed = discord.Embed(
        title=title,
        color=0xffd700
    )
    
    if user_items:
        items_text = ""
        for item_name, quantity in user_items:
            items_text += f"• **{item_name}** ×{quantity}\n"
        
        embed.description = items_text
    else:
        embed.description = "No sauce items purchased yet!"
    
    embed.add_field(
        name="🛍️ How to Get Items",
        value="Purchase items from the Bling Shop using `-blingshop`!",
        inline=False
    )
    
    embed.add_field(
        name="🔄 Monthly Reset",
        value="Sauce items reset at the beginning of each month along with Bling.",
        inline=False
    )
    
    if user and ctx.author.guild_permissions.administrator:
        embed.set_footer(text=f"Viewing {target.display_name}'s sauce items (Admin View)")
    
    await ctx.send(embed=embed)

# NEW: Buy Bling Item
# FIXED: Buy Bling Item with sauce items tracking
@bot.command()
async def buybling(ctx, item_id: str = None):
    if not item_id:
        await ctx.send(f"{EMOJIS['alert']} Please specify an item to buy! Use `-blingshop` to see available items.")
        return
    
    if item_id not in BLING_SHOP:
        await ctx.send(f"{EMOJIS['alert']} Invalid item! Use `-blingshop` to see available items.")
        return
    
    # Check if user has sauce role
    guild_config = db.get_server_config(ctx.guild.id)
    if not guild_config or not guild_config.get('sauce_role'):
        await ctx.send(f"{EMOJIS['alert']} Sauce system is not configured on this server!")
        return
    
    sauce_role = ctx.guild.get_role(guild_config['sauce_role'])
    if not sauce_role or sauce_role not in ctx.author.roles:
        await ctx.send(f"{EMOJIS['alert']} You need the Sauce role to use the Bling Shop!")
        return
    
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    item_data = BLING_SHOP[item_id]
    
    if user_data['bling'] < item_data['price']:
        await ctx.send(f"{EMOJIS['alert']} You don't have enough Bling! You need {item_data['price']} {EMOJIS['bling']} but only have {user_data['bling']} {EMOJIS['bling']}.")
        return
    
    # Process purchase
    if item_id == 'strick_removal':
        if user_data['stricks'] <= 0:
            await ctx.send(f"{EMOJIS['alert']} You don't have any stricks to remove!")
            return
        db.update_user_stricks(ctx.author.id, -1)
        db.update_user_bling(ctx.author.id, -item_data['price'])
        # Track purchased item
        c = db.conn.cursor()
        c.execute("INSERT OR REPLACE INTO sauce_items (user_id, item_name, quantity) VALUES (?, ?, COALESCE((SELECT quantity FROM sauce_items WHERE user_id = ? AND item_name = ?), 0) + 1)",
                 (ctx.author.id, item_data['name'], ctx.author.id, item_data['name']))
        db.conn.commit()
        await ctx.send(f"{EMOJIS['bling']} Purchased **{item_data['name']}**! One strick has been removed.")
    
    elif item_id == 'strick_shield':
        db.update_user_bling(ctx.author.id, -item_data['price'])
        # Track purchased item  
        c = db.conn.cursor()
        c.execute("INSERT OR REPLACE INTO sauce_items (user_id, item_name, quantity) VALUES (?, ?, COALESCE((SELECT quantity FROM sauce_items WHERE user_id = ? AND item_name = ?), 0) + 1)",
                 (ctx.author.id, item_data['name'], ctx.author.id, item_data['name']))
        db.conn.commit()
        await ctx.send(f"{EMOJIS['bling']} Purchased **{item_data['name']}**! You're protected from stricks for 7 days.")
    
    elif item_id == 'brawl_pass':
        db.update_user_bling(ctx.author.id, -item_data['price'])
        # Track purchased item
        c = db.conn.cursor()
        c.execute("INSERT OR REPLACE INTO sauce_items (user_id, item_name, quantity) VALUES (?, ?, COALESCE((SELECT quantity FROM sauce_items WHERE user_id = ? AND item_name = ?), 0) + 1)",
                 (ctx.author.id, item_data['name'], ctx.author.id, item_data['name']))
        db.conn.commit()
        await ctx.send(f"{EMOJIS['bling']} Purchased **{item_data['name']}**! You can now enter Brawl Pass giveaways.")
    
    else:
        await ctx.send(f"{EMOJIS['alert']} Item purchase failed!")

# FIXED: Aura command - Add this after the other @bot.command() definitions
# Look for a good spot around line 2550, after the profile command but before other commands

@bot.command()
async def sugarrush(ctx):
    """Activate Sugar Rush for 10 minutes - triples all box rewards!"""
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    # Check if user has used sugarrush today
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if user_data['last_sugarrush'] == today:
        await ctx.send(f"{EMOJIS['alert']} You've already used Sugar Rush today! Come back tomorrow.")
        return
    
    # Check if sugarrush is already active
    if user_data['sugarrush_active']:
        expires_time = datetime.datetime.fromisoformat(user_data['sugarrush_expires'])
        if datetime.datetime.now() < expires_time:
            time_left = expires_time - datetime.datetime.now()
            minutes_left = int(time_left.total_seconds() // 60)
            seconds_left = int(time_left.total_seconds() % 60)
            await ctx.send(f"{EMOJIS['alert']} Sugar Rush is already active! {minutes_left}m {seconds_left}s remaining.")
            return
    
    # Activate Sugar Rush
    now = datetime.datetime.now()
    expires = now + datetime.timedelta(minutes=10)
    
    c = db.conn.cursor()
    c.execute("UPDATE users SET last_sugarrush = ?, sugarrush_active = 1, sugarrush_expires = ? WHERE user_id = ?",
             (today, expires.isoformat(), ctx.author.id))
    db.conn.commit()
    
    embed = discord.Embed(
        title="🍬 SUGAR RUSH ACTIVATED! 🍬",
        description="**Triple rewards** on all boxes for the next **10 minutes**!",
        color=0xff69b4
    )
    embed.add_field(
        name="🎁 What's Boosted",
        value="• All box rewards are **TRIPLED**\n• Works with `-box` command\n• Applies to ALL box types",
        inline=False
    )
    embed.add_field(
        name="⏰ Duration",
        value="10 minutes starting now!\nUse `-box` as much as you can!",
        inline=False
    )
    embed.set_footer(text="Sugar Rush can be used once per day")
    
    await ctx.send(embed=embed)
    
    # Schedule deactivation
    asyncio.create_task(deactivate_sugarrush(ctx.author.id, 600))  # 10 minutes

async def deactivate_sugarrush(user_id, delay_seconds):
    """Deactivate Sugar Rush after delay"""
    await asyncio.sleep(delay_seconds)
    
    c = db.conn.cursor()
    c.execute("UPDATE users SET sugarrush_active = 0 WHERE user_id = ?", (user_id,))
    db.conn.commit()

@bot.command()
@commands.has_permissions(administrator=True)
async def adminsugarrush(ctx, user: discord.Member, duration_minutes: int = 10):
    """Admin command to activate Sugar Rush for any user"""
    user_data = db.get_user(user.id)
    if not user_data:
        db.create_user(user.id)
        user_data = db.get_user(user.id)
    
    # Activate Sugar Rush
    now = datetime.datetime.now()
    expires = now + datetime.timedelta(minutes=duration_minutes)
    
    c = db.conn.cursor()
    c.execute("UPDATE users SET sugarrush_active = 1, sugarrush_expires = ? WHERE user_id = ?",
             (expires.isoformat(), user.id))
    db.conn.commit()
    
    embed = discord.Embed(
        title="🍬 ADMIN: SUGAR RUSH ACTIVATED! 🍬",
        description=f"**Sugar Rush** has been activated for {user.mention} for **{duration_minutes} minutes**!",
        color=0xff69b4
    )
    embed.add_field(
        name="🎁 What's Boosted",
        value="• All box rewards are **TRIPLED**\n• Works with `-box` command\n• Applies to ALL box types",
        inline=False
    )
    embed.add_field(
        name="⏰ Duration",
        value=f"{duration_minutes} minutes starting now!",
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    # Schedule deactivation
    asyncio.create_task(deactivate_sugarrush(user.id, duration_minutes * 60))

@bot.command()
async def aura(ctx, user: discord.Member = None):
    """Check your aura or give aura to another user"""
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    if user is None:
        # Check own aura
        embed = discord.Embed(
            title=f"{EMOJIS['aura']} YOUR AURA {EMOJIS['aura']}",
            description=f"You have **{user_data['aura']}** aura!",
            color=0x9370DB
        )
        embed.add_field(
            name="What is Aura?",
            value="Aura represents how much the community appreciates you! Other members can give you aura to show their appreciation.",
            inline=False
        )
        embed.add_field(
            name="How to Get More Aura",
            value="• Other members can give you aura using `-aura @username`\n• Be active and helpful in the community!\n• Participate in events and activities",
            inline=False
        )
        await ctx.send(embed=embed)
    else:
        # Give aura to another user
        if user.id == ctx.author.id:
            await ctx.send(f"{EMOJIS['alert']} You can't give aura to yourself!")
            return
        
        # Check if user has given aura today
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if user_data.get('last_aura_given') == today:
            await ctx.send(f"{EMOJIS['alert']} You've already given aura today! You can give aura again tomorrow.")
            return
        
        # Give random amount of aura (10-30)
        aura_amount = random.randint(10, 30)
        
        # Update recipient's aura
        db.update_user_currency(user.id, 'aura', aura_amount)
        
        # Update giver's last given date
        c = db.conn.cursor()
        c.execute("UPDATE users SET last_aura_given = ? WHERE user_id = ?", (today, ctx.author.id))
        db.conn.commit()
        
        embed = discord.Embed(
            title=f"{EMOJIS['aura']} AURA GIVEN! {EMOJIS['aura']}",
            description=f"You gave **{aura_amount}** aura to {user.mention}!",
            color=0x9370DB
        )
        embed.add_field(
            name="Community Appreciation",
            value=f"Thank you for showing appreciation to {user.display_name}! 💫",
            inline=False
        )
        await ctx.send(embed=embed)

# NEW: Sauce command for users to check their sauce status
@bot.command()
async def sauce(ctx):
    # Check if user has sauce role
    guild_config = db.get_server_config(ctx.guild.id)
    if not guild_config or not guild_config.get('sauce_role'):
        await ctx.send(f"{EMOJIS['alert']} Sauce system is not configured on this server!")
        return
    
    sauce_role = ctx.guild.get_role(guild_config['sauce_role'])
    if not sauce_role or sauce_role not in ctx.author.roles:
        await ctx.send(f"{EMOJIS['alert']} You do not own a sauce role to use this command!")
        return
    
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    embed = discord.Embed(
        title=f"{EMOJIS['bling']} YOUR SAUCE STATUS {EMOJIS['bling']}",
        color=0xffd700
    )
    
    embed.add_field(
        name=f"{EMOJIS['bling']} Bling Balance",
        value=f"**{user_data['bling']}** Bling",
        inline=True
    )
    
    embed.add_field(
        name=f"{EMOJIS['strick']} Stricks",
        value=f"**{user_data['stricks']}/3** stricks",
        inline=True
    )
    
    # Show last income claim info
    last_claim = user_data.get('last_income_claim')
    last_amount = user_data.get('last_income_amount', 0)
    
    if last_claim:
        last_claim_time = datetime.datetime.fromisoformat(last_claim)
        time_since_last = datetime.datetime.now() - last_claim_time
        time_left = 7200 - time_since_last.total_seconds()
        
        if time_left > 0:
            hours_left = int(time_left // 3600)
            minutes_left = int((time_left % 3600) // 60)
            embed.add_field(
                name="⏰ Next Income",
                value=f"Available in {hours_left}h {minutes_left}m",
                inline=False
            )
        else:
            embed.add_field(
                name="⏰ Next Income",
                value="Available now! Use `-income`",
                inline=False
            )
        
        embed.add_field(
            name="📊 Last Income",
            value=f"**{last_amount}** Bling - {last_claim_time.strftime('%Y-%m-%d %H:%M')}",
            inline=False
        )
    else:
        embed.add_field(
            name="⏰ Next Income",
            value="Available now! Use `-income`",
            inline=False
        )
    
    # Add warning if user has stricks
    if user_data['stricks'] >= 3:
        embed.add_field(
            name="⚠️ WARNING",
            value="You have 3 stricks and can no longer earn Bling! Use the Bling Shop to remove stricks.",
            inline=False
        )
    elif user_data['stricks'] > 0:
        embed.add_field(
            name="⚠️ Warning",
            value=f"You have {user_data['stricks']} stricks. At 3 stricks, you can no longer earn Bling!",
            inline=False
        )
    
    await ctx.send(embed=embed)
# FIXED: Pop-up spawner with proper implementation
@tasks.loop(minutes=1)
async def popup_spawner():
    c = db.conn.cursor()
    configs = c.execute("SELECT * FROM popup_config WHERE popup_enabled = 1 AND popup_channel IS NOT NULL").fetchall()
    
    for config in configs:
        guild_id = config['guild_id']
        channel_id = config['popup_channel']
        cooldown = config['popup_cooldown']
        
        guild = bot.get_guild(guild_id)
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                # Check if we should spawn a pop-up (random chance based on cooldown)
                if random.random() < (1.0 / cooldown):
                    await spawn_random_popup(channel, guild_id)

async def spawn_random_popup(channel, guild_id):
    """Spawn a pop-up question in the specified channel with configurable rewards"""
    # Get server config for ping role
    guild_config = db.get_server_config(guild_id)
    ping_role = None
    if guild_config and guild_config.get('popup_ping_role'):
        ping_role = channel.guild.get_role(guild_config['popup_ping_role'])
    
    # Get popup config for cooldown
    popup_config = db.get_popup_config(guild_id)
    
    # Determine popup type with weighted chances
    popup_roll = random.random() * 100
    popup_type = None
    
    if popup_roll < 20:  # 20% free XP
        popup_type = 'free_xp'
    elif popup_roll < 50:  # 30% trivia
        popup_type = 'trivia'
    elif popup_roll < 75:  # 25% guess brawler
        popup_type = 'guess_brawler'
    else:  # 25% two truths one lie
        popup_type = 'two_truths_lie'
    
    # Get random question of the selected type
    if popup_type == 'free_xp':
        question_data = POPUP_QUESTIONS['free_xp']
    else:
        questions = POPUP_QUESTIONS[popup_type]
        question_data = random.choice(questions)
    
    # Create embed based on question type
    embed = discord.Embed(
        title=f"{EMOJIS['pop']} BRAWL STARS POP-UP! {EMOJIS['pop']}",
        description=question_data['question'],
        color=0x00ff00
    )
    
    # Add difficulty field
    embed.add_field(
        name="📊 Difficulty",
        value=question_data['difficulty'],
        inline=True
    )
    
    # Updated rewards - replaced 1% mystery box with new rewards
    reward_text = "500 XP + "
    if popup_type == 'free_xp':
        reward_text += "**5% chance for:** 1 Emerald, Magic Key, or 200 Silver!"
    else:
        reward_text += "**15% chance for:** 1 Emerald (5%), Magic Key (5%), or 200 Silver (5%)!"
    
    embed.add_field(
        name="🎁 Rewards",
        value=reward_text,
        inline=False
    )
    
    embed.set_footer(text="First to answer correctly gets the reward! (60 seconds)")
    
    message_content = ""
    if ping_role:
        message_content = f"{ping_role.mention} "
    
    message = await channel.send(content=message_content, embed=embed)
    
    # Store the active pop-up
    bot.active_channel_popups[channel.id] = {
        'type': popup_type,
        'answer': question_data['answer'],
        'message_id': message.id,
        'expires': datetime.datetime.now() + datetime.timedelta(seconds=60),
        'claimed': False,
        'question_data': question_data
    }
    
    # Schedule expiration message
    asyncio.create_task(popup_expiration_check(channel.id))

async def popup_expiration_check(channel_id):
    """Check if pop-up expired and send message if no one answered"""
    await asyncio.sleep(60)  
    
    popup_data = bot.active_channel_popups.get(channel_id)
    if popup_data and not popup_data['claimed']:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send("⏰ Time's up! No one answered correctly.")
        del bot.active_channel_popups[channel_id]

server_activity = {}
last_drop_times = {}

@tasks.loop(minutes=1)  # Check every minute instead of every hour
async def starr_drop_spawner():
    # Check all servers with spawn channels configured
    c = db.conn.cursor()
    channels = c.execute("SELECT guild_id, spawn_channel FROM server_config WHERE spawn_channel IS NOT NULL").fetchall()
    
    for guild_id, channel_id in channels:
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
            
        channel = guild.get_channel(channel_id)
        if not channel:
            continue
        
        # Check if server has been active recently (messages in last 5 minutes)
        current_time = datetime.datetime.now()
        guild_key = str(guild_id)
        
        # Check if server was active recently
        if guild_key in server_activity:
            last_activity = server_activity[guild_key]
            time_since_activity = (current_time - last_activity).total_seconds()
            
            # If server was active within last 5 minutes, consider spawning a drop
            if time_since_activity <= 300:  # 5 minutes
                # Check if enough time has passed since last drop (30 minutes minimum)
                last_drop = last_drop_times.get(guild_key)
                if not last_drop or (current_time - last_drop).total_seconds() >= 1800:  # 30 minutes
                    await spawn_starr_drop(channel)
                    last_drop_times[guild_key] = current_time

async def spawn_starr_drop(channel):
    rarity_roll = random.random() * 100
    if rarity_roll < 50:
        rarity = 'Rare'
        chance = "50%"
    elif rarity_roll < 82:
        rarity = 'Super Rare'
        chance = "32%"
    elif rarity_roll < 94:
        rarity = 'Epic'
        chance = "12%"
    elif rarity_roll < 98.9:
        rarity = 'Mythic'
        chance = "4.9%"
    elif rarity_roll < 99.9:
        rarity = 'Legendary'
        chance = "1%"
    else:
        rarity = 'Ultra Legendary'
        chance = "0.1%"
    
    embed = discord.Embed(
        title=f"{EMOJIS[rarity.lower().replace(' ', '') + 'drop']} {rarity.upper()} STARR DROP APPEARED! {EMOJIS[rarity.lower().replace(' ', '') + 'drop']}",
        description=f"A {rarity} Starr Drop has appeared! Click the button below to catch it!",
        color=0xffd700
    )
    embed.add_field(
        name="Rarity Info",
        value=f"**Chance:** {chance}\n**Rarity:** {rarity}",
        inline=True
    )
    embed.set_image(url=STARR_DROP_IMAGES[rarity])
    embed.set_footer(text="This drop will disappear in 5 minutes!")
    
    view = StarrDropView(rarity)
    message = await channel.send(embed=embed, view=view)
    
    # Store the active drop with message ID for cleanup
    active_starr_drops[channel.id] = {
        'rarity': rarity,
        'message_id': message.id,
        'expires': datetime.datetime.now() + datetime.timedelta(minutes=5),
        'claimed': False
    }

# Weekly reset
@tasks.loop(hours=24)
async def weekly_reset():
    if datetime.datetime.now().weekday() == 0:  # Monday
        # Reset weekly XP and award top 3
        c = db.conn.cursor()
        top_3 = c.execute(
            "SELECT user_id, SUM(xp_gained) as total_xp FROM weekly_xp GROUP BY user_id ORDER BY total_xp DESC LIMIT 3"
        ).fetchall()
        
        rewards = [30, 20, 10]  # Gold amounts for top 3
        for i, (user_id, xp) in enumerate(top_3):
            if i < len(rewards):
                db.update_user_currency(user_id, 'gold', rewards[i])
        
        # Clear weekly XP
        c.execute("DELETE FROM weekly_xp")
        db.conn.commit()

# Golden Pass monthly reset
@tasks.loop(hours=24)
async def golden_pass_reset():
    # Reset on the first day of each month
    if datetime.datetime.now().day == 1:
        c = db.conn.cursor()
        # Award pass completion badges
        completed_users = c.execute("SELECT user_id FROM users WHERE golden_xp >= 3000").fetchall()  # FIXED: Use golden_xp
        for (user_id,) in completed_users:
            # Check if user already has the pass badge
            has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                                 (user_id, "Pass Completion")).fetchone()
            if not has_badge:
                c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                         (user_id, "Pass Completion"))
                c.execute("UPDATE users SET pass_completed = pass_completed + 1 WHERE user_id = ?", (user_id,))
        
        # Reset golden XP for all users
        c.execute("UPDATE users SET golden_xp = 0")
        db.conn.commit()

# Event cleanup
@tasks.loop(minutes=5)
async def event_cleanup():
    db.clear_expired_events()

# Sauce monthly reset (changed from weekly)

@tasks.loop(hours=24)
async def sauce_monthly_reset():
    # Reset on the first day of each month
    if datetime.datetime.now().day == 1:
        db.reset_monthly_stricks()
        # NEW: Clear sauce items
        c = db.conn.cursor()
        c.execute("DELETE FROM sauce_items")
        db.conn.commit()
        print("Monthly reset: Cleared all sauce items and stricks")

# Guess game cleanup
@tasks.loop(minutes=1)
async def guess_game_cleanup():
    current_time = datetime.datetime.now()
    expired_games = [channel_id for channel_id, data in active_guess_games.items() 
                     if current_time > data['expires']]
    for channel_id in expired_games:
        del active_guess_games[channel_id]

# Cleanup expired tasks
@tasks.loop(minutes=1)
async def cleanup_tasks():
    current_time = datetime.datetime.now()
    
    # Cleanup expired popups
    expired_popups = [user_id for user_id, data in active_popups.items() if current_time > data['expires']]
    for user_id in expired_popups:
        del active_popups[user_id]
    
    # Cleanup expired starr drops
    expired_drops = [channel_id for channel_id, data in active_starr_drops.items() if current_time > data['expires']]
    for channel_id in expired_drops:
        del active_starr_drops[channel_id]
    
    # Cleanup expired channel pop-ups
    expired_channel_popups = [channel_id for channel_id, data in bot.active_channel_popups.items() 
                             if current_time > data['expires']]
    for channel_id in expired_channel_popups:
        del bot.active_channel_popups[channel_id]

@tasks.loop(minutes=1)
async def sugarrush_cleanup():
    """Clean up expired Sugar Rush activations"""
    now = datetime.datetime.now().isoformat()
    c = db.conn.cursor()
    c.execute("UPDATE users SET sugarrush_active = 0 WHERE sugarrush_expires < ?", (now,))
    db.conn.commit()

# FIXED: Profile command with server-specific XP and copper display - REMOVED bling and strick
@bot.command()
async def profile(ctx, user: discord.Member = None):
    target = user or ctx.author
    user_data = db.get_user(target.id)
    if not user_data:
        db.create_user(target.id)
        user_data = db.get_user(target.id)
    
    # FIXED: Use server-specific XP
    xp = db.get_server_user_xp(target.id, ctx.guild.id)
    level, xp_needed, total_xp = calculate_level(xp)
    xp_current = xp - total_xp
    progress = (xp_current / xp_needed) * 100 if xp_needed > 0 else 100
    
    golden_level, golden_needed, golden_current = calculate_golden_level(user_data['golden_xp'])
    golden_progress = (golden_current / golden_needed) * 100 if golden_needed > 0 else 100
    
    # Get collection counts
    c = db.conn.cursor()
    char_count = c.execute("SELECT COUNT(*) FROM user_characters WHERE user_id = ?", (target.id,)).fetchone()[0]
    skin_count = c.execute("SELECT COUNT(*) FROM user_skins WHERE user_id = ?", (target.id,)).fetchone()[0]
    artifact_count = c.execute("SELECT COUNT(*) FROM user_artifacts WHERE user_id = ?", (target.id,)).fetchone()[0]
    badge_count = c.execute("SELECT COUNT(*) FROM user_badges WHERE user_id = ?", (target.id,)).fetchone()[0]
    
    # Get city progress
    buildings = db.get_user_buildings(target.id)
    total_buildings = len(CITY_BUILDINGS)
    built_count = len(buildings)
    max_levels = sum([data['max_level'] for data in CITY_BUILDINGS.values()])
    current_levels = sum([b['level'] for b in buildings])
    city_progress = (current_levels / max_levels) * 100 if max_levels > 0 else 0
    
    embed = discord.Embed(
        title=f"{EMOJIS['levelbadge']} {target.display_name}'s PROFILE {EMOJIS['levelbadge']}",
        color=0x00ff00
    )
    
    embed.add_field(
        name="📊 LEVEL & STATS",
        value=f"{EMOJIS['xp']} **Level:** {level}\n"
              f"📈 **Progress:** {progress:.1f}% ({xp_current}/{xp_needed} XP)\n"
              f"⭐ **Total XP:** {xp}",
        inline=True
    )
    
    embed.add_field(
        name=f"{EMOJIS['goldenxp']} GOLDEN PASS",
        value=f"{EMOJIS['pass']} **Tier:** {golden_level}\n"
              f"📊 **Progress:** {golden_progress:.1f}%\n"
              f"✨ **Completed:** {user_data['pass_completed']} times",
        inline=True
    )
    
    embed.add_field(
        name="💰 CURRENCIES",
        value=f"{EMOJIS['planks']} **Planks:** {user_data['planks']}\n"
              f"{EMOJIS['stone']} **Stone:** {user_data['stone']}\n"
              f"{EMOJIS['iron']} **Iron:** {user_data['iron']}\n"
              f"{EMOJIS['copper']} **Copper:** {user_data['copper']}\n"
              f"{EMOJIS['silver']} **Silver:** {user_data['silver']}\n"
              f"{EMOJIS['gold']} **Gold:** {user_data['gold']}\n"
              f"{EMOJIS['diamonds']} **Diamonds:** {user_data['diamonds']}\n"
              f"{EMOJIS['magic_key']} **Magic Keys:** {user_data['magic_keys']}",  # FIXED: Added magic keys
        inline=True
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**🎯 COLLECTIONS**",
        inline=False
    )
    
    embed.add_field(
        name="Collections",
        value=f"{EMOJIS['characterbadge']} **Characters:** {char_count}/20\n"
              f"{EMOJIS['skinbadge']} **Skins:** {skin_count}/30\n"
              f"{EMOJIS['artifactbadge']} **Artifacts:** {artifact_count}/15\n"
              f"{EMOJIS['citybadge']} **Badges:** {badge_count}/9\n"
              f"{EMOJIS['citybadge']} **City:** {city_progress:.1f}% ({current_levels}/{max_levels} levels)\n"
              f"{EMOJIS['aura']} **Aura:** {user_data['aura']}",
        inline=True
    )
    
    await ctx.send(embed=embed)

# FIXED: Golden Pass command
@bot.command()
async def goldenpass(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    golden_level, golden_needed, golden_current = calculate_golden_level(user_data['golden_xp'])
    golden_progress = (golden_current / golden_needed) * 100 if golden_needed > 0 else 100
    
    # Determine user's boost tier
    boost_tier = 'free'
    guild_config = db.get_server_config(ctx.guild.id)
    
    if guild_config:
        member = ctx.guild.get_member(ctx.author.id)
        if guild_config.get('boost3_role'):
            boost_role = ctx.guild.get_role(guild_config['boost3_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost3'
        elif guild_config.get('boost2_role'):
            boost_role = ctx.guild.get_role(guild_config['boost2_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost2'
        elif guild_config.get('boost1_role'):
            boost_role = ctx.guild.get_role(guild_config['boost1_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost1'
    
    embed = discord.Embed(
        title=f"{EMOJIS['pass']} GOLDEN PASS PROGRESS {EMOJIS['pass']}",
        description=f"**Tier:** {golden_level}\n**Boost:** {boost_tier.upper()}",
        color=0xffd700
    )
    
    # Create progress bar
    bars = 20
    filled_bars = int(golden_progress / 5)  # 5% per bar
    progress_bar = "█" * filled_bars + "░" * (bars - filled_bars)
    
    embed.add_field(
        name="Progress",
        value=f"**{golden_current}/{golden_needed} Golden XP** ({golden_progress:.1f}%)\n`{progress_bar}`",
        inline=False
    )
    
    # Show next tier rewards
    next_rewards = get_golden_pass_rewards(boost_tier, golden_level + 1)
    if next_rewards:
        reward_text = "\n".join([f"{EMOJIS[currency]} {amount} {currency.capitalize()}" 
                               for currency, amount in next_rewards.items()])
        embed.add_field(
            name=f"🎁 Tier {golden_level + 1} Rewards",
            value=reward_text,
            inline=False
        )
    
    embed.set_footer(text="Earn Golden XP by completing daily quests and being active!")
    await ctx.send(embed=embed)

# UPDATED: Pass rewards command with improved display and reduced diamonds
@bot.command()
async def passrewards(ctx):
    embed = discord.Embed(
        title=f"{EMOJIS['pass']} GOLDEN PASS REWARDS {EMOJIS['pass']}",
        description="Monthly cumulative rewards for each tier:",
        color=0xffd700
    )
    
    # Calculate cumulative rewards for each boost tier with reduced diamonds
    boost_tiers = ['free', 'boost1', 'boost2', 'boost3']
    
    for boost_tier in boost_tiers:
        cumulative_rewards = {}
        
        # Calculate rewards for tiers 1-50 with reduced diamonds
        for tier in range(1, 51):
            rewards = get_golden_pass_rewards(boost_tier, tier)
            for currency, amount in rewards.items():
                cumulative_rewards[currency] = cumulative_rewards.get(currency, 0) + amount
        
        # Apply diamond reductions
        if boost_tier == 'free' and 'diamonds' in cumulative_rewards:
            cumulative_rewards['diamonds'] = min(cumulative_rewards['diamonds'], 5)  # Reduced from 15 to 5
        elif boost_tier == 'boost1' and 'diamonds' in cumulative_rewards:
            cumulative_rewards['diamonds'] = min(cumulative_rewards['diamonds'], 20)  # Reduced from 29 to 20
        elif boost_tier == 'boost2' and 'diamonds' in cumulative_rewards:
            cumulative_rewards['diamonds'] = min(cumulative_rewards['diamonds'], 35)  # Reduced from 50 to 35
        elif boost_tier == 'boost3' and 'diamonds' in cumulative_rewards:
            cumulative_rewards['diamonds'] = min(cumulative_rewards['diamonds'], 50)  # Reduced from 74 to 50
        
        # Format the rewards text
        reward_texts = []
        for currency, total_amount in cumulative_rewards.items():
            if total_amount > 0:
                reward_texts.append(f"{EMOJIS[currency]} {total_amount} {currency.capitalize()}")
        
        tier_name = "Free" if boost_tier == 'free' else f"Boost {boost_tier[-1]}"
        embed.add_field(
            name=f"{tier_name} (Monthly Total)",
            value="\n".join(reward_texts) if reward_texts else "No rewards",
            inline=True
        )
    
    embed.add_field(
        name="💡 How it Works",
        value="These are the **total monthly rewards** you get from completing all 50 tiers of the Golden Pass! Higher boost tiers give more rewards.",
        inline=False
    )
    
    await ctx.send(embed=embed)

# NEW: Artifacts command
@bot.command()
async def artifacts(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    c = db.conn.cursor()
    user_artifacts = c.execute("SELECT artifact_name FROM user_artifacts WHERE user_id = ?", (ctx.author.id,)).fetchall()
    user_artifact_names = [artifact[0] for artifact in user_artifacts]
    
    embed = discord.Embed(
        title=f"{EMOJIS['artifactbadge']} YOUR ARTIFACT COLLECTION {EMOJIS['artifactbadge']}",
        description=f"You have {len(user_artifact_names)}/15 artifacts",
        color=0x9b59b6
    )
    
    # Show all artifacts with status
    artifact_status = []
    for artifact_name in ARTIFACTS.keys():
        status = "✅" if artifact_name in user_artifact_names else "❌"
        artifact_status.append(f"{status} **{artifact_name}**")
    
    # Split into chunks for better display
    chunk_size = 5
    artifact_chunks = [artifact_status[i:i + chunk_size] for i in range(0, len(artifact_status), chunk_size)]
    
    for i, chunk in enumerate(artifact_chunks):
        embed.add_field(
            name=f"Artifacts {i+1}" if i == 0 else "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            value="\n".join(chunk),
            inline=False
        )
    
    embed.add_field(
        name="🎁 How to Get Artifacts",
        value="• **Artifact Boxes**: Use `-artifactsbox` (requires 1000 Copper + 1 Magic Key)\n• **Mystery Boxes**: Rare chance from mystery boxes\n• **Special Events**: During limited-time events",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def tutorial(ctx, topic: str = None):
    if topic:
        topic = topic.lower()
        if topic == 'aura':
            embed = discord.Embed(
                title="💫 AURA SYSTEM TUTORIAL 💫",
                description="Aura represents how much the community appreciates you!",
                color=0x9370DB
            )
            embed.add_field(
                name="How it Works",
                value="• Members can give 10-30 aura to someone else once per day\n• Use `-aura @user` to give aura\n• Use `-aura` to check your own aura\n• Aura shows community appreciation and support",
                inline=False
            )
            await ctx.send(embed=embed)
        
        elif topic == 'boxes':
            embed = discord.Embed(
                title="📦 BOX SYSTEM TUTORIAL 📦",
                description="Learn how the box system works!",
                color=0xff69b4
            )
            embed.add_field(
                name="Box Types",
                value="• **Small Box**: 50% chance, 2 rewards\n• **Regular Box**: 25% chance, 4 rewards\n• **Big Box**: 15% chance, 7 rewards\n• **Mega Box**: 5% chance, 10 rewards\n• **Omega Box**: 1% chance, 20 rewards\n• **Ultra Box**: 0.1% chance, 35 rewards\n• **Mystery Box**: Special boxes from levels\n• **Artifact Box**: Unlock with copper and magic keys",
                inline=False
            )
            embed.add_field(
                name="How to Use",
                value="• Use `-box` to get a random box\n• Use `-openbox` to see your boxes\n• Click the 'Open' button to open boxes\n• Better boxes = more rewards!\n• Use `-artifactsbox` to unlock artifact boxes",
                inline=False
            )
            await ctx.send(embed=embed)
        
        elif topic == 'battle':
            embed = discord.Embed(
                title="⚔️ BATTLE SYSTEM TUTORIAL ⚔️",
                description="Battle other players or AI with your characters!",
                color=0xff0000
            )
            embed.add_field(
                name="PVE Battles",
                value="• Use `-battle pve <character>`\n• Higher rarity = higher win chance\n• Win rewards based on character rarity",
                inline=False
            )
            embed.add_field(
                name="PVP Battles", 
                value="• Use `-battle pvp @user <character>` to challenge\n• The challenged user uses `-battleaccept @user <character>`\n• Higher rarity characters have advantage\n• Winner gets rewards based on their character's rarity",
                inline=False
            )
            embed.add_field(
                name="Win Chances",
                value="• **Rare**: 10% (PVE)\n• **Super Rare**: 25%\n• **Epic**: 45%\n• **Mythic**: 65%\n• **Legendary**: 80%\n• **Ultra Legendary**: 90%",
                inline=False
            )
            await ctx.send(embed=embed)
        
        elif topic == 'copper':
            embed = discord.Embed(
                title=f"{EMOJIS['copper']} COPPER SYSTEM TUTORIAL {EMOJIS['copper']}",
                description="Learn about the copper resource!",
                color=0xb87333
            )
            embed.add_field(
                name="What is Copper?",
                value="Copper is a resource that sits between iron and silver in value and rarity.",
                inline=False
            )
            embed.add_field(
                name="How to Get Copper",
                value="""• **Boxes**: 12.7% chance from any box
• **Copper Mine**: Build a copper mine in your city
• **Golden Pass**: Some tiers reward copper
• **Battles**: Chance to get copper from PVE battles""",
                inline=False
            )
            embed.add_field(
                name="What is Copper Used For?",
                value="""• **Building Upgrades**: Required for upgrading most buildings
• **Artifact Boxes**: 1000 copper + 1 magic key to unlock
• **Future Content**: More uses coming soon!""",
                inline=False
            )
            embed.add_field(
                name="Magic Keys",
                value="Magic keys are rare items needed to unlock artifact boxes. Get them from boxes or special rewards!",
                inline=False
            )
            await ctx.send(embed=embed)
        
        else:
            await ctx.send(f"{EMOJIS['alert']} Tutorial topic not found! Use `-tutorial` to see all topics.")
    
    else:
        # Main tutorial - REWRITTEN for better user guidance
        embed = discord.Embed(
            title="🎮 BOT TUTORIAL & GUIDE 🎮",
            description="Welcome! Here's how to use this bot efficiently:",
            color=0x00ff00
        )
        
        embed.add_field(
            name="🚀 GETTING STARTED",
            value="""**1. EARN XP & LEVEL UP**
• Chat in any channel to earn XP (10 XP per message)
• Share art/clips in designated channels for bonus XP
• Level up to unlock mystery boxes and rewards

**2. DAILY ACTIVITIES**
• Use `-daily` every day for free rewards
• Use `-weekly` for bigger weekly rewards  
• Complete `-quests` for Golden XP

**3. MANAGE YOUR ECONOMY**
• Use `-bal` to check your resources
• Use `-profile` to see your progress
• Build your city with `-city` and `-upgrade`""",
            inline=False
        )
        
        embed.add_field(
            name="📦 BOXES & REWARDS",
            value="""**BOX SYSTEM**
• Use `-box` to get random boxes
• Use `-openbox` to open collected boxes
• Better boxes = more and better rewards

**ARTIFACT BOXES**
• Get magic keys from boxes (0.1% chance)
• Collect 1000 copper from boxes or mines
• Use `-artifactsbox` to unlock artifact boxes""",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ BATTLE SYSTEM",
            value="""**CHARACTER COLLECTION**
• Use `-characters` to see your collection
• Use `-catch` when Starr Drops appear
• Complete your collection for badges!""",
            inline=False
        )
        
        embed.add_field(
            name="🏆 PROGRESSION SYSTEMS",
            value="""**GOLDEN PASS**
• Earn Golden XP from daily activities
• Use `-goldenpass` to check progress
• Reach higher tiers for better rewards

**BADGES & ACHIEVEMENTS**
• Use `-badges` to track progress
• Complete collections and challenges
• Earn special roles for major achievements""",
            inline=False
        )
        
        embed.add_field(
            name="💡 PRO TIPS",
            value="""• **Check `-chances`** to see drop rates
• **Build your city early** for passive income
• **Complete daily quests** for Golden XP
• **Catch Starr Drops** for rare characters
• **Trade resources** with `-trade` if needed
• **Upgrade buildings** for better production""",
            inline=False
        )
        
        embed.add_field(
            name="🔧 NEED HELP?",
            value="""Use `-help` for all commands
Use `-tutorial <topic>` for specific guides
Topics: aura, boxes, battle, copper""",
            inline=False
        )
        
        embed.set_footer(text="Happy gaming! Start with -daily and -box to get going! 🎮")
        await ctx.send(embed=embed)
# NEW: Give Bling command for admins
@bot.command()
@commands.has_permissions(administrator=True)
async def givebling(ctx, user: discord.Member, amount: int):
    user_data = db.get_user(user.id)
    if not user_data:
        db.create_user(user.id)
    
    db.update_user_bling(user.id, amount)
    await ctx.send(f"{EMOJIS['bling']} Gave **{amount} Bling** to {user.mention}! They now have {user_data['bling'] + amount if user_data else amount} Bling.")
    # NEW: Give Strick command for admins
@bot.command()
@commands.has_permissions(administrator=True)
async def givestrick(ctx, user: discord.Member, amount: int = 1):
    user_data = db.get_user(user.id)
    if not user_data:
        db.create_user(user.id)
        user_data = db.get_user(user.id)
    
    db.update_user_stricks(user.id, amount)
    await ctx.send(f"{EMOJIS['strick']} Gave **{amount} strick(s)** to {user.mention}! They now have {user_data['stricks'] + amount} stricks.")

# NEW: Help Sauce command
@bot.command()
async def helpsauce(ctx):
    embed = discord.Embed(
        title=f"{EMOJIS['bling']} SAUCE SYSTEM GUIDE {EMOJIS['bling']}",
        description="Learn how the Sauce system works for content creators!",
        color=0xffd700
    )
    
    embed.add_field(
        name="🎯 WHAT IS THE SAUCE SYSTEM?",
        value="The Sauce system is for content creators to earn **Bling** for their contributions!",
        inline=False
    )
    
    embed.add_field(
        name="💰 HOW TO EARN BLING",
        value="""**Available command:**
-income : for more info!""",
        inline=False
    )
    
    embed.add_field(
        name="⏰ INCOME COOLDOWN",
        value="You can claim income **every 2 hours** per income type!",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ STRIKE SYSTEM",
        value="""• **3 strikes** = Can no longer earn Bling!
• Strike removal costs **3000 Bling** in the shop
• Strike reset monthly if you earn enough Bling""",
        inline=False
    )
    
    embed.add_field(
        name="🛍️ BLING SHOP",
        value="""Use `-blingshop` to see available items:
• **Strike Removal** - 2500 Bling
• **Strike Shield (7 days)** - 2000 Bling  
• **Brawl Pass Giveaway Ticket** - 1200 Bling""",
        inline=False
    )
    
    embed.add_field(
        name="🔧 ADMIN COMMANDS",
        value="""`-sauceset setrole @role` - Set Sauce role
`-givebling @user amount` - Give Bling
`-removebling @user amount` - Remove Bling  
`-givestrick @user amount` - Give stricks
`-removestrick @user amount` - Remove stricks""",
        inline=False
    )
    
    embed.set_footer(text="Use -sauce to check your status, -income to see types, -blingshop to browse!")
    await ctx.send(embed=embed)
    
# NEW: Remove Strick command for admins  
@bot.command()
@commands.has_permissions(administrator=True)
async def removestrick(ctx, user: discord.Member, amount: int = 1):
    user_data = db.get_user(user.id)
    if not user_data:
        await ctx.send(f"{EMOJIS['alert']} User not found in database!")
        return
    
    current_stricks = user_data['stricks']
    if amount > current_stricks:
        amount = current_stricks  # Remove all stricks if amount exceeds current
    
    db.update_user_stricks(user.id, -amount)
    await ctx.send(f"{EMOJIS['strick']} Removed **{amount} strick(s)** from {user.mention}! They now have {current_stricks - amount} stricks.")
    
@bot.command()
async def quests(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    quests = db.get_daily_quests(ctx.author.id)
    
    # Check if any quests were completed and award Golden XP
    golden_xp_rewarded = 0
    
    # Quest 1: Open 10 Boxes - 100 Golden XP
    if quests['quest1_progress'] >= 10 and quests['quest1_progress'] != 1000:  # 1000 is our completion marker
        golden_xp_rewarded += 100
        db.update_daily_quest(ctx.author.id, 'quest1_progress', 1000)  # Mark as completed
    
    # Quest 2: Send 3 Messages - 50 Golden XP  
    if quests['quest2_progress'] >= 3 and quests['quest2_progress'] != 1000:
        golden_xp_rewarded += 50
        db.update_daily_quest(ctx.author.id, 'quest2_progress', 1000)
    
    # Quest 3: Catch 1 Starr Drop - 150 Golden XP
    if quests['quest3_progress'] >= 1 and quests['quest3_progress'] != 1000:
        golden_xp_rewarded += 150
        db.update_daily_quest(ctx.author.id, 'quest3_progress', 1000)
    
    # Quest 4: Win 3 Battles - 200 Golden XP
    if quests['quest4_progress'] >= 3 and quests['quest4_progress'] != 1000:
        golden_xp_rewarded += 200
        db.update_daily_quest(ctx.author.id, 'quest4_progress', 1000)
    
    # Quest 5: Collect City Income 2 Times - 100 Golden XP
    if quests['quest5_progress'] >= 2 and quests['quest5_progress'] != 1000:
        golden_xp_rewarded += 100
        db.update_daily_quest(ctx.author.id, 'quest5_progress', 1000)
    
    # Award Golden XP if any quests were completed
    if golden_xp_rewarded > 0:
        c = db.conn.cursor()
        c.execute("UPDATE users SET golden_xp = golden_xp + ? WHERE user_id = ?", 
                 (golden_xp_rewarded, ctx.author.id))
        db.conn.commit()
    
    embed = discord.Embed(
        title=f"{EMOJIS['quests']} DAILY QUESTS {EMOJIS['daily']}",
        description="Complete these quests to earn Golden XP!",
        color=0x00ff00
    )
    
    # Update progress display to show completion status
    quest1_progress = "✅ COMPLETED" if quests['quest1_progress'] >= 1000 else f"{min(quests['quest1_progress'], 10)}/10"
    quest2_progress = "✅ COMPLETED" if quests['quest2_progress'] >= 1000 else f"{min(quests['quest2_progress'], 3)}/3"
    quest3_progress = "✅ COMPLETED" if quests['quest3_progress'] >= 1000 else f"{min(quests['quest3_progress'], 1)}/1"
    quest4_progress = "✅ COMPLETED" if quests['quest4_progress'] >= 1000 else f"{min(quests['quest4_progress'], 3)}/3"
    quest5_progress = "✅ COMPLETED" if quests['quest5_progress'] >= 1000 else f"{min(quests['quest5_progress'], 2)}/2"
    
    embed.add_field(
        name="📦 Open 10 Boxes",
        value=f"**Progress:** {quest1_progress}\n**Reward:** 100 Golden XP",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="",
        inline=False
    )
    
    embed.add_field(
        name="💬 Send 3 Messages",
        value=f"**Progress:** {quest2_progress}\n**Reward:** 50 Golden XP",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Catch 1 Starr Drop",
        value=f"**Progress:** {quest3_progress}\n**Reward:** 150 Golden XP",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Win 3 Battles",
        value=f"**Progress:** {quest4_progress}\n**Reward:** 200 Golden XP",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="",
        inline=False
    )
    
    embed.add_field(
        name="🏙️ Collect City Income 2 Times",
        value=f"**Progress:** {quest5_progress}\n**Reward:** 100 Golden XP",
        inline=False
    )
    
    # Show completion message if Golden XP was awarded
    if golden_xp_rewarded > 0:
        embed.add_field(
            name="🎉 QUEST REWARDS CLAIMED! 🎉",
            value=f"You earned **{golden_xp_rewarded} Golden XP** for completing quests!",
            inline=False
        )
    
    total_completed = sum([
        1 if quests['quest1_progress'] >= 1000 else 0,
        1 if quests['quest2_progress'] >= 1000 else 0,
        1 if quests['quest3_progress'] >= 1000 else 0,
        1 if quests['quest4_progress'] >= 1000 else 0,
        1 if quests['quest5_progress'] >= 1000 else 0
    ])
    
    if total_completed >= 5:
        embed.add_field(
            name="🏆 All Quests Completed!",
            value=f"You've completed all 5 daily quests! Great job!",
            inline=False
        )
    
    embed.set_footer(text="Quests reset daily at midnight UTC • Use -quests to claim rewards")
    await ctx.send(embed=embed)

def get_starr_drop_reward(rarity):
    if rarity == 'Rare':
        if random.random() < 0.8:
            # Get random rare character
            rare_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Rare']
            return {'character': random.choice(rare_chars)}
        else:
            return {'currency': 'silver', 'amount': random.randint(20, 60)}  # Doubled silver
    
    elif rarity == 'Super Rare':
        if random.random() < 0.8:
            super_rare_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Super Rare']
            return {'character': random.choice(super_rare_chars)}
        else:
            return {'currency': 'silver', 'amount': random.randint(60, 200)}  # Doubled silver
    
    elif rarity == 'Epic':
        if random.random() < 0.8:
            epic_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Epic']
            return {'character': random.choice(epic_chars)}
        elif random.random() < 0.9:
            return {'currency': 'silver', 'amount': random.randint(200, 400)}  # Doubled silver
        else:
            return {'currency': 'gold', 'amount': random.randint(10, 20)}
    
    elif rarity == 'Mythic':
        if random.random() < 0.9:
            mythic_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Mythic']
            return {'character': random.choice(mythic_chars)}
        else:
            return {'currency': 'gold', 'amount': random.randint(20, 50)}
    
    elif rarity == 'Legendary':
        if random.random() < 0.9:
            legendary_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Legendary']
            return {'character': random.choice(legendary_chars)}
        elif random.random() < 0.95:
            return {'currency': 'gold', 'amount': random.randint(50, 100)}
        else:
            return {'currency': 'diamonds', 'amount': random.randint(2, 5)}
    
    elif rarity == 'Ultra Legendary':
        if random.random() < 0.9:
            ultra_chars = [name for name, data in CHARACTERS.items() if data['rarity'] == 'Ultra Legendary']
            return {'character': random.choice(ultra_chars)}
        else:
            return {'currency': 'diamonds', 'amount': 25}
    
    return {'currency': 'silver', 'amount': 20}  # Fallback

# Command: Daily Rewards
@bot.command()
async def daily(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if user_data['last_daily'] == today:
        await ctx.send(f"{EMOJIS['alert']} You've already claimed your daily reward today!")
        return
    
    # Check and update daily streak
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    new_streak = 1
    if user_data['last_daily'] == yesterday:
        new_streak = user_data['daily_streak'] + 1
    elif user_data['last_daily'] != today:
        new_streak = 1
    
    # Update last daily and streak
    c = db.conn.cursor()
    c.execute("UPDATE users SET last_daily = ?, daily_streak = ? WHERE user_id = ?", 
             (today, new_streak, ctx.author.id))
    
    # Check user's boost tier for different rewards
    boost_tier = 'free'
    guild_config = db.get_server_config(ctx.guild.id)
    
    if guild_config:
        member = ctx.guild.get_member(ctx.author.id)
        if guild_config.get('boost3_role'):
            boost_role = ctx.guild.get_role(guild_config['boost3_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost3'
        elif guild_config.get('boost2_role'):
            boost_role = ctx.guild.get_role(guild_config['boost2_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost2'
        elif guild_config.get('boost1_role'):
            boost_role = ctx.guild.get_role(guild_config['boost1_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost1'
    
    # Determine reward based on boost tier
    daily_roll = random.random() * 100
    
    if boost_tier == 'free':
        if daily_roll < 50:
            reward = {'type': 'silver', 'amount': random.randint(20, 50)}
        elif daily_roll < 82:
            reward = {'type': 'gold', 'amount': random.randint(3, 5)}
        elif daily_roll < 94:
            reward = {'type': 'planks', 'amount': 5000}
        elif daily_roll < 98.9:
            artifact = get_random_artifact()
            if artifact != "10 Silver":
                reward = {'type': 'artifact', 'name': artifact}
            else:
                reward = {'type': 'silver', 'amount': 10}
        elif daily_roll < 99.9:
            db.add_box_to_user(ctx.author.id, 'ultra_box')
            reward = {'type': 'ultra_box'}
        else:
            reward = {'type': 'diamonds', 'amount': 2}
    else:
        # Boosted rewards
        if daily_roll < 50:
            reward = {'type': 'silver', 'amount': random.randint(30, 200)}
        elif daily_roll < 82:
            reward = {'type': 'gold', 'amount': random.randint(5, 10)}
        elif daily_roll < 94:
            reward = {'type': 'planks', 'amount': 10000}
        elif daily_roll < 98.9:
            # 2 artifacts
            artifact1 = get_random_artifact()
            artifact2 = get_random_artifact()
            reward = {'type': 'double_artifact', 'name1': artifact1, 'name2': artifact2}
        elif daily_roll < 99.9:
            db.add_box_to_user(ctx.author.id, 'ultra_box', 3)
            reward = {'type': 'triple_ultra_box'}
        else:
            reward = {'type': 'diamonds', 'amount': 10}
    
    embed = discord.Embed(
        title="🎁 DAILY REWARD CLAIMED! 🎁",
        description=f"**Daily Streak:** {new_streak} days\n**Boost Tier:** {boost_tier.upper()}",
        color=0xff69b4
    )
    
    if reward['type'] == 'silver':
        db.update_user_currency(ctx.author.id, 'silver', reward['amount'])
        embed.add_field(name="💰 Silver", value=f"{EMOJIS['silver']} {reward['amount']} Silver", inline=False)
    elif reward['type'] == 'gold':
        db.update_user_currency(ctx.author.id, 'gold', reward['amount'])
        embed.add_field(name="💰 Gold", value=f"{EMOJIS['gold']} {reward['amount']} Gold", inline=False)
    elif reward['type'] == 'planks':
        db.update_user_currency(ctx.author.id, 'planks', reward['amount'])
        embed.add_field(name="🪵 Planks", value=f"{EMOJIS['planks']} {reward['amount']} Planks", inline=False)
    elif reward['type'] == 'artifact':
        await add_artifact_to_user(ctx.author.id, reward['name'])
        embed.add_field(name="🎁 Artifact", value=f"**{reward['name']}**", inline=False)
    elif reward['type'] == 'double_artifact':
        await add_artifact_to_user(ctx.author.id, reward['name1'])
        await add_artifact_to_user(ctx.author.id, reward['name2'])
        embed.add_field(name="🎁 Double Artifacts", value=f"**{reward['name1']}** and **{reward['name2']}**", inline=False)
    elif reward['type'] == 'ultra_box':
        embed.add_field(name="📦 Ultra Box", value="You found an Ultra Box! Use `-openbox ultra` to open it!", inline=False)
    elif reward['type'] == 'triple_ultra_box':
        embed.add_field(name="📦 Triple Ultra Box", value="You found 3 Ultra Boxes! Use `-openbox ultra` to open them!", inline=False)
    elif reward['type'] == 'diamonds':
        db.update_user_currency(ctx.author.id, 'diamonds', reward['amount'])
        embed.add_field(name="💎 Diamonds", value=f"{EMOJIS['diamonds']} {reward['amount']} Diamonds", inline=False)
    
    db.conn.commit()
    # Check for daily badge after claiming
    await check_badge_achievements(ctx.author.id)
    await ctx.send(embed=embed)

# Command: Weekly Rewards
@bot.command()
async def weekly(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    # Get current week
    current_week = datetime.datetime.now().strftime("%Y-%W")
    
    if user_data['last_weekly'] == current_week:
        await ctx.send(f"{EMOJIS['alert']} You've already claimed your weekly reward this week!")
        return
    
    # Update last weekly
    c = db.conn.cursor()
    c.execute("UPDATE users SET last_weekly = ? WHERE user_id = ?", (current_week, ctx.author.id))
    
    # Check user's boost tier for different rewards
    boost_tier = 'free'
    guild_config = db.get_server_config(ctx.guild.id)
    
    if guild_config:
        member = ctx.guild.get_member(ctx.author.id)
        if guild_config.get('boost3_role'):
            boost_role = ctx.guild.get_role(guild_config['boost3_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost3'
        elif guild_config.get('boost2_role'):
            boost_role = ctx.guild.get_role(guild_config['boost2_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost2'
        elif guild_config.get('boost1_role'):
            boost_role = ctx.guild.get_role(guild_config['boost1_role'])
            if boost_role and boost_role in member.roles:
                boost_tier = 'boost1'
    
    # Determine reward based on boost tier
    weekly_roll = random.random() * 100
    
    if boost_tier == 'free':
        if weekly_roll < 50:
            db.add_box_to_user(ctx.author.id, 'omega_box')
            reward = {'type': 'omega_box'}
        elif weekly_roll < 82:
            reward = {'type': 'gold', 'amount': random.randint(35, 50)}
        elif weekly_roll < 94:
            # 2 artifacts
            artifact1 = get_random_artifact()
            artifact2 = get_random_artifact()
            reward = {'type': 'double_artifact', 'name1': artifact1, 'name2': artifact2}
        elif weekly_roll < 98.9:
            reward = {'type': 'diamonds', 'amount': 3}
        else:
            db.add_box_to_user(ctx.author.id, 'mystery_box')
            reward = {'type': 'mystery_box'}
    else:
        # Boosted rewards
        if weekly_roll < 50:
            db.add_box_to_user(ctx.author.id, 'ultra_box', 3)
            reward = {'type': 'triple_ultra_box'}
        elif weekly_roll < 82:
            reward = {'type': 'diamonds', 'amount': 10}
        elif weekly_roll < 94:
            db.add_box_to_user(ctx.author.id, 'mystery_box')
            reward = {'type': 'mystery_box'}
        elif weekly_roll < 98.9:
            # 5 artifacts
            artifacts = [get_random_artifact() for _ in range(5)]
            reward = {'type': 'multiple_artifacts', 'artifacts': artifacts}
        else:
            db.add_box_to_user(ctx.author.id, 'mystery_box', 3)
            reward = {'type': 'triple_mystery_box'}
    
    embed = discord.Embed(
        title="📅 WEEKLY REWARD CLAIMED! 📅",
        description=f"**Boost Tier:** {boost_tier.upper()}",
        color=0x7289da
    )
    
    if reward['type'] == 'omega_box':
        embed.add_field(name="📦 Omega Box", value="You received an Omega Box! Use `-openbox omega` to open it!", inline=False)
    elif reward['type'] == 'gold':
        db.update_user_currency(ctx.author.id, 'gold', reward['amount'])
        embed.add_field(name="💰 Gold", value=f"{EMOJIS['gold']} {reward['amount']} Gold", inline=False)
    elif reward['type'] == 'double_artifact':
        await add_artifact_to_user(ctx.author.id, reward['name1'])
        await add_artifact_to_user(ctx.author.id, reward['name2'])
        embed.add_field(name="🎁 Double Artifacts", value=f"**{reward['name1']}** and **{reward['name2']}**", inline=False)
    elif reward['type'] == 'diamonds':
        db.update_user_currency(ctx.author.id, 'diamonds', reward['amount'])
        embed.add_field(name="💎 Diamonds", value=f"{EMOJIS['diamonds']} {reward['amount']} Diamonds", inline=False)
    elif reward['type'] == 'mystery_box':
        embed.add_field(name="🎁 Mystery Box", value="You received a Mystery Box! Use `-openbox mystery` to open it!", inline=False)
    elif reward['type'] == 'triple_ultra_box':
        embed.add_field(name="📦 Triple Ultra Box", value="You received 3 Ultra Boxes! Use `-openbox ultra` to open them!", inline=False)
    elif reward['type'] == 'multiple_artifacts':
        for artifact in reward['artifacts']:
            await add_artifact_to_user(ctx.author.id, artifact)
        artifact_names = ", ".join([f"**{a}**" for a in reward['artifacts']])
        embed.add_field(name="🎁 Multiple Artifacts", value=f"You found: {artifact_names}", inline=False)
    elif reward['type'] == 'triple_mystery_box':
        embed.add_field(name="🎁 Triple Mystery Box", value="You received 3 Mystery Boxes! Use `-openbox mystery` to open them!", inline=False)
    
    db.conn.commit()
    await ctx.send(embed=embed)

# UPDATED: Shop command to show copper in trading rates
@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🛍️ SKIN SHOP 🛍️",
        description="Buy awesome skins with your currencies!",
        color=0x7289da
    )
    
    # Group skins by rarity
    skins_by_rarity = {}
    for skin_name, skin_data in SKINS.items():
        rarity = skin_data['rarity']
        if rarity not in skins_by_rarity:
            skins_by_rarity[rarity] = []
        
        price_text = ""
        if 'price_silver' in skin_data:
            price_text += f"{EMOJIS['silver']} {skin_data['price_silver']} "
        if 'price_gold' in skin_data:
            price_text += f"{EMOJIS['gold']} {skin_data['price_gold']} "
        if 'price_diamond' in skin_data:
            price_text += f"{EMOJIS['diamonds']} {skin_data['price_diamond']}"
        
        skins_by_rarity[rarity].append(f"**{skin_name}** - {price_text}")
    
    # Add skins to embed by rarity
    for rarity, skins_list in skins_by_rarity.items():
        emoji_key = rarity.lower().replace(' ', '') + 'skin'
        if emoji_key == 'ultralegendaryskin':
            emoji_key = 'ultralegendaryskin'
        
        embed.add_field(
            name=f"{EMOJIS.get(emoji_key, '🎨')} {rarity} Skins",
            value="\n".join(skins_list),
            inline=False
        )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**💱 TRADING RATES**",
        inline=False
    )
    
    # UPDATED: Added copper to trade rates
    embed.add_field(
        name="Exchange Rates",
        value=f"10000 Planks -> 20 Silver\n10000 Stone -> 10 Gold\n10000 Iron -> 1 Diamond\n5000 Copper -> 5 Gold",
        inline=False
    )
    
    embed.set_footer(text="Use `-buy <skin_name>` to purchase a skin! Use `-trade <amount> <from_currency> <to_currency>` to exchange currencies!")
    await ctx.send(embed=embed)

# Command: Buy Skin
@bot.command()
async def buy(ctx, *, skin_name: str):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    skin_data = None
    for name, data in SKINS.items():
        if name.lower() == skin_name.lower():
            skin_data = data
            skin_name = name
            break
    
    if not skin_data:
        await ctx.send(f"{EMOJIS['alert']} Skin '{skin_name}' not found!")
        return
    
    # Check if user already has the skin
    c = db.conn.cursor()
    has_skin = c.execute("SELECT 1 FROM user_skins WHERE user_id = ? AND skin_name = ?", 
                        (ctx.author.id, skin_name)).fetchone()
    if has_skin:
        await ctx.send(f"{EMOJIS['alert']} You already own this skin!")
        return
    
    # Check if user has enough currency
    can_afford = True
    missing = []
    
    if 'price_silver' in skin_data and user_data['silver'] < skin_data['price_silver']:
        can_afford = False
        missing.append(f"{EMOJIS['silver']} {skin_data['price_silver'] - user_data['silver']} more Silver")
    
    if 'price_gold' in skin_data and user_data['gold'] < skin_data['price_gold']:
        can_afford = False
        missing.append(f"{EMOJIS['gold']} {skin_data['price_gold'] - user_data['gold']} more Gold")
    
    if 'price_diamond' in skin_data and user_data['diamonds'] < skin_data['price_diamond']:
        can_afford = False
        missing.append(f"{EMOJIS['diamonds']} {skin_data['price_diamond'] - user_data['diamonds']} more Diamonds")
    
    if not can_afford:
        await ctx.send(f"{EMOJIS['alert']} You can't afford this skin! You need:\n" + "\n".join(missing))
        return
    
    # Deduct currency and add skin
    if 'price_silver' in skin_data:
        db.update_user_currency(ctx.author.id, 'silver', -skin_data['price_silver'])
    if 'price_gold' in skin_data:
        db.update_user_currency(ctx.author.id, 'gold', -skin_data['price_gold'])
    if 'price_diamond' in skin_data:
        db.update_user_currency(ctx.author.id, 'diamonds', -skin_data['price_diamond'])
    
    c.execute("INSERT INTO user_skins (user_id, skin_name, rarity) VALUES (?, ?, ?)",
             (ctx.author.id, skin_name, skin_data['rarity']))
    db.conn.commit()
    
    embed = discord.Embed(
        title="🎉 SKIN PURCHASED! 🎉",
        description=f"You bought **{skin_name}** ({skin_data['rarity']})!",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# UPDATED: Trade command with copper support
@bot.command()
async def trade(ctx, amount: int, from_currency: str, to_currency: str):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    # Define exchange rates - UPDATED: Added copper rate
    exchange_rates = {
        'planks': {'silver': 0.002},  # 10000 planks = 20 silver
        'stone': {'gold': 0.001},     # 10000 stone = 10 gold
        'iron': {'diamonds': 0.0001}, # 10000 iron = 1 diamond
        'copper': {'gold': 0.001}     # 5000 copper = 5 gold
    }
    
    # Validate currencies
    from_currency = from_currency.lower()
    to_currency = to_currency.lower()
    
    if from_currency not in exchange_rates:
        await ctx.send(f"{EMOJIS['alert']} Invalid source currency! Available: planks, stone, iron, copper")
        return
    
    if to_currency not in exchange_rates[from_currency]:
        available = ', '.join(exchange_rates[from_currency].keys())
        await ctx.send(f"{EMOJIS['alert']} Invalid target currency for {from_currency}! Available: {available}")
        return
    
    # Check if user has enough source currency
    if user_data[from_currency] < amount:
        await ctx.send(f"{EMOJIS['alert']} You don't have enough {from_currency}! You have {user_data[from_currency]}, but need {amount}.")
        return
    
    # Calculate exchange
    rate = exchange_rates[from_currency][to_currency]
    received_amount = int(amount * rate)
    
    if received_amount < 1:
        await ctx.send(f"{EMOJIS['alert']} The amount is too small to exchange! You would get 0 {to_currency}.")
        return
    
    # Perform exchange
    db.update_user_currency(ctx.author.id, from_currency, -amount)
    db.update_user_currency(ctx.author.id, to_currency, received_amount)
    
    embed = discord.Embed(
        title="💱 TRADE COMPLETED! 💱",
        description=f"Successfully exchanged {amount} {from_currency} for {received_amount} {to_currency}!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="Exchange Rate",
        value=f"**Rate:** 1 {from_currency} = {rate} {to_currency}",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Command: Characters
@bot.command()
async def characters(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    c = db.conn.cursor()
    user_chars = c.execute("SELECT character_name FROM user_characters WHERE user_id = ?", (ctx.author.id,)).fetchall()
    user_char_names = [char[0] for char in user_chars]
    
    embed = discord.Embed(
        title=f"{EMOJIS['characterbadge']} YOUR CHARACTER COLLECTION {EMOJIS['characterbadge']}",
        description=f"You have {len(user_char_names)}/20 characters",
        color=0x7289da
    )
    
    # Group characters by rarity
    chars_by_rarity = {}
    for char_name, char_data in CHARACTERS.items():
        rarity = char_data['rarity']
        if rarity not in chars_by_rarity:
            chars_by_rarity[rarity] = []
        
        status = "✅" if char_name in user_char_names else "❌"
        chars_by_rarity[rarity].append(f"{status} {char_name}")
    
    for rarity, char_list in chars_by_rarity.items():
        embed.add_field(
            name=f"{rarity} Characters",
            value="\n".join(char_list),
            inline=True
        )
    
    await ctx.send(embed=embed)

# Command: Character Info
@bot.command()
async def character(ctx, *, character_name: str):
    char_data = None
    for name, data in CHARACTERS.items():
        if name.lower() == character_name.lower():
            char_data = data
            character_name = name
            break
    
    if not char_data:
        await ctx.send(f"{EMOJIS['alert']} Character '{character_name}' not found!")
        return
    
    # Check if user has the character
    c = db.conn.cursor()
    has_char = c.execute("SELECT 1 FROM user_characters WHERE user_id = ? AND character_name = ?", 
                        (ctx.author.id, character_name)).fetchone()
    
    status = "✅ Owned" if has_char else "❌ Not Owned"
    
    embed = discord.Embed(
        title=f"🎭 {character_name}",
        description=char_data['description'],
        color=0xff69b4
    )
    embed.add_field(name="Rarity", value=char_data['rarity'], inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    
    await ctx.send(embed=embed)

# Command: Building Info
@bot.command()
async def building(ctx, *, building_name: str):
    # Find the building
    building_data = None
    building_type = None
    
    for b_type, b_data in CITY_BUILDINGS.items():
        if b_data['name'].lower() == building_name.lower() or b_type.lower() == building_name.lower():
            building_data = b_data
            building_type = b_type
            break
    
    if not building_data:
        available_buildings = ", ".join([b_data['name'] for b_data in CITY_BUILDINGS.values()])
        await ctx.send(f"{EMOJIS['alert']} Invalid building! Available buildings: {available_buildings}")
        return
    
    # Get user's current level for this building
    user_building = db.get_user_building(ctx.author.id, building_type)
    current_level = user_building['level'] if user_building else 0
    
    embed = discord.Embed(
        title=f"{building_data['emoji']} {building_data['name']} INFO {building_data['emoji']}",
        description=building_data['description'],
        color=0x2ecc71
    )
    
    embed.add_field(
        name="🏗️ CURRENT STATUS",
        value=f"**Your Level:** {current_level}/{building_data['max_level']}\n"
              f"**Collection Time:** {building_data['collection_hours']} hours",
        inline=False
    )
    
    # Show requirements
    if building_data['requirements']:
        req_text = "\n".join([f"{CITY_BUILDINGS[req]['emoji']} {CITY_BUILDINGS[req]['name']} Level {min_level}" 
                             for req, min_level in building_data['requirements'].items()])
        embed.add_field(
            name="📋 REQUIREMENTS",
            value=req_text,
            inline=False
        )
    
    # Show current outputs if built
    if current_level > 0:
        current_outputs = building_data['outputs'][current_level]
        output_text = "\n".join([f"{EMOJIS[currency]} {amount} {currency.capitalize()}" 
                               for currency, amount in current_outputs.items()])
        embed.add_field(
            name="💰 CURRENT PRODUCTION",
            value=output_text,
            inline=False
        )
    
    # Show upgrade costs if not max level
    if current_level < building_data['max_level']:
        next_level = current_level + 1
        upgrade_costs = building_data['costs'][next_level]
        cost_text = "\n".join([f"{EMOJIS[currency]} {amount} {currency.capitalize()}" 
                             for currency, amount in upgrade_costs.items()])
        embed.add_field(
            name=f"⚡ UPGRADE TO LEVEL {next_level}",
            value=cost_text,
            inline=False
        )
        
        # Show next level outputs
        next_outputs = building_data['outputs'][next_level]
        next_output_text = "\n".join([f"{EMOJIS[currency]} {amount} {currency.capitalize()}" 
                                    for currency, amount in next_outputs.items()])
        embed.add_field(
            name="🎯 NEXT LEVEL PRODUCTION",
            value=next_output_text,
            inline=False
        )
    
    embed.set_footer(text=f"Use -upgrade {building_data['name']} to upgrade this building!")
    await ctx.send(embed=embed)

# Command: City
@bot.command()
async def city(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    buildings = db.get_user_buildings(ctx.author.id)
    building_dict = {b['building_type']: b for b in buildings}
    
    embed = discord.Embed(
        title=f"🏙️ {ctx.author.display_name}'s CITY 🏙️",
        description="Manage your city buildings to generate passive income!",
        color=0x2ecc71
    )
    
    # Calculate total progress
    total_buildings = len(CITY_BUILDINGS)
    built_count = len(buildings)
    max_levels = sum([data['max_level'] for data in CITY_BUILDINGS.values()])
    current_levels = sum([b['level'] for b in buildings])
    city_progress = (current_levels / max_levels) * 100 if max_levels > 0 else 0
    
    # Create progress bar
    bars = 20
    filled_bars = int(city_progress / 5)  # 5% per bar
    progress_bar = "█" * filled_bars + "░" * (bars - filled_bars)
    
    embed.add_field(
        name="🏗️ CITY PROGRESS",
        value=f"**Buildings:** {built_count}/{total_buildings}\n**Levels:** {current_levels}/{max_levels}\n**Progress:** {city_progress:.1f}%\n`{progress_bar}`",
        inline=False
    )
    
    # Show building status
    building_status = []
    for building_type, building_data in CITY_BUILDINGS.items():
        building_info = building_dict.get(building_type)
        level = building_info['level'] if building_info else 0
        max_level = building_data['max_level']
        
        status_emoji = "🟢" if level == max_level else "🟡" if level > 0 else "🔴"
        building_status.append(f"{status_emoji} **{building_data['name']}** - Level {level}/{max_level}")
    
    # Split building status into chunks for better display
    chunk_size = 4
    building_chunks = [building_status[i:i + chunk_size] for i in range(0, len(building_status), chunk_size)]
    
    for i, chunk in enumerate(building_chunks):
        embed.add_field(
            name=f"🏛️ BUILDINGS {i+1}" if i == 0 else "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            value="\n".join(chunk),
            inline=False
        )
    
    embed.add_field(
        name="💰 INCOME INFORMATION",
        value="Use `-collect` to gather resources from your buildings!\nUse `-upgrade <building>` to upgrade your buildings!\nUse `-building <name>` for detailed info!\nUse `-cityproduction` to see hourly production rates!",
        inline=False
    )
    
    # Check if city is complete for badge
    if current_levels >= max_levels:
        # Award city badge if not already awarded
        c = db.conn.cursor()
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (ctx.author.id, "City Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (ctx.author.id, "City Badge"))
            db.conn.commit()
            embed.add_field(
                name="🏆 BADGE EARNED! 🏆",
                value="You've completed your city and earned the City Badge!",
                inline=False
            )
    
    await ctx.send(embed=embed)

# NEW: City Production command
@bot.command()
async def cityproduction(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    buildings = db.get_user_buildings(ctx.author.id)
    building_dict = {b['building_type']: b for b in buildings}
    
    embed = discord.Embed(
        title=f"🏭 {ctx.author.display_name}'s HOURLY PRODUCTION RATES 🏭",
        description="Here's what your city produces every hour:",
        color=0x2ecc71
    )
    
    total_production = {}
    has_buildings = False
    
    for building_type, building_data in CITY_BUILDINGS.items():
        building_info = building_dict.get(building_type)
        level = building_info['level'] if building_info else 0
        
        if level > 0:
            has_buildings = True
            outputs = building_data['outputs'][level]
            collection_hours = building_data['collection_hours']
            
            # Calculate hourly production
            hourly_outputs = {}
            for currency, amount in outputs.items():
                hourly_amount = amount / collection_hours
                hourly_outputs[currency] = hourly_amount
                total_production[currency] = total_production.get(currency, 0) + hourly_amount
            
            # Format building production
            production_text = ""
            for currency, hourly_amount in hourly_outputs.items():
                if currency == 'diamonds' and hourly_amount < 1:
                    production_text += f"{EMOJIS[currency]} {hourly_amount:.3f}/h\n"
                else:
                    production_text += f"{EMOJIS[currency]} {hourly_amount:.1f}/h\n"
            
            embed.add_field(
                name=f"{building_data['emoji']} {building_data['name']} (Lvl {level})",
                value=production_text,
                inline=True
            )
    
    if not has_buildings:
        embed.add_field(
            name="No Buildings",
            value="You don't have any buildings yet! Use `-upgrade` to build some and start generating resources.",
            inline=False
        )
    else:
        # Add total production summary
        if total_production:
            total_text = ""
            for currency, hourly_amount in total_production.items():
                if currency == 'diamonds' and hourly_amount < 1:
                    total_text += f"{EMOJIS[currency]} {hourly_amount:.3f}/h\n"
                else:
                    total_text += f"{EMOJIS[currency]} {hourly_amount:.1f}/h\n"
            
            embed.add_field(
                name="📊 TOTAL HOURLY PRODUCTION",
                value=total_text,
                inline=False
            )
        
        embed.add_field(
            name="💡 PRODUCTION INFO",
            value="• Numbers show **resources per hour**\n• Actual collection happens every building's collection period\n• Use `-collect` to gather accumulated resources\n• Upgrade buildings to increase production rates!",
            inline=False
        )
    
    await ctx.send(embed=embed)

# FIXED: Upgrade Building command with proper error handling
@bot.command()
async def upgrade(ctx, *, building_name: str):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    # Find the building type
    building_type = None
    building_data = None
    
    for b_type, b_data in CITY_BUILDINGS.items():
        if b_data['name'].lower() == building_name.lower() or b_type.lower() == building_name.lower():
            building_type = b_type
            building_data = b_data
            break
    
    if not building_type:
        available_buildings = ", ".join([b_data['name'] for b_data in CITY_BUILDINGS.values()])
        await ctx.send(f"{EMOJIS['alert']} Invalid building! Available buildings: {available_buildings}")
        return
    
    # Check requirements
    for req_building, min_level in building_data['requirements'].items():
        req_info = db.get_user_building(ctx.author.id, req_building)
        if not req_info or req_info['level'] < min_level:
            req_data = CITY_BUILDINGS[req_building]
            await ctx.send(f"{EMOJIS['alert']} You need {req_data['name']} at level {min_level} to build this!")
            return
    
    # Get current building level
    building_info = db.get_user_building(ctx.author.id, building_type)
    current_level = building_info['level'] if building_info else 0
    max_level = building_data['max_level']
    
    if current_level >= max_level:
        await ctx.send(f"{EMOJIS['alert']} This building is already fully upgraded!")
        return
    
    # Get costs for next level
    next_level = current_level + 1
    costs = building_data['costs'][next_level]
    
    # Check if user has enough resources
    can_afford = True
    missing = []
    
    for currency, amount in costs.items():
        emoji_key = 'diamonds' if currency == 'diamonds' else currency
        if user_data.get(currency, 0) < amount:
            can_afford = False
            missing.append(f"{EMOJIS[emoji_key]} {amount - user_data.get(currency, 0)} more {currency.capitalize()}")
    
    if not can_afford:
        await ctx.send(f"{EMOJIS['alert']} You don't have enough resources to upgrade to level {next_level}! You need:\n" + "\n".join(missing))
        return
    
    # Deduct resources and upgrade building
    for currency, amount in costs.items():
        db.update_user_currency(ctx.author.id, currency, -amount)
    
    db.upgrade_building(ctx.author.id, building_type, next_level)
    
    # Get new output information
    new_outputs = building_data['outputs'][next_level]
    output_text = ", ".join([f"{EMOJIS[currency]} {amount} {currency.capitalize()}" for currency, amount in new_outputs.items()])
    
    embed = discord.Embed(
        title="🏗️ BUILDING UPGRADED! 🏗️",
        description=f"You upgraded **{building_data['name']}** to level {next_level}!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="New Production",
        value=f"Now produces every {building_data['collection_hours']} hours:\n{output_text}",
        inline=False
    )
    
    embed.add_field(
        name="Building Description",
        value=building_data['description'],
        inline=False
    )
    
    await ctx.send(embed=embed)

# UPDATED: Collect Resources command - now tracks quest progress
@bot.command()
async def collect(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    buildings = db.get_user_buildings(ctx.author.id)
    
    if not buildings:
        await ctx.send(f"{EMOJIS['alert']} You don't have any buildings to collect from! Use `-upgrade` to build some.")
        return
    
    total_collected = {}
    collected_from = []
    
    for building in buildings:
        building_type = building['building_type']
        level = building['level']
        
        if level == 0:
            continue
            
        building_data = CITY_BUILDINGS[building_type]
        
        # Check if building is ready to collect
        last_collected = building['last_collected']
        now = datetime.datetime.now()
        
        if last_collected:
            last_time = datetime.datetime.fromisoformat(last_collected)
            hours_since_last = (now - last_time).total_seconds() / 3600
            
            if hours_since_last < building_data['collection_hours']:
                continue  # Not ready to collect yet
        
        # Calculate resources to collect
        outputs = building_data['outputs'][level]
        for currency, amount in outputs.items():
            # Handle fractional diamonds (only give whole diamonds when accumulated)
            if currency == 'diamonds' and amount < 1:
                # Track fractional diamonds in user data for later collection
                current_fractional = user_data.get('fractional_diamonds', 0)
                new_fractional = current_fractional + amount
                if new_fractional >= 1:
                    whole_diamonds = int(new_fractional)
                    fractional_remainder = new_fractional - whole_diamonds
                    db.update_user_currency(ctx.author.id, 'diamonds', whole_diamonds)
                    total_collected['diamonds'] = total_collected.get('diamonds', 0) + whole_diamonds
                    # Store remainder
                    c = db.conn.cursor()
                    c.execute("UPDATE users SET fractional_diamonds = ? WHERE user_id = ?", (fractional_remainder, ctx.author.id))
                else:
                    # Store fractional amount
                    c = db.conn.cursor()
                    c.execute("UPDATE users SET fractional_diamonds = ? WHERE user_id = ?", (new_fractional, ctx.author.id))
            else:
                db.update_user_currency(ctx.author.id, currency, amount)
                total_collected[currency] = total_collected.get(currency, 0) + amount
        
        # Update collection time
        db.update_building_collection(ctx.author.id, building_type)
        collected_from.append(building_data['name'])
    
    if not collected_from:
        await ctx.send(f"{EMOJIS['alert']} No buildings are ready to collect from yet! Check back later.")
        return
    
    # Update daily quest progress for collecting income
    quests = db.get_daily_quests(ctx.author.id)
    if quests and quests['quest5_progress'] < 2:
        new_progress = min(quests['quest5_progress'] + 1, 2)
        db.update_daily_quest(ctx.author.id, 'quest5_progress', new_progress)
    
    embed = discord.Embed(
        title="💰 RESOURCES COLLECTED! 💰",
        description=f"Collected resources from {len(collected_from)} buildings!",
        color=0xffd700
    )
    
    embed.add_field(
        name="🏗️ Buildings Collected From",
        value="\n".join([f"• {name}" for name in collected_from]),
        inline=False
    )
    
    if total_collected:
        collected_text = "\n".join([f"{EMOJIS[currency]} {currency.capitalize()}: +{amount}" 
                                  for currency, amount in total_collected.items()])
        embed.add_field(
            name="📦 Resources Collected",
            value=collected_text,
            inline=False
        )
    
    await ctx.send(embed=embed)

# Command: Badges
@bot.command()
async def badges(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    c = db.conn.cursor()
    user_badges = c.execute("SELECT badge_name FROM user_badges WHERE user_id = ?", (ctx.author.id,)).fetchall()
    user_badge_names = [badge[0] for badge in user_badges]
    
    # Define all possible badges
    all_badges = {
        "Level Badge": {"emoji": EMOJIS['levelbadge'], "requirement": "Reach level 100"},
        "Artifact Badge": {"emoji": EMOJIS['artifactbadge'], "requirement": "Collect all artifacts"}, 
        "Skin Badge": {"emoji": EMOJIS['skinbadge'], "requirement": "Collect all skins"},
        "Character Badge": {"emoji": EMOJIS['characterbadge'], "requirement": "Collect all characters"},
        "City Badge": {"emoji": EMOJIS['citybadge'], "requirement": "Complete building your city"},
        "Boost Badge": {"emoji": EMOJIS['boostbadge'], "requirement": "Boost a server twice"},
        "Daily Badge": {"emoji": EMOJIS['dailybadge'], "requirement": "Claim /daily everyday for 30 Days"},
        "Pass Badge": {"emoji": EMOJIS['passbadge'], "requirement": "Finish the pass once"},
        "Command Badge": {"emoji": EMOJIS['commandbadge'], "requirement": "5000 Commands"},
        "Drop Badge": {"emoji": EMOJIS['dropbadge'], "requirement": "Opening 100 Drops"}
    }
    
    # Check badge progress with progress bars
    badge_progress = {}
    for badge_name, badge_info in all_badges.items():
        has_badge = badge_name in user_badge_names
        
        # Calculate progress for each badge
        progress = 0
        if badge_name == "Level Badge":
            # FIXED: Use server-specific XP
            xp = db.get_server_user_xp(ctx.author.id, ctx.guild.id)
            level, _, _ = calculate_level(xp)
            progress = min(100, (level / 100) * 100)
        elif badge_name == "Artifact Badge":
            artifact_count = c.execute("SELECT COUNT(*) FROM user_artifacts WHERE user_id = ?", (ctx.author.id,)).fetchone()[0]
            progress = min(100, (artifact_count / 15) * 100)
        elif badge_name == "Skin Badge":
            skin_count = c.execute("SELECT COUNT(*) FROM user_skins WHERE user_id = ?", (ctx.author.id,)).fetchone()[0]
            progress = min(100, (skin_count / 30) * 100)
        elif badge_name == "Character Badge":
            char_count = c.execute("SELECT COUNT(*) FROM user_characters WHERE user_id = ?", (ctx.author.id,)).fetchone()[0]
            progress = min(100, (char_count / 20) * 100)
        elif badge_name == "City Badge":
            buildings = db.get_user_buildings(ctx.author.id)
            max_levels = sum([data['max_level'] for data in CITY_BUILDINGS.values()])
            current_levels = sum([b['level'] for b in buildings])
            progress = min(100, (current_levels / max_levels) * 100) if max_levels > 0 else 0
        elif badge_name == "Daily Badge":
            progress = min(100, (user_data['daily_streak'] / 30) * 100)
        elif badge_name == "Pass Badge":
            progress = 100 if user_data['pass_completed'] > 0 else 0
        elif badge_name == "Command Badge":
            progress = min(100, (user_data['commands_used'] / 5000) * 100)
        elif badge_name == "Drop Badge":
            progress = min(100, (user_data['drops_caught'] / 100) * 100)
        elif badge_name == "Boost Badge":
            # Simple implementation for boost badge
            progress = 50 if user_data['last_boost_claim'] else 0
        
        # Create progress bar
        bars = 10
        filled_bars = int((progress / 100) * bars)
        progress_bar = "█" * filled_bars + "░" * (bars - filled_bars)
        
        badge_progress[badge_name] = {
            "emoji": badge_info["emoji"],
            "requirement": badge_info["requirement"],
            "status": "✅" if has_badge else f"{progress:.1f}%",
            "progress_bar": progress_bar
        }
    
    # Check for master/ultra/ultimate badges
    total_badges = len(user_badge_names)
    master_progress = min(100, (total_badges / 5) * 100)
    ultra_progress = min(100, (total_badges / 7) * 100)
    ultimate_progress = min(100, (total_badges / 10) * 100)
    
    master_bars = int((master_progress / 100) * 10)
    ultra_bars = int((ultra_progress / 100) * 10)
    ultimate_bars = int((ultimate_progress / 100) * 10)
    
    master_status = "✅" if total_badges >= 5 else f"{master_progress:.1f}%"
    ultra_status = "✅" if total_badges >= 7 else f"{ultra_progress:.1f}%"
    ultimate_status = "✅" if total_badges >= 10 else f"{ultimate_progress:.1f}%"
    
    embed = discord.Embed(
        title=f"🏆 {ctx.author.display_name}'s BADGES 🏆",
        description=f"You have {total_badges}/10 badges",
        color=0xffd700
    )
    
    # Add regular badges with progress bars
    for badge_name, progress in badge_progress.items():
        embed.add_field(
            name=f"{progress['status']} {progress['emoji']} {badge_name}",
            value=f"{progress['requirement']}\n`{progress['progress_bar']}`",
            inline=False
        )
    
    # Add special badge roles with progress bars
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**SPECIAL BADGE ROLES**",
        inline=False
    )
    
    embed.add_field(
        name=f"{master_status} {EMOJIS['master']} Master Badge",
        value=f"Earn 5 Badges and receive an exclusive role\n`{'█' * master_bars}{'░' * (10 - master_bars)}`",
        inline=False
    )
    
    embed.add_field(
        name=f"{ultra_status} {EMOJIS['ultra']} Ultra Badge",
        value=f"Earn 7 Badges and receive an exclusive role\n`{'█' * ultra_bars}{'░' * (10 - ultra_bars)}`",
        inline=False
    )
    
    embed.add_field(
        name=f"{ultimate_status} {EMOJIS['ultimate']} Ultimate Badge",
        value=f"Earn every badge and receive an exclusive role\n`{'█' * ultimate_bars}{'░' * (10 - ultimate_bars)}`",
        inline=False
    )
    
    await ctx.send(embed=embed)

# FIXED: Aura Leaderboard command
@bot.command()
async def auraleaderboard(ctx):
    c = db.conn.cursor()
    top_aura = c.execute("SELECT user_id, aura FROM users WHERE aura > 0 ORDER BY aura DESC LIMIT 10").fetchall()
    
    embed = discord.Embed(
        title=f"{EMOJIS['aura']} AURA LEADERBOARD {EMOJIS['aura']}",
        color=0x9370DB
    )
    
    leaderboard_text = ""
    for i, (user_id, aura) in enumerate(top_aura):
        user = bot.get_user(user_id)
        username = user.display_name if user else f"Unknown User ({user_id})"
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
        leaderboard_text += f"{medal} **{username}** - {aura} aura\n"
    
    if not leaderboard_text:
        leaderboard_text = "No one has any aura yet!"
    
    embed.description = leaderboard_text
    await ctx.send(embed=embed)

# NEW: Bling Leaderboard command
@bot.command()
async def blingleaderboard(ctx):
    c = db.conn.cursor()
    top_bling = c.execute("SELECT user_id, bling FROM users WHERE bling > 0 ORDER BY bling DESC LIMIT 10").fetchall()
    
    embed = discord.Embed(
        title=f"{EMOJIS['bling']} BLING LEADERBOARD {EMOJIS['bling']}",
        color=0xffd700
    )
    
    leaderboard_text = ""
    for i, (user_id, bling) in enumerate(top_bling):
        user = bot.get_user(user_id)
        username = user.display_name if user else f"Unknown User ({user_id})"
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
        leaderboard_text += f"{medal} **{username}** - {bling} {EMOJIS['bling']}\n"
    
    if not leaderboard_text:
        leaderboard_text = "No one has any Bling yet!"
    
    embed.description = leaderboard_text
    embed.set_footer(text="Bling is earned by Sauce members through the -income command")
    await ctx.send(embed=embed)

# UPDATED: Guess Number Game command with 1 minute timer and 4 guesses max
@bot.command()
async def guessnumber(ctx):
    """Start a guess the number game with rewards!"""
    # Check if there's already an active game in this channel
    if ctx.channel.id in active_guess_games:
        await ctx.send(f"{EMOJIS['alert']} There's already an active guess number game in this channel!")
        return
    
    # Generate random number between 1-100
    target_number = random.randint(1, 100)
    
    embed = discord.Embed(
        title="🎯 GUESS THE NUMBER GAME! 🎯",
        description="I'm thinking of a number between **1 and 100**!\n\nType your guess in the chat to win **200 XP + random resource**!",
        color=0x00ff00
    )
    embed.add_field(
        name="🏆 Rewards",
        value="• **200 XP**\n• **Random Resource** (20 silver, 2 gold, 50-60 iron, 60-80 copper, 200 stone, or 2000 planks)",
        inline=False
    )
    embed.add_field(
        name="📋 Rules",
        value="• **4 guesses maximum** per player\n• **1 minute time limit**\n• First correct guess wins!",
        inline=False
    )
    embed.set_footer(text="Game expires in 1 minute!")
    
    await ctx.send(embed=embed)
    
    # Store the active game with 1 minute timer
    active_guess_games[ctx.channel.id] = {
        'number': target_number,
        'expires': datetime.datetime.now() + datetime.timedelta(minutes=1),
        'claimed': False
    }
# Command: XP Level - FIXED: Server-specific XP
@bot.command()
async def xplevel(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    # FIXED: Use server-specific XP
    xp = db.get_server_user_xp(ctx.author.id, ctx.guild.id)
    level, xp_needed, total_xp = calculate_level(xp)
    xp_current = xp - total_xp
    progress = (xp_current / xp_needed) * 100 if xp_needed > 0 else 100
    
    # Create progress bar
    bars = 20
    filled_bars = int((xp_current / xp_needed) * bars) if xp_needed > 0 else bars
    progress_bar = "█" * filled_bars + "░" * (bars - filled_bars)
    
    embed = discord.Embed(
        title=f"{EMOJIS['xp']} LEVEL PROGRESS {EMOJIS['xp']}",
        color=0x00ff00
    )
    
    embed.add_field(
        name="Current Level",
        value=f"**Level {level}**",
        inline=True
    )
    
    embed.add_field(
        name="Progress", 
        value=f"{xp_current}/{xp_needed} XP ({progress:.1f}%)",
        inline=True
    )
    
    embed.add_field(
        name="Progress Bar",
        value=f"`{progress_bar}`",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**📊 STATISTICS**",
        inline=False
    )
    
    embed.add_field(
        name="Total XP",
        value=f"{xp} XP",
        inline=True
    )
    
    embed.add_field(
        name="XP to Next Level",
        value=f"{xp_needed - xp_current} XP needed",
        inline=True
    )
    
    await ctx.send(embed=embed)

# Command: XP Info
@bot.command()
async def xp(ctx):
    embed = discord.Embed(
        title=f"{EMOJIS['xp']} XP SYSTEM INFO {EMOJIS['xp']}",
        color=0x7289da
    )
    
    embed.add_field(
        name="🎯 How to Earn XP",
        value="""• **Chatting**: 10 XP per message
• **Sharing Arts**: 200 XP (in art channel)
• **Sending Clips**: 100 XP (in clip channel)  
• **Pop-up Questions**: 500 XP
• **Boost Role**: 2x-3x XP multiplier!""",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**📊 LEVEL DIFFICULTY**",
        inline=False
    )
    
    embed.add_field(
        name="Level Ranges",
        value="""• **Level 1-10**: Easy
• **Level 11-25**: Moderate  
• **Level 26-50**: A bit grindy
• **Level 51-75**: Very grindy
• **Level 76-100**: EXTREME difficult""",
        inline=False
    )
    
    embed.add_field(
        name="🏆 WEEKLY LEADERBOARD",
        value="Top 3 players each week earn rare ores:\n🥇 30 Gold\n🥈 20 Gold\n🥉 10 Gold",
        inline=False
    )
    
    embed.add_field(
        name="💫 SERVER-SPECIFIC LEVELS",
        value="Your level progress is now separate for each server! Talk in different servers to level up separately.",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Command: XP Leaderboard - FIXED: Server-specific leaderboard
@bot.command()
async def xpleaderboard(ctx):
    c = db.conn.cursor()
    
    # Server-specific leaderboard (using server_xp table)
    top_server = c.execute(
        "SELECT user_id, xp FROM server_xp WHERE guild_id = ? ORDER BY xp DESC LIMIT 10",
        (ctx.guild.id,)
    ).fetchall()
    
    # Weekly leaderboard
    week = datetime.datetime.now().strftime("%Y-%W")
    top_weekly = c.execute(
        "SELECT user_id, SUM(xp_gained) as weekly_xp FROM weekly_xp WHERE week = ? GROUP BY user_id ORDER BY weekly_xp DESC LIMIT 5",
        (week,)
    ).fetchall()
    
    embed = discord.Embed(
        title=f"{EMOJIS['xp']} XP LEADERBOARDS {EMOJIS['xp']}",
        color=0xffd700
    )
    
    # Server leaderboard
    server_text = ""
    for i, (user_id, xp) in enumerate(top_server):
        user = bot.get_user(user_id)
        username = user.display_name if user else f"Unknown User ({user_id})"
        level, _, _ = calculate_level(xp)
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
        server_text += f"{medal} **{username}** - Level {level} ({xp} XP)\n"
    
    embed.add_field(name="🏠 SERVER LEADERBOARD", value=server_text or "No data yet!", inline=False)
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**📅 WEEKLY LEADERBOARD**",
        inline=False
    )
    
    # Weekly leaderboard
    weekly_text = ""
    for i, (user_id, weekly_xp) in enumerate(top_weekly):
        user = bot.get_user(user_id)
        username = user.display_name if user else f"Unknown User ({user_id})"
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
        weekly_text += f"{medal} **{username}** - {weekly_xp} XP\n"
    
    embed.add_field(name="Weekly Rankings", value=weekly_text or "No data yet!", inline=False)
    
    if weekly_text:
        embed.set_footer(text="Weekly leaderboard resets every Monday!")
    
    await ctx.send(embed=embed)

# Command: XP Roles
@bot.command()
async def xproles(ctx):
    c = db.conn.cursor()
    level_roles = c.execute(
        "SELECT level, role_id FROM level_roles WHERE guild_id = ? ORDER BY level",
        (ctx.guild.id,)
    ).fetchall()
    
    embed = discord.Embed(
        title=f"{EMOJIS['xp']} LEVEL ROLES {EMOJIS['xp']}",
        description="Roles you can earn by reaching certain levels:",
        color=0x7289da
    )
    
    if level_roles:
        roles_text = ""
        for level, role_id in level_roles:
            role = ctx.guild.get_role(role_id)
            if role:
                roles_text += f"**Level {level}**: {role.mention}\n"
        
        embed.description = roles_text
    else:
        embed.description = "No level roles set up yet! Admins can use `-xpperk <level> <role>` to add them."
    
    await ctx.send(embed=embed)

# Command: Boost Claim
@bot.command()
async def boostclaim(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    # Check which boost role user has
    guild_config = db.get_server_config(ctx.guild.id)
    
    if not guild_config:
        await ctx.send(f"{EMOJIS['alert']} No boost roles configured on this server!")
        return
    
    boost_level = 0
    member = ctx.guild.get_member(ctx.author.id)
    
    if guild_config.get('boost3_role'):
        boost_role = ctx.guild.get_role(guild_config['boost3_role'])
        if boost_role and boost_role in member.roles:
            boost_level = 3
    elif guild_config.get('boost2_role'):
        boost_role = ctx.guild.get_role(guild_config['boost2_role'])
        if boost_role and boost_role in member.roles:
            boost_level = 2
    elif guild_config.get('boost1_role'):
        boost_role = ctx.guild.get_role(guild_config['boost1_role'])
        if boost_role and boost_role in member.roles:
            boost_level = 1
    
    if boost_level == 0:
        await ctx.send(f"{EMOJIS['alert']} You don't have any boost role! Boost the server to claim rewards.")
        return
    
    # Check if already claimed this month
    current_month = datetime.datetime.now().strftime("%Y-%m")
    if user_data['last_boost_claim'] == current_month:
        await ctx.send(f"{EMOJIS['alert']} You've already claimed your boost rewards this month!")
        return
    
    # Give rewards
    rewards = BOOST_REWARDS[boost_level]
    for currency, amount in rewards.items():
        db.update_user_currency(ctx.author.id, currency, amount)
    
    # Update last claim
    c = db.conn.cursor()
    c.execute("UPDATE users SET last_boost_claim = ? WHERE user_id = ?", (current_month, ctx.author.id))
    db.conn.commit()
    
    embed = discord.Embed(
        title=f"{EMOJIS[f'boost{boost_level}']} BOOST REWARDS CLAIMED! {EMOJIS[f'boost{boost_level}']}",
        description=f"Thank you for boosting the server! Here are your monthly rewards:",
        color=0xff69b4
    )
    
    reward_text = "\n".join([f"{EMOJIS[currency]} {amount} {currency.capitalize()}" 
                           for currency, amount in rewards.items()])
    embed.add_field(name="🎁 Rewards", value=reward_text, inline=False)
    
    embed.add_field(
        name="💫 Thank You!",
        value="Your support helps keep the server amazing! We appreciate you! 💖",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Command: Flip Coin
@bot.command()
async def flip(ctx):
    result = random.choice(['Heads', 'Tails'])
    await ctx.send(f"🎲 {ctx.author.mention} flipped a coin and got **{result}**!")

# Command: Avatar
@bot.command()
async def av(ctx, user: discord.Member = None):
    target = user or ctx.author
    embed = discord.Embed(title=f"{target.display_name}'s Avatar", color=0x00ff00)
    embed.set_image(url=target.display_avatar.url)
    await ctx.send(embed=embed)

# Command: Emoji
@bot.command()
async def em(ctx, emoji: discord.Emoji):
    embed = discord.Embed(title=f"Emoji: {emoji.name}", color=0x00ff00)
    embed.set_image(url=emoji.url)
    await ctx.send(embed=embed)

@em.error
async def em_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"{EMOJIS['alert']} Please provide a valid custom emoji from this server!")

# UPDATED: Chances command with cleaned up descriptions
@bot.command()
async def chances(ctx):
    embed = discord.Embed(
        title="🎰 CHANCE PERCENTAGES 🎰",
        description="Here are the chances for getting various items:",
        color=0x9b59b6
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**📦 BOX TYPES**",
        inline=False
    )
    
    embed.add_field(
        name="Box Distribution",
        value="""**Small Box**: 50% (2 draws)
**Regular Box**: 25% (4 draws)  
**Big Box**: 15% (7 draws)
**Mega Box**: 5% (10 draws)
**Omega Box**: 1% (20 draws)
**Ultra Box**: 0.1% (35 draws)""",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**💰 BOX REWARDS**",
        inline=False
    )
    
    embed.add_field(
        name="Reward Distribution",
        value="""**Planks**: 35.9%
**Stone**: 25%
**Iron**: 20%
**Copper**: 12.7%
**Silver**: 4%
**Gold**: 2%
**Diamonds**: 0.1%
**Mystery Box**: 0.1%
**Magic Key**: 0.1%
**Ultra Box**: 0.1%""",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**🎁 MYSTERY BOX REWARDS**",
        inline=False
    )
    
    embed.add_field(
        name="Mystery Box Distribution",
        value="""**Ultra Box + 3 Diamonds**: 20%
**Epic/Mythic/Legendary Characters**: 30%
**500 Gold**: 10%
**20 Diamonds**: 1%
**1000 Iron**: 29%
**Magic Key**: 10%""",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**🎁 ARTIFACT BOX**",
        inline=False
    )
    
    embed.add_field(
        name="Artifact Box Rewards",
        value="""**1-2 Artifacts**: 100% guaranteed
Unlock with 1000 Copper + 1 Magic Key""",
        inline=False
    )
    
    embed.add_field(
        name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        value="**⭐ STARR DROPS**",
        inline=False
    )
    
    embed.add_field(
        name="Drop Rarity",
        value="""**Rare**: 50%
**Super Rare**: 32%
**Epic**: 12%
**Mythic**: 4.9%
**Legendary**: 1%
**Ultra Legendary**: 0.1%""",
        inline=False
    )
    
    await ctx.send(embed=embed)

# NEW: Balance command - FIXED: Copper display
@bot.command()
async def bal(ctx):
    user_data = db.get_user(ctx.author.id)
    if not user_data:
        db.create_user(ctx.author.id)
        user_data = db.get_user(ctx.author.id)
    
    embed = discord.Embed(
        title=f"💰 {ctx.author.display_name}'s BALANCE 💰",
        color=0xffd700
    )
    
    embed.add_field(
        name="Basic Resources",
        value=f"{EMOJIS['planks']} **Planks:** {user_data['planks']}\n"
              f"{EMOJIS['stone']} **Stone:** {user_data['stone']}\n"
              f"{EMOJIS['iron']} **Iron:** {user_data['iron']}\n"
              f"{EMOJIS['copper']} **Copper:** {user_data['copper']}",
        inline=True
    )
    
    embed.add_field(
        name="Premium Resources",
        value=f"{EMOJIS['silver']} **Silver:** {user_data['silver']}\n"
              f"{EMOJIS['gold']} **Gold:** {user_data['gold']}\n"
              f"{EMOJIS['diamonds']} **Diamonds:** {user_data['diamonds']}\n"
              f"{EMOJIS['magic_key']} **Magic Keys:** {user_data['magic_keys']}",
        inline=True
    )
    
    embed.add_field(
        name="Special Currencies",
        value=f"{EMOJIS['aura']} **Aura:** {user_data['aura']}",
        inline=True
    )
    
    await ctx.send(embed=embed)

# UPDATED: Help command - REMOVED sauce system commands
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title=f"🌟 {bot.user.name} COMMAND CENTER 🌟",
        description="Welcome to the ultimate gaming experience! Here are all available commands:",
        color=0x7289da
    )
    
    embed.add_field(
        name="🎮 LEVEL & XP COMMANDS",
        value="""```-profile - View your amazing profile
-xplevel - Check your level progress  
-xp - Learn about the XP system
-xpleaderboard - See who's on top
-xproles - Available level rewards```""",
        inline=False
    )
    
    embed.add_field(
        name="🎰 GACHA & ECONOMY",
        value="""```-bal - Check your wealth
-box - Open mysterious boxes
-catch - Catch Starr Drops
-daily - Claim daily rewards
-weekly - Claim weekly rewards
-sugarrush - Triple box rewards for 10 minutes (once daily)
-shop - Browse awesome skins
-buy - Purchase skins
-trade - Exchange currencies```""",
        inline=False
    )
    
    embed.add_field(
        name="🏆 COLLECTION & PROGRESS",
        value="""```-characters - Your character collection
-artifacts - Your artifact collection  
-quests - Your daily quests
-badges - Your earned badges
-city - View city progress
-upgrade - Upgrade buildings
-collect - Collect city resources
-cityproduction - Production rates```""",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ BATTLE SYSTEM",
        value="""```-battle pve <character> - Battle AI
-battle pvp @user <character> - Challenge
-battleaccept @user <character> - Accept```""",
        inline=False
    )
    
    embed.add_field(
        name="💫 GOLDEN PASS SYSTEM",
        value="""```-goldenpass - Check pass progress
-passrewards - See monthly rewards```""",
        inline=False
    )
    
    embed.add_field(
        name="🎪 FUN & SOCIAL",
        value="""```-aura - Check your aura
-aura @user - Give aura to someone
-auraleaderboard - Aura rankings
-flip - Flip a coin
-av @user - Show avatar
-em :emoji: - Show emoji
-guessnumber - Number guessing game```""",
        inline=False
    )
    
    embed.add_field(
        name="📊 LEADERBOARDS",
        value="""```-xpleaderboard - XP rankings
-battleleaderboard - Battle wins```""",
        inline=False
    )
    
    embed.add_field(
        name="🔧 UTILITY & INFO",
        value="""```-tutorial - Beginner's guide
-chances - See all percentages
-openbox - Open your boxes
-artifactsbox - Unlock artifact boxes```""",
        inline=False
    )
    
    embed.set_footer(text="Use - before each command • Admins: Use -helpadmin for admin commands")
    await ctx.send(embed=embed)

# UPDATED: Help Admin command with sauce system
@bot.command()
async def helpadmin(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(f"{EMOJIS['alert']} You need administrator permissions to use this command!")
        return
        
    embed = discord.Embed(
        title="⚙️ ADMIN COMMAND CENTER ⚙️",
        description="Administrator commands for server management:",
        color=0xff0000
    )
    
    embed.add_field(
        name="🎯 XP & LEVEL SYSTEM",
        value="""```-xpboost 1/2 - Set art/clip channels
-xpperk <level> <role> - Set level reward role
-announcementchannel - Set announcement channel```""",
        inline=False
    )
    
    embed.add_field(
        name="🎰 GACHA SYSTEM",
        value="""```-spawnchannel <channel> - Set Starr Drop channel```""",
        inline=False
    )
    
    embed.add_field(
        name="💫 BOOST SYSTEM",
        value="""```-boost1 @role - Set Boost 1 role (2x XP)
-boost2 @role - Set Boost 2 role (2.5x XP)
-boost3 @role - Set Boost 3 role (3x XP)```""",
        inline=False
    )
    
    embed.add_field(
        name="📢 POP-UP SYSTEM",
        value="""```-popupchannel #channel - Set pop-up channel
-popupcooldown <min> - Set pop-up frequency
-popuptoggle - Enable/disable pop-ups
-popupconfig - Show pop-up settings
-popupping @role - Set pop-up ping role```""",
        inline=False
    )
    
    embed.add_field(
        name="🏅 BADGE SYSTEM",
        value="""```-setmaster @role - Set Master Badge role
-setultra @role - Set Ultra Badge role  
-setultimate @role - Set Ultimate Badge role```""",
        inline=False
    )
    
    embed.add_field(
        name="🎉 EVENT SYSTEM",
        value="""```-event double_xp <hours> - Start double XP event
-event double_currency <hours> - Start double currency event
-event end - End all active events
-event status - Show active events```""",
        inline=False
    )
    
    embed.add_field(
        name="🎁 REWARD SYSTEM",
        value="""```-givecurrency @user <amount> <type> - Give currency to user
-givebox @user <type> - Give box to user
-giveall <type> <amount> - Give to all members```""",
        inline=False
    )
    
    embed.add_field(
        name="👑 SAUCE SYSTEM",
        value="""```-sauce setrole @role - Set Sauce role
-givebling @user <amount> - Give Bling
-removebling @user <amount> - Remove Bling
-givestrick @user <amount> - Give stricks
-removestrick @user <amount> - Remove stricks```""",
        inline=False
    )
    
    embed.set_footer(text="Administrator commands - Use with care! 🔧")
    await ctx.send(embed=embed)

# NEW: Remove Bling command for admins
@bot.command()
@commands.has_permissions(administrator=True)
async def removebling(ctx, user: discord.Member, amount: int):
    user_data = db.get_user(user.id)
    if not user_data:
        await ctx.send(f"{EMOJIS['alert']} User not found in database!")
        return
    
    current_bling = user_data['bling']
    if amount > current_bling:
        amount = current_bling  # Remove all bling if amount exceeds current
    
    db.update_user_bling(user.id, -amount)
    await ctx.send(f"{EMOJIS['bling']} Removed **{amount} Bling** from {user.mention}! They now have {current_bling - amount} Bling.")

# Admin Commands

# Command: XP Boost Channel Setup
@bot.command()
@commands.has_permissions(administrator=True)
async def xpboost(ctx, channel_type: int):
    if channel_type not in [1, 2]:
        await ctx.send(f"{EMOJIS['alert']} Invalid channel type! Use 1 for art channel or 2 for clip channel.")
        return
    
    c = db.conn.cursor()
    
    if channel_type == 1:
        db.update_server_config(ctx.guild.id, art_channel=ctx.channel.id)
        message = "Art channel set! Users will get 200 XP for sharing arts here."
    else:
        db.update_server_config(ctx.guild.id, clip_channel=ctx.channel.id)
        message = "Clip channel set! Users will get 100 XP for sending clips here."
    
    await ctx.send(f"{EMOJIS['boost1'] if channel_type == 1 else EMOJIS['boost2']} {message}")

# Command: Set Level Role
@bot.command()
@commands.has_permissions(administrator=True)
async def xpperk(ctx, level: int, role: discord.Role):
    if level < 1 or level > 100:
        await ctx.send(f"{EMOJIS['alert']} Level must be between 1 and 100!")
        return
    
    c = db.conn.cursor()
    c.execute("INSERT OR REPLACE INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)",
             (ctx.guild.id, level, role.id))
    db.conn.commit()
    
    await ctx.send(f"{EMOJIS['boost3']} Level {level} reward set to {role.mention}!")

# Command: Set Starr Drop Channel
@bot.command()
@commands.has_permissions(administrator=True)
async def spawnchannel(ctx, channel: discord.TextChannel = None):
    target_channel = channel or ctx.channel
    
    db.update_server_config(ctx.guild.id, spawn_channel=target_channel.id)
    
    await ctx.send(f"{EMOJIS['raredrop']} Starr Drops will now spawn in {target_channel.mention} every hour!")

# Command: Set Boost Role
@bot.command()
@commands.has_permissions(administrator=True)
async def boost1(ctx, role: discord.Role):
    db.update_server_config(ctx.guild.id, boost1_role=role.id)
    
    await ctx.send(f"{EMOJIS['boost1']} Boost 1 role set to {role.mention}! (2x XP, 2x Starr Drops)")

@bot.command()
@commands.has_permissions(administrator=True)
async def boost2(ctx, role: discord.Role):
    db.update_server_config(ctx.guild.id, boost2_role=role.id)
    
    await ctx.send(f"{EMOJIS['boost2']} Boost 2 role set to {role.mention}! (2.5x XP, 3x Starr Drops)")

@bot.command()
@commands.has_permissions(administrator=True)
async def boost3(ctx, role: discord.Role):
    db.update_server_config(ctx.guild.id, boost3_role=role.id)
    
    await ctx.send(f"{EMOJIS['boost3']} Boost 3 role set to {role.mention}! (3x XP, 3x Starr Drops)")

# Command: Set Announcement Channel
@bot.command()
@commands.has_permissions(administrator=True)
async def announcementchannel(ctx, channel: discord.TextChannel = None):
    target_channel = channel or ctx.channel
    
    db.update_server_config(ctx.guild.id, announcement_channel=target_channel.id)
    
    await ctx.send(f"{EMOJIS['alert']} Announcement channel set to {target_channel.mention}! Tier-up notifications will be sent here.")

# Command: Set Pop-up Ping Role
@bot.command()
@commands.has_permissions(administrator=True)
async def popupping(ctx, role: discord.Role = None):
    if role:
        db.update_server_config(ctx.guild.id, popup_ping_role=role.id)
        await ctx.send(f"{EMOJIS['pop']} Pop-up ping role set to {role.mention}! This role will be pinged when pop-ups appear.")
    else:
        db.update_server_config(ctx.guild.id, popup_ping_role=None)
        await ctx.send(f"{EMOJIS['pop']} Pop-up ping role removed! Pop-ups will no longer ping any role.")

# Pop-up Admin Commands
@bot.command()
@commands.has_permissions(administrator=True)
async def popupchannel(ctx, channel: discord.TextChannel = None):
    target_channel = channel or ctx.channel
    
    db.update_popup_config(ctx.guild.id, channel_id=target_channel.id)
    
    await ctx.send(f"{EMOJIS['pop']} Pop-up questions will now spawn in {target_channel.mention}!")

@bot.command()
@commands.has_permissions(administrator=True)
async def popupcooldown(ctx, cooldown: int):
    if cooldown < 1 or cooldown > 60:
        await ctx.send(f"{EMOJIS['alert']} Cooldown must be between 1 and 60 minutes!")
        return
    
    db.update_popup_config(ctx.guild.id, cooldown=cooldown)
    
    await ctx.send(f"{EMOJIS['pop']} Pop-up cooldown set to {cooldown} minutes!")

@bot.command()
@commands.has_permissions(administrator=True)
async def popuptoggle(ctx):
    config = db.get_popup_config(ctx.guild.id)
    new_status = 0 if config['popup_enabled'] else 1
    
    db.update_popup_config(ctx.guild.id, enabled=new_status)
    
    status = "enabled" if new_status else "disabled"
    await ctx.send(f"{EMOJIS['pop']} Pop-up questions are now **{status}**!")

@bot.command()
@commands.has_permissions(administrator=True)
async def popupconfig(ctx):
    config = db.get_popup_config(ctx.guild.id)
    guild_config = db.get_server_config(ctx.guild.id)
    
    embed = discord.Embed(
        title=f"{EMOJIS['pop']} POP-UP CONFIGURATION {EMOJIS['pop']}",
        color=0x00ff00
    )
    
    channel = ctx.guild.get_channel(config['popup_channel']) if config['popup_channel'] else None
    ping_role = ctx.guild.get_role(guild_config['popup_ping_role']) if guild_config and guild_config['popup_ping_role'] else None
    status = "✅ Enabled" if config['popup_enabled'] else "❌ Disabled"
    
    embed.add_field(
        name="Current Settings",
        value=f"**Status:** {status}\n"
              f"**Channel:** {channel.mention if channel else 'Not set'}\n"
              f"**Ping Role:** {ping_role.mention if ping_role else 'Not set'}\n"
              f"**Cooldown:** {config['popup_cooldown']} minutes\n"
              f"**Spawn Chance:** 1 in {config['popup_cooldown']} chance per minute\n"
              f"**Timer:** 60 seconds per pop-up",
        inline=False
    )
    
    embed.add_field(
        name="Commands",
        value="`-popupchannel #channel` - Set pop-up channel\n"
              "`-popupcooldown <minutes>` - Set spawn frequency\n"
              "`-popuptoggle` - Enable/disable pop-ups\n"
              "`-popupping @role` - Set pop-up ping role\n"
              "`-popupconfig` - Show current settings",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Badge Role Admin Commands
@bot.command()
@commands.has_permissions(administrator=True)
async def setmaster(ctx, role: discord.Role):
    db.update_server_config(ctx.guild.id, master_badge_role=role.id)
    
    await ctx.send(f"{EMOJIS['master']} Master Badge role set to {role.mention}!")

@bot.command()
@commands.has_permissions(administrator=True)
async def setultra(ctx, role: discord.Role):
    db.update_server_config(ctx.guild.id, ultra_badge_role=role.id)
    
    await ctx.send(f"{EMOJIS['ultra']} Ultra Badge role set to {role.mention}!")

@bot.command()
@commands.has_permissions(administrator=True)
async def setultimate(ctx, role: discord.Role):
    db.update_server_config(ctx.guild.id, ultimate_badge_role=role.id)
    
    await ctx.send(f"{EMOJIS['ultimate']} Ultimate Badge role set to {role.mention}!")

# Event System Admin Commands
@bot.command()
@commands.has_permissions(administrator=True)
async def event(ctx, event_type: str, duration: int = 1):
    if event_type == "double_xp":
        db.add_active_event(ctx.guild.id, 'double_xp', 2.0, duration)
        await ctx.send("🎉 **Double XP Event Started!**\nAll XP gains are doubled for {duration} hours!")
    
    elif event_type == "double_currency":
        db.add_active_event(ctx.guild.id, 'double_currency', 2.0, duration)
        await ctx.send("💰 **Double Currency Event Started!**\nAll currency gains are doubled for {duration} hours!")
    
    elif event_type == "end":
        db.clear_expired_events()
        await ctx.send("🛑 **All active events have been ended!**")
    
    elif event_type == "status":
        active_events = db.get_active_events(ctx.guild.id)
        if not active_events:
            await ctx.send("📊 **Event Status:** No active events")
        else:
            embed = discord.Embed(title="📊 ACTIVE EVENTS", color=0x00ff00)
            for event in active_events:
                end_time = datetime.datetime.fromisoformat(event['end_time'])
                time_left = end_time - datetime.datetime.now()
                hours_left = max(0, int(time_left.total_seconds() // 3600))
                minutes_left = max(0, int((time_left.total_seconds() % 3600) // 60))
                
                embed.add_field(
                    name=f"{event['event_type'].replace('_', ' ').title()}",
                    value=f"Multiplier: {event['multiplier']}x\nTime Left: {hours_left}h {minutes_left}m",
                    inline=True
                )
            await ctx.send(embed=embed)
    
    else:
        await ctx.send(f"{EMOJIS['alert']} Available events: `double_xp`, `double_currency`, `end`, `status`")

# Reward System Admin Commands
@bot.command()
@commands.has_permissions(administrator=True)
async def givecurrency(ctx, user: discord.Member, amount: int, currency_type: str):
    valid_currencies = ['planks', 'stone', 'iron', 'copper', 'silver', 'gold', 'diamonds']
    
    if currency_type not in valid_currencies:
        await ctx.send(f"{EMOJIS['alert']} Invalid currency type! Available: {', '.join(valid_currencies)}")
        return
    
    db.update_user_currency(user.id, currency_type, amount)
    
    await ctx.send(f"🎁 {EMOJIS[currency_type]} Gave **{amount} {currency_type.capitalize()}** to {user.mention}!")

@bot.command()
@commands.has_permissions(administrator=True)
async def givebox(ctx, user: discord.Member, box_type: str):
    valid_boxes = ['small', 'regular', 'big', 'mega', 'omega', 'ultra', 'mystery', 'artifact']
    
    if box_type not in valid_boxes:
        await ctx.send(f"{EMOJIS['alert']} Invalid box type! Available: {', '.join(valid_boxes)}")
        return
    
    if box_type == 'mystery':
        db.add_box_to_user(user.id, 'mystery_box')
        await ctx.send(f"🎁 Gave **Mystery Box** to {user.mention}! They can use `-openbox mystery` to open it.")
    elif box_type == 'artifact':
        db.add_box_to_user(user.id, 'artifact_box')
        await ctx.send(f"🎁 Gave **Artifact Box** to {user.mention}! They can use `-artifactsbox` to unlock it.")
    else:
        db.add_box_to_user(user.id, f"{box_type}_box")
        await ctx.send(f"📦 Gave **{box_type.capitalize()} Box** to {user.mention}!")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveall(ctx, item_type: str, amount: int):
    if item_type not in ['planks', 'stone', 'iron', 'copper', 'silver', 'gold', 'diamonds']:
        await ctx.send(f"{EMOJIS['alert']} Invalid item type! Available: planks, stone, iron, copper, silver, gold, diamonds")
        return
    
    # Get all users in the database
    c = db.conn.cursor()
    users = c.execute("SELECT user_id FROM users").fetchall()
    
    # Give currency to all users
    for (user_id,) in users:
        db.update_user_currency(user_id, item_type, amount)
    
    await ctx.send(f"🎁 {EMOJIS[item_type]} Gave **{amount} {item_type.capitalize()}** to all {len(users)} users!")

# FIXED: Set Sauce Role command - proper implementation
@bot.command()
@commands.has_permissions(administrator=True)
async def sauceset(ctx, subcommand: str = None, role: discord.Role = None):
    if not subcommand:
        await ctx.send(f"{EMOJIS['alert']} Please specify a subcommand! Use `-sauce setrole @role`")
        return
    
    if subcommand.lower() == 'setrole':
        if not role:
            await ctx.send(f"{EMOJIS['alert']} Please mention a role! Use `-sauce setrole @role`")
            return
        
        db.update_server_config(ctx.guild.id, sauce_role=role.id)
        await ctx.send(f"{EMOJIS['bling']} Sauce role set to {role.mention}! Users with this role can now use the Sauce system.")
    
    else:
        await ctx.send(f"{EMOJIS['alert']} Invalid subcommand! Use `-sauce setrole @role`")

# Badge checking system - FIXED: Server-specific level checking
async def check_badge_achievements(user_id):
    user_data = db.get_user(user_id)
    if not user_data:
        return
    
    c = db.conn.cursor()
    
    # Check Level Badge - FIXED: This now requires level 100 in any server
    # We need to check all servers the user has XP in
    server_xp_records = c.execute("SELECT xp FROM server_xp WHERE user_id = ?", (user_id,)).fetchall()
    max_level = 0
    for (xp,) in server_xp_records:
        level, _, _ = calculate_level(xp)
        max_level = max(max_level, level)
    
    if max_level >= 100:
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (user_id, "Level Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (user_id, "Level Badge"))
    
    # Check Artifact Badge
    artifact_count = c.execute("SELECT COUNT(*) FROM user_artifacts WHERE user_id = ?", (user_id,)).fetchone()[0]
    if artifact_count >= 15:
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (user_id, "Artifact Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (user_id, "Artifact Badge"))
    
    # Check Skin Badge
    skin_count = c.execute("SELECT COUNT(*) FROM user_skins WHERE user_id = ?", (user_id,)).fetchone()[0]
    if skin_count >= 30:
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (user_id, "Skin Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (user_id, "Skin Badge"))
    
    # Check Character Badge
    char_count = c.execute("SELECT COUNT(*) FROM user_characters WHERE user_id = ?", (user_id,)).fetchone()[0]
    if char_count >= 20:
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (user_id, "Character Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (user_id, "Character Badge"))
    
    # Check City Badge
    buildings = db.get_user_buildings(user_id)
    max_levels = sum([data['max_level'] for data in CITY_BUILDINGS.values()])
    current_levels = sum([b['level'] for b in buildings])
    if current_levels >= max_levels:
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (user_id, "City Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (user_id, "City Badge"))
    
    # Check Daily Badge
    if user_data['daily_streak'] >= 30:
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (user_id, "Daily Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (user_id, "Daily Badge"))
    
    # Check Pass Badge (handled in golden_pass_reset)
    
    # Check Command Badge
    if user_data['commands_used'] >= 5000:
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (user_id, "Command Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (user_id, "Command Badge"))
    
    # Check Drop Badge
    if user_data['drops_caught'] >= 100:
        has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                             (user_id, "Drop Badge")).fetchone()
        if not has_badge:
            c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                     (user_id, "Drop Badge"))
    
    # Check Boost Badge
    if user_data['last_boost_claim']:
        boost_claims = c.execute("SELECT COUNT(*) FROM (SELECT DISTINCT last_boost_claim FROM users WHERE user_id = ? AND last_boost_claim IS NOT NULL)", 
                               (user_id,)).fetchone()[0]
        if boost_claims >= 2:
            has_badge = c.execute("SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?", 
                                 (user_id, "Boost Badge")).fetchone()
            if not has_badge:
                c.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", 
                         (user_id, "Boost Badge"))
    
    db.conn.commit()
    
    # Check for special badge roles
    await check_badge_roles(user_id)

async def check_badge_roles(user_id):
    # This would need to be implemented per guild
    pass

# FIXED: Error handling with proper embed creation
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"{EMOJIS['alert']} Command not found! Use `-help` to see all commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{EMOJIS['alert']} You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"{EMOJIS['alert']} Missing required argument! Use `-help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"{EMOJIS['alert']} Invalid argument provided! Check command usage with `-help`.")
    else:
        # Create an embed for the error message
        embed = discord.Embed(
            title=f"{EMOJIS['alert']} An Error Occurred",
            description=f"```{str(error)}```",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        print(f"Error: {error}")

# Run the bot
if __name__ == "__main__":
    # Initialize active drops dictionary
    active_starr_drops = {}
    
    # Initialize active channel pop-ups dictionary
    bot.active_channel_popups = {}
    
    # Get bot token from environment variable
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN not found in .env file!")
        exit(1)
    
    bot.run(token)
