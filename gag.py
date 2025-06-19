import discord
from discord.ext import commands, tasks
import requests
import os

api_url = 'https://growagardenapi.vercel.app/api/stock/GetStock'
valid_types = ['egg', 'stock', 'gear', 'cosmetic', 'event']
channel_settings = {}

def format_stock_list(items):
    if not items:
        return "nothing here right now"
    return "\n".join(f"{item.get('name', 'unnamed')} — {item.get('stock', '?')}" for item in items)

async def get_stock_by_type(stock_type):
    try:
        res = requests.get(api_url)
        data = res.json().get("Data", {})
        return {
            'event': data.get('honey', []),
            'stock': data.get('seeds', []),
            'cosmetic': data.get('cosmetics', []),
            'gear': data.get('gear', []),
            'egg': data.get('egg', [])
        }.get(stock_type, [])
    except Exception as e:
        print(f"failed to fetch stock: {e}")
        return None

async def get_all_stock():
    try:
        res = requests.get(api_url)
        data = res.json().get("Data", {})
        return {
            'egg': data.get('egg', []),
            'stock': data.get('seeds', []),
            'gear': data.get('gear', []),
            'cosmetic': data.get('cosmetics', []),
            'event': data.get('honey', [])
        }
    except Exception as e:
        print(f"failed to fetch all stock: {e}")
        return None

async def has_permissions(channel):
    perms = channel.permissions_for(channel.guild.me)
    return perms.send_messages and perms.view_channel

@bot.event
async def on_ready():
    send_updates.start()

@bot.command(name="set")
@commands.has_permissions(administrator=True)
async def set_updates(ctx, channel: discord.TextChannel = None, stock_type: str = None, ping: str = None, *, role: discord.Role = None):
    if not channel or not stock_type or ping is None:
        return await ctx.send(embed=discord.Embed(
            description="Command: **set**\n\nSends automatic stock updates for selected item types like eggs, gear, etc to a specific channel, with optional role pings.```fix\nUsage: ,set #channel <type: egg/stock/gear/cosmetic/event/all> <true/false> [@role if true]```",
            color=0xffffff
        ))

    if not await has_permissions(channel):
        return await ctx.send(embed=discord.Embed(
            description=f"> {ctx.author.mention}: i can't send messages or view {channel.mention}",
            color=0xffffff
        ))

    stock_type = stock_type.lower()
    if stock_type not in valid_types and stock_type != 'all':
        return await ctx.send(embed=discord.Embed(
            description=f"> {ctx.author.mention}: choose: egg, stock, gear, cosmetic, event, all",
            color=0xffffff
        ))

    ping_enabled = ping.lower() == 'true'
    if ping_enabled and not role:
        return await ctx.send(embed=discord.Embed(
            description=f"> {ctx.author.mention}: you must mention a role if ping is set to true",
            color=0xffffff
        ))

    key = channel.id
    if key not in channel_settings:
        channel_settings[key] = []
    types_to_add = valid_types if stock_type == 'all' else [stock_type]
    for t in types_to_add:
        channel_settings[key] = [entry for entry in channel_settings[key] if entry['type'] != t]
        channel_settings[key].append({
            'type': t,
            'ping': ping_enabled,
            'role': role
        })

    await ctx.send(embed=discord.Embed(
        description=f"> {ctx.author.mention}: updates set for {', '.join(types_to_add)} in {channel.mention}",
        color=0xffffff
    ))

@set_updates.error
async def set_updates_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(
            description=f"> {ctx.author.mention}: you need to be an admin to use this command",
            color=0xffffff
        ))
    else:
        print(f"error in set command: {error}")

@bot.command(name="unset")
@commands.has_permissions(administrator=True)
async def unset_updates(ctx, channel: discord.TextChannel = None, stock_type: str = None):
    if not channel or not stock_type:
        return await ctx.send(embed=discord.Embed(
            description="Command: **unset**\n\nStops automatic stock updates for a specific item type in a chosen channel by removing previously set notifications```fix\nUsage: ,unset #channel <type: egg/stock/gear/cosmetic/event/all>```",
            color=0xffffff
        ))

    if not await has_permissions(channel):
        return await ctx.send(embed=discord.Embed(
            description=f"> {ctx.author.mention}: i can't send messages or view {channel.mention}",
            color=0xffffff
        ))

    stock_type = stock_type.lower()
    if stock_type not in valid_types and stock_type != 'all':
        return await ctx.send(embed=discord.Embed(
            description=f"> {ctx.author.mention}: choose from: egg, stock, gear, cosmetic, event, all",
            color=0xffffff
        ))

    key = channel.id
    if key not in channel_settings:
        return await ctx.send(embed=discord.Embed(
            description=f"> {ctx.author.mention}: no updates are set for that channel",
            color=0xffffff
        ))

    if stock_type == 'all':
        channel_settings.pop(key)
    else:
        channel_settings[key] = [entry for entry in channel_settings[key] if entry['type'] != stock_type]
        if not channel_settings[key]:
            channel_settings.pop(key)

    await ctx.send(embed=discord.Embed(
        description=f"> {ctx.author.mention}: updates removed for {stock_type} in {channel.mention}",
        color=0xffffff
    ))

@unset_updates.error
async def unset_updates_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(
            description=f"> {ctx.author.mention}: you need to be an admin to use this command",
            color=0xffffff
        ))
    else:
        print(f"error in unset command: {error}")

@tasks.loop(minutes=5)
async def send_updates():
    for channel_id, configs in channel_settings.items():
        channel = bot.get_channel(channel_id)
        if not channel or not await has_permissions(channel):
            continue

        for entry in configs:
            try:
                if entry['type'] == 'all':
                    stock_data = await get_all_stock()
                    if stock_data is None:
                        continue
                    description = ""
                    for stock_type, items in stock_data.items():
                        description += f"**{stock_type}**\n{format_stock_list(items)}\n\n"
                    embed = discord.Embed(title="current stock", description=description, color=0xffffff)
                else:
                    stock = await get_stock_by_type(entry['type'])
                    if stock is None:
                        continue
                    embed = discord.Embed(title=f"{entry['type']} stock", description=format_stock_list(stock), color=0xffffff)

                if entry['ping'] and entry['role']:
                    await channel.send(content=entry['role'].mention, embed=embed)
                else:
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"error sending update in {channel_id}: {e}")
