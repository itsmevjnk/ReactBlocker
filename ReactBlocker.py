
# ReactBlocker - A Python Discord bot for blocking user(s) from adding specific reaction(s).
# <C> 2022 Nguyen Thanh Vinh (itsmevjnk)

import discord
import pickle
from discord.ext import commands
from os.path import exists

intents = discord.Intents.default()
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix="^", intents = intents)
bot_data = {} # dictionary for storing bot's data
if exists("data.pkl"):
    try:
        with open("data.pkl", "rb") as f: bot_data = pickle.load(f)
        print("Loaded bot data from data.pkl")
    except: pass

def add_guild_to_data(guild):
    if not guild.id in dict(bot_data["guilds"]).keys():
        bot_data["guilds"][guild.id] = {
            "usr_exclude": False, # set if reaction blocking applies for everyone except those included in usr_whitelist,
                                  # not set if reaction blocking applies for those included in usr_blacklist
            "usr_whitelist": set(),
            "usr_blacklist": set(),

            "r_exclude": False, # set if all reactions except those included in r_whitelist are blocked,
                                # not set if only reactions in r_blacklist are blocked
            "r_whitelist": set(),
            "r_blacklist": set()
        }

@bot.event
async def on_ready():
    print(f"ReactBlocker is logged in as {bot.user}")
    print("Connected guild(s):")
    for guild in bot.guilds:
        print(f"  {guild.name} (ID: {guild.id})")
        add_guild_to_data(guild)

@bot.event
async def on_guild_join(guild):
    print(f"Joined guild {guild.name} (ID: {guild.id})")
    add_guild_to_data(guild)

@bot.event
async def on_guild_remove(guild):
    print(f"Removed from guild {guild.name} (ID: {guild.id})")
    del bot_data["guilds"][guild.id]

@bot.event
async def on_raw_reaction_add(payload):
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    emoji = payload.emoji
    if emoji.is_custom_emoji(): einfo = str(emoji.id) # custom emoji will be stored as IDs
    else: einfo = emoji.name # unicode emoji will be stored as is
    # print(einfo)
    user = bot.get_user(payload.user_id)
    if not user: user = await bot.fetch_user(payload.user_id)
    print(f"Reaction {einfo} added by user {user.id}") # TODO: comment this out for less spamming
    ginfo = bot_data["guilds"][payload.guild_id]
    if (((ginfo["usr_exclude"] and not user.id in ginfo["usr_whitelist"]) or (not ginfo["usr_exclude"] and user.id in ginfo["usr_blacklist"]))
       and (ginfo["r_exclude"] and not einfo in ginfo["r_whitelist"]) or (not ginfo["r_exclude"] and einfo in ginfo["r_blacklist"])):
        await message.remove_reaction(emoji, user)
        print(f"Blocked reaction {einfo} by user {user.id}")

@bot.command(name="toggle-user")
@commands.has_guild_permissions(manage_messages = True)
async def toggle_user(ctx): # Toggle user include/exclude mode
    bot_data["guilds"][ctx.guild.id]["usr_exclude"] = not bot_data["guilds"][ctx.guild.id]["usr_exclude"]
    await ctx.send("User mode set to " + ("***Exclude***." if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else "***Include***."))

@bot.command(name="toggle-react")
@commands.has_guild_permissions(manage_messages = True)
async def toggle_react(ctx): # Toggle reaction include/exclude mode
    bot_data["guilds"][ctx.guild.id]["r_exclude"] = not bot_data["guilds"][ctx.guild.id]["r_exclude"]
    await ctx.send("Reaction blocking mode set to " + ("***Exclude***." if bot_data["guilds"][ctx.guild.id]["r_exclude"] else "***Include***."))

@bot.command(name="get-user")
@commands.has_guild_permissions(manage_messages = True)
async def get_user(ctx): # Get user include/exclude mode
    await ctx.send("User mode is " + ("***Exclude***." if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else "***Include***."))

@bot.command(name="get-react")
@commands.has_guild_permissions(manage_messages = True)
async def get_react(ctx): # Get reaction include/exclude mode
    await ctx.send("Reaction blocking mode is " + ("***Exclude***." if bot_data["guilds"][ctx.guild.id]["r_exclude"] else "***Include***."))

@bot.command(name="add-user")
@commands.has_guild_permissions(manage_messages = True)
async def add_user(ctx, *args): # Add user(s) to blacklist/whitelist depending on mode
    users = set()
    if len(args) == 0: await ctx.send("At least one user is expected.")
    for arg in args:
        argstr = str(arg)
        if argstr.startswith("<@!") and argstr.endswith(">"): # valid mention
            users.add(int(argstr.replace("<@!", "").replace(">", "")))
        elif argstr.isdigit(): # user ID
            users.add(int(argstr))
        else: await ctx.send(f"Invalid mention/user `{argstr}`.")
    if bot_data["guilds"][ctx.guild.id]["usr_exclude"]:
        bot_data["guilds"][ctx.guild.id]["usr_whitelist"].update(users)
    else:
        bot_data["guilds"][ctx.guild.id]["usr_blacklist"].update(users)
    await ctx.send("Added " + ", ".join([f"`{u}`" for u in users]) + " to the " + ("whitelist." if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else "blacklist."))

@bot.command(name="del-user")
@commands.has_guild_permissions(manage_messages = True)
async def del_user(ctx, *args): # Delete user(s) from blacklist/whitelist depending on mode
    users = set()
    if len(args) == 0: await ctx.send("At least one user is expected.")
    for arg in args:
        argstr = str(arg)
        if argstr.startswith("<@!") and argstr.endswith(">"): # valid mention
            users.add(int(argstr.replace("<@!", "").replace(">", "")))
        elif argstr.isdigit(): # user ID
            users.add(int(argstr))
        else: await ctx.send(f"Invalid mention/user `{argstr}`.")
    for u in users:
        if bot_data["guilds"][ctx.guild.id]["usr_exclude"]:
            bot_data["guilds"][ctx.guild.id]["usr_whitelist"].discard(u)
        else:
            bot_data["guilds"][ctx.guild.id]["usr_blacklist"].discard(u)
    await ctx.send("Deleted " + ", ".join([f"`{u}`" for u in users]) + " from the " + ("whitelist." if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else "blacklist."))

@bot.command(name="lst-user")
@commands.has_guild_permissions(manage_messages = True)
async def lst_user(ctx, *args): # List user(s) in the whitelist/blacklist
    if (bot_data["guilds"][ctx.guild.id]["usr_exclude"] and len(bot_data["guilds"][ctx.guild.id]["usr_whitelist"]) == 0) or (not bot_data["guilds"][ctx.guild.id]["usr_exclude"] and len(bot_data["guilds"][ctx.guild.id]["usr_blacklist"]) == 0):
        await ctx.send("There are currently no users in the " + ("whitelist." if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else "blacklist."))
    else: await ctx.send("List of user(s) in the " + ("whitelist" if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else "blacklist") + ":\n```\n" + "\n".join([str(u) for u in set(bot_data["guilds"][ctx.guild.id]["usr_whitelist"] if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else bot_data["guilds"][ctx.guild.id]["usr_blacklist"])]) + "\n```")

@bot.command(name="add-react")
@commands.has_guild_permissions(manage_messages = True)
async def add_react(ctx, *args): # Add reaction(s) to blacklist/whitelist depending on mode
    reacts = set()
    if len(args) == 0: await ctx.send("At least one reaction is expected.")
    for arg in args:
        reacts.add(str(arg).replace("`", "")) # TODO: check if reaction is valid
    if bot_data["guilds"][ctx.guild.id]["r_exclude"]:
        bot_data["guilds"][ctx.guild.id]["r_whitelist"].update(reacts)
    else:
        bot_data["guilds"][ctx.guild.id]["r_blacklist"].update(reacts)
    await ctx.send("Added " + " ".join(reacts) + " to the " + ("whitelist." if bot_data["guilds"][ctx.guild.id]["r_exclude"] else "blacklist."))

@bot.command(name="del-react")
@commands.has_guild_permissions(manage_messages = True)
async def del_react(ctx, *args): # Delete reaction(s) from the blacklist/whitelist depending on mode
    reacts = set()
    if len(args) == 0: await ctx.send("At least one reaction is expected.")
    for arg in args:
        reacts.add(str(arg).replace("`", "")) # TODO: check if reaction is valid
    for r in reacts:
        if bot_data["guilds"][ctx.guild.id]["r_exclude"]:
            bot_data["guilds"][ctx.guild.id]["r_whitelist"].discard(r)
        else:
            bot_data["guilds"][ctx.guild.id]["r_blacklist"].discard(r)
    await ctx.send("Removed " + " ".join(reacts) + " from the " + ("whitelist." if bot_data["guilds"][ctx.guild.id]["r_exclude"] else "blacklist."))

@bot.command(name="lst-react")
@commands.has_guild_permissions(manage_messages = True)
async def lst_react(ctx, *args): # List reactions(s) in the whitelist/blacklist
    if (bot_data["guilds"][ctx.guild.id]["r_exclude"] and len(bot_data["guilds"][ctx.guild.id]["r_whitelist"]) == 0) or (not bot_data["guilds"][ctx.guild.id]["r_exclude"] and len(bot_data["guilds"][ctx.guild.id]["r_blacklist"]) == 0):
        await ctx.send("There are currently no reactions in the " + ("whitelist." if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else "blacklist."))
    else: await ctx.send("List of reaction(s) in the " + ("whitelist" if bot_data["guilds"][ctx.guild.id]["r_exclude"] else "blacklist") + ": " + " ".join(bot_data["guilds"][ctx.guild.id]["r_whitelist"] if bot_data["guilds"][ctx.guild.id]["usr_exclude"] else bot_data["guilds"][ctx.guild.id]["usr_blacklist"]))

if type(bot_data.get("guilds", None)) != dict: bot_data["guilds"] = {}
bot_token = bot_data.get("token", None)
if type(bot_token) != str:
    bot_token = input("Please enter the bot's token: ")
    bot_data["token"] = bot_token
print("Starting ReactBlocker...")
try: bot.run(bot_token)
finally:
    with open("data.pkl", "wb") as f: pickle.dump(bot_data, f)
    print("Saved bot data to data.pkl")