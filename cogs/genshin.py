import genshinstats as gs
import asyncio
import aiohttp
import discord
import os
import sys
import json

from cachetools import TTLCache
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from psutil import users
from utils import permissions, http, grouper, send_pages, to_thread, default
from typing import Any, Optional, TypeVar, Union , Dict
from datetime import datetime, timedelta


GENSHIN_LOGO = "https://yt3.ggpht.com/ytc/AKedOLRtloUOEZcHaRhCYeKyHRg31e54hCcIaVfQ7IN-=s900-c-k-c0x00ffffff-no-rj"
base = "https://webstatic-sea.hoyolab.com/app/community-game-records-sea/images/"
abyss_banners = {
    0:  base + "pc-abyss-bg.dc0c3ac6.png",
    9:  base + "pc9.1f1920d2.png",
    10: base + "pc10.b0019d93.png",
    11: base + "pc11.38507e1e.png",
    12: base + "pc12.43f28b10.png",
}
T = TypeVar('T')
if not os.path.isfile("config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open("config.json") as file:
        config = json.load(file)

def _item_color(rarity: int = 0) -> int:
    if rarity == 5:
        return 0xf1c40f # gold
    elif rarity == 4:
        return 0x9b59b6 # purple
    elif rarity == 3:
        return 0x3498db # blue
    else:
        return 0xffffff # white

class GenshinImpact(commands.Cog):
    """Show info about Genshin Impact users using mihoyo's api"""
    

    def __init__(self, bot):
        self.bot = bot
        gs.set_cookies(config['cookie_file'])
        self.cache = TTLCache(1024, 3600)
        gs.install_cache(self.cache)

    def _element_emoji(self, element: str) -> discord.Emoji:
        g = self.bot.get_guild(570841314200125460) or self.bot.guilds[0]
        e = discord.utils.get(g.emojis, name=element.lower())
        try:
            assert e
            return e
    # many more statements like this
        except AssertionError:
            return e

    async def _user_uid(self, ctx: commands.Context, user: Union[discord.User, discord.Member, int, None]) -> int:
        """Helper function to either get the uid or raise an error"""
        if isinstance(user, int):
            return user

    

    @commands.group(invoke_without_command=True, aliases=['gs', 'gistats', 'player'])
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def playerstats(self, ctx: commands.Context, usr: int):
        """Shows info about a genshin player"""
        uid = await self._user_uid(ctx, usr)

        await ctx.trigger_typing()
        try:
            data = await to_thread(gs.get_user_stats, uid)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return
        
        await ctx.trigger_typing()

        getdata = data["stats"]
        pages = []
        
        stats_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic user stats"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url=GENSHIN_LOGO
        )
        for field, value in data['stats'].items():
            stats_embed.add_field(
                name=field.replace('_', ' '),
                value=value
            )
        pages.append(stats_embed)

        exploration_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic exploration info"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url=GENSHIN_LOGO
        )
        for city in reversed(data['explorations']):
            exploration_embed.add_field(
                name=city['name'],
                value=f"explored {city['explored']}% ({city['type']} lvl {city['level']})\n" + 
                      ', '.join(f"{i['name']} lvl {i['level']}" for i in city['offerings']),
                inline=False
            )
        if len(data['teapots']) >= 1:
            teapot = data['teapots'][0]
            exploration_embed.add_field(
                name="Teapot",
                value=f"Adeptal energy: {teapot['comfort']} (level {teapot['level']})\n"
                      f"Placed items: {teapot['placed_items']}\n"
                      f"Unlocked styles: {', '.join(i['name'] for i in data['teapots'])}"
            )
        
        pages.append(exploration_embed)

        character_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic character info"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url=GENSHIN_LOGO
        )
        characters = sorted(data['characters'], key=lambda x: x['level'], reverse=True)
        for chunk in grouper(characters, 15):
            embed = character_embed.copy()
            for char in chunk:
                embed.add_field(
                    name=f"{char['name']}",
                    value=f"{'★'*char['rarity']} {char['element']}\nlvl {char['level']}, friendship {char['friendship']}"
                )
            pages.append(embed)

        await send_pages(ctx, ctx, pages)

    async def _genshin_abyss_new(self, uid: int) -> discord.Embed:
        """Gets the embeds for spiral abyss history for a specific season."""
        data = gs.get_spiral_abyss(uid, True)
        if data['stats']['total_battles'] == 0:
            return []

        star = self._element_emoji('abyss_star')
        embeds = [
            discord.Embed(
                colour=0xffffff,
                title=f"Spiral abyss info of {uid}",
                description="Overall spiral abyss stats"
            ).add_field(
                name="Stats",
                value=f"Max floor: {data['stats']['max_floor']} Total stars: {data['stats']['total_stars']}\n"
                      f"Total battles: {data['stats']['total_battles']} Total wins: {data['stats']['total_wins']}",
                inline=False
            ).add_field(
                name="Character ranks",
                value="\n".join(f"**{k.replace('_',' ')}**: " + ', '.join(f"{i['name']} ({i['value']})" for i in v[:4]) for k,v in data['character_ranks'].items() if v) or "avalible only for floor 9 or above",
                inline=False
            ).set_author(
                name=f"Season {data['season']} ({data['season_start_time'].replace('-', '/')} - {data['season_end_time'].replace('-', '/')})\n"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            ).set_image(
                url=abyss_banners[0]
            )
        ]
        for floor in data['floors']:
            embed = discord.Embed(
                colour=0xffffff,
                title=f"Spiral abyss info of {uid}",
                description=f"Floor **{floor['floor']}** (**{floor['stars']}**{star})",
                timestamp=datetime.fromisoformat(floor['start'])
            ).set_author(
                name=f"Season {data['season']} ({data['season_start_time'].replace('-', '/')} - {data['season_end_time'].replace('-', '/')})\n"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            ).set_image(
                url=abyss_banners.get(floor['floor'], discord.Embed.Empty)
            )
            for chamber in floor['chambers']:
                for battle in chamber['battles']:
                    embed.add_field(
                        name=f"Chamber {chamber['chamber']}" + (f"{', 1st' if battle['half']==1 else ', 2nd'} Half " if chamber['has_halves'] else '') + f" ({chamber['stars']}{star})",
                        value='\n'.join(f"{i['name']} (lvl {i['level']})" for i in battle['characters']),
                        inline=True
                    )
                    if battle['half'] == 2:
                        embed.add_field(name='\u200b', value='\u200b')
            embeds.append(embed)
        return embeds

    async def _genshin_abyss_ago(self, uid: int) -> discord.Embed:
        """Gets the embeds for spiral abyss history for a specific season."""
        data = gs.get_spiral_abyss(uid, False)
        if data['stats']['total_battles'] == 0:
            return []

        star = self._element_emoji('abyss_star')
        embeds = [
            discord.Embed(
                colour=0xffffff,
                title=f"Spiral abyss info of {uid}",
                description="Overall spiral abyss stats"
            ).add_field(
                name="Stats",
                value=f"Max floor: {data['stats']['max_floor']} Total stars: {data['stats']['total_stars']}\n"
                      f"Total battles: {data['stats']['total_battles']} Total wins: {data['stats']['total_wins']}",
                inline=False
            ).add_field(
                name="Character ranks",
                value="\n".join(f"**{k.replace('_',' ')}**: " + ', '.join(f"{i['name']} ({i['value']})" for i in v[:4]) for k,v in data['character_ranks'].items() if v) or "avalible only for floor 9 or above",
                inline=False
            ).set_author(
                name=f"Season {data['season']} ({data['season_start_time'].replace('-', '/')} - {data['season_end_time'].replace('-', '/')})\n"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            ).set_image(
                url=abyss_banners[0]
            )
        ]
        for floor in data['floors']:
            embed = discord.Embed(
                colour=0xffffff,
                title=f"Spiral abyss info of {uid}",
                description=f"Floor **{floor['floor']}** (**{floor['stars']}**{star})",
                timestamp=datetime.fromisoformat(floor['start'])
            ).set_author(
                name=f"Season {data['season']} ({data['season_start_time'].replace('-', '/')} - {data['season_end_time'].replace('-', '/')})\n"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            ).set_image(
                url=abyss_banners.get(floor['floor'], discord.Embed.Empty)
            )
            for chamber in floor['chambers']:
                for battle in chamber['battles']:
                    embed.add_field(
                        name=f"Chamber {chamber['chamber']}" + (f"{', 1st' if battle['half']==1 else ', 2nd'} Half " if chamber['has_halves'] else '') + f" ({chamber['stars']}{star})",
                        value='\n'.join(f"{i['name']} (lvl {i['level']})" for i in battle['characters']),
                        inline=True
                    )
                    if battle['half'] == 2:
                        embed.add_field(name='\u200b', value='\u200b')
            embeds.append(embed)
        return embeds


    @commands.group(invoke_without_command=True, aliases=['ga', 'giabyss', 'spiral'])
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def abyss(self, ctx: commands.Context, usr: int):
        """Shows info about a genshin player's spiral abyss runs"""
        uid = await self._user_uid(ctx, usr)
        spiral_abyss = gs.get_spiral_abyss(uid)

        await ctx.trigger_typing()
        embeds = []
        try:
            embeds += await self._genshin_abyss_new(uid)
            embeds += await self._genshin_abyss_ago(uid)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return
        if not embeds:
            await ctx.send("Player hasn't done any spiral abyss in the past month")
            return
        
        await send_pages(ctx, ctx, embeds)

    @commands.group(invoke_without_command=True, aliases=['gc', 'gichara', 'chara'])
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def characters(self, ctx: commands.Context, usr: int, lang: str = 'en-us'):
        """Shows info about a genshin player's characters"""
        uid = await self._user_uid(ctx, usr)
        langs = gs.get_langs()
        icon_cache: dict[int, str] = {}
        if lang not in langs:
            raise commands.UserInputError("Invalid lang, must be one of: " + ', '.join(langs.keys()))
        
        await ctx.trigger_typing()
        try:
            data = gs.get_characters(uid)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return
        for char in data:
            icon_cache[char['weapon']['name']] = char['weapon']['icon']
        
        embeds = [
            discord.Embed(
                colour=_item_color(char['rarity']),
                title=char['name'],
                description=f"{'★'*char['rarity']} {char['element']} "
                            f"level {char['level']} C{char['constellation']}"
            ).set_thumbnail(
                url=char['weapon']['icon']
            ).set_image(
                url=char['image']
            ).add_field(
                name=f"Weapon",
                value=f"{'★'*char['weapon']['rarity']} {char['weapon']['type']} - {char['weapon']['name']}\n"
                      f"level {char['weapon']['level']} refinement {char['weapon']['refinement']}",
                inline=False
            ).add_field(
                name=f"Artifacts",
                value="\n".join(f"**{(i['pos_name'].title()+':')}** {i['set']['name']}\n{'★'*i['rarity']} lvl {i['level']} - {i['name']}" for i in char['artifacts']) or 'none equipped',
                inline=False
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            )
            for char in data
        ]
        await send_pages(ctx, ctx, embeds)

        pass

def setup(bot):
    bot.add_cog(GenshinImpact(bot))