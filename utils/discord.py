from __future__ import annotations

import asyncio
import re
import warnings
from typing import TYPE_CHECKING, AsyncIterable, Iterable, Union

import discord
from discord.ext import commands

from .tools import Paginator



async def get_role(
    guild: discord.Guild,
    name: str,
    overwrite: discord.PermissionOverwrite = None,
    permissions: discord.Permissions = None,
) -> discord.Role:
    """Returns a role with specific overwrites"""
    role = discord.utils.find(lambda r: r.name.lower() == name.lower(), guild.roles)

    if role is None:
        role = await guild.create_role(name=name, permissions=permissions or discord.Permissions.none())
    elif permissions is not None and role.permissions != permissions:
        await role.edit(permissions=permissions)

    if overwrite is None:
        return role

    for channel in guild.channels:
        if channel.category and channel.permissions_synced:
            channel = channel.category
        if channel.overwrites_for(role) != overwrite:
            await channel.set_permissions(role, overwrite=overwrite)

    return role


async def get_muted_role(guild: discord.Guild) -> discord.Role:
    """Returns the muted role or creates one."""
    overwrite = discord.PermissionOverwrite(send_messages=False, add_reactions=False)
    return await get_role(guild, "muted", overwrite)


async def get_webhook(channel: discord.TextChannel) -> discord.Webhook:
    """Returns the general bot hook or creates one"""
    webhook = discord.utils.find(
        lambda w: w.name is not None and w.name.lower() == "culture hook", await channel.webhooks()
    )

    if webhook is None:
        from bot import bot

        webhook = await channel.create_webhook(
            name="Culture Hook", avatar=await bot.user.display_avatar.read(), reason="For making better looking messages"
        )

    return webhook

def get_emoji(name: str, guild: discord.Guild = None) -> discord.Emoji:
    """Returns the emoji from the main server"""
    if guild is None:
        from bot import bot
        guild = bot.get_guild(570841314200125460) # type: ignore
    
    emoji = discord.utils.find(lambda e: e.name.lower() == name.lower(), guild.emojis)
    if emoji is None:
        warnings.warn(f"Couldn't find an emoji: {name}")
        return discord.PartialEmoji(name=":grey_question:") # type: ignore
    
    return emoji

async def _try_delete_reaction(message: discord.Message, payload: discord.RawReactionActionEvent) -> None:
    try:
        await message.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))
    except discord.Forbidden:
        pass

page_left, page_right, remove = "◀", "▶", "❌"
async def send_pages(
    ctx: commands.Context,
    destination: Union[discord.abc.Messageable, discord.Message],
    pages: Union[Iterable[discord.Embed], AsyncIterable[discord.Embed]],
    asyncify: bool = False,
    timeout: int = 60,
):
    """Send multiple embeds as pages, supports iterators

    If asyncify is true the items will be gotten asynchronously even with sync iterables.
    """
    paginator = await Paginator.create(pages)
    if isinstance(destination, discord.Message):
        message = destination
    else:
        message = await destination.send(embed=paginator.curr)

    for reaction in (page_left, page_right, remove):
        asyncio.create_task(message.add_reaction(reaction))

    while True:
        try:
            payload = await ctx.bot.wait_for(
                "raw_reaction_add",
                check=lambda payload: payload.user_id != ctx.bot.user.id and message.id == payload.message_id,
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass
            return

        del_task = asyncio.create_task(_try_delete_reaction(message, payload))

        if payload.user_id != ctx.author.id:
            continue

        r = str(payload.emoji)
        if r == remove:
            del_task.cancel()
            await message.delete()
            return
        elif r == page_right:
            embed = await paginator.next(asyncify=asyncify)
        elif r == page_left:
            try:
                embed = paginator.prev()
            except IndexError:
                continue
        else:
            continue

        await message.edit(embed=embed)

def bot_channel_only(regex: str = r"bot|spam", category: bool = True, dms: bool = True):
    def predicate(ctx: commands.Context):
        channel = ctx.channel
        if not isinstance(channel, discord.TextChannel):
            if dms:
                return True
            raise commands.CheckFailure("Dms are not counted as a bot channel.")

        if re.search(regex, channel.name) or category and re.search(regex, str(channel.category)):
            return True

        raise commands.CheckFailure("This channel is not a bot channel.")

    return commands.check(predicate)

def guild_check(guild: Union[int, discord.Guild]):
    """A check decorator for guilds"""
    guild = guild.id if isinstance(guild, discord.Guild) else guild

    def predicate(ctx: commands.Context):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        elif ctx.guild.id != guild:
            raise commands.CheckFailure("This command cannot be used in this server")
        else:
            return True
    
    return commands.check(predicate)
