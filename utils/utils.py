"""General utility functions that don't fit elsewhere"""
from __future__ import annotations

import asyncio
import re
import time
from asyncio import Task
from datetime import datetime, timedelta, timezone
from typing import *  # type: ignore

from typing_extensions import TypeAlias

import discord
from discord.ext import commands

T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")

_Event: TypeAlias = Union[str, Tuple[str, Optional[Callable[..., bool]]]]

def humandate(dt: Union[datetime, str, None]) -> str:
    if dt is None:
        return "unknown"
    elif isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%a, %b %d, %Y %H:%M %p")

def humandelta(delta: timedelta) -> str:
    s = int(delta.total_seconds())
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    return (f"{d}d" if d else "") + (f"{h}h" if h else "") + f"{m}min {s}s"

def utc_as_timezone(dt: datetime, naive: bool = False, reverse: bool = False) -> datetime:
    """Converts a random utc datetime into a correct local timezone aware datetime"""
    ts = dt.timestamp()
    localtm = time.localtime(ts)
    delta = timedelta(seconds=localtm.tm_gmtoff)
    if reverse:
        delta = -delta

    tz = timezone(delta, localtm.tm_zone)

    dt += delta
    return dt if naive else dt.astimezone(tz)

def humanlist(l: Sequence[str], join: str = 'and') -> str:
    """Returns a human readable list"""
    return ', '.join(l[:-1]) + f' {join} ' + l[-1]

async def _wait_for_many(
    bot: commands.Bot,
    events: Iterable[_Event],
    timeout: Optional[int] = None,
    return_when: str = 'ALL_COMPLETED',
) -> set[Task[Any]]:
    """Waits for multiple events"""
    events = [(e, None) if isinstance(e, str) else e for e in events]
    futures = [
        bot.loop.create_task(bot.wait_for(event, check=check), name=event) 
        for event, check in events
    ]
    done, pending = await asyncio.wait(futures, loop=bot.loop, timeout=timeout, return_when=return_when)
    for task in pending:
        task.cancel()
    return done

async def wait_for_any(bot: commands.Bot, *events: _Event, timeout: int = None) -> Union[tuple[str, Any], tuple[Literal[''], None]]:
    """Waits for the first event to complete"""
    tasks = await _wait_for_many(bot, events, timeout=timeout, return_when='FIRST_COMPLETED')
    if not tasks:
        return '', None
    task = tasks.pop()
    return task.get_name(), task.result()

async def wait_for_all(bot: commands.Bot, *events: _Event, timeout: int = None) -> dict[str, Any]:
    """Waits for the all event to complete"""
    tasks = await _wait_for_many(bot, events, timeout=timeout, return_when='ALL_COMPLETED')
    return {task.get_name(): task.result() for task in tasks}

async def wait_for_reaction(
    bot: commands.Bot, 
    check: Callable[[discord.RawReactionActionEvent], bool] = None, 
    timeout: int = None
) -> Optional[discord.RawReactionActionEvent]:
    """Waits for a reaction add or remove"""
    events = [(event, check) for event in ('raw_reaction_add', 'raw_reaction_remove')]
    name, data = await wait_for_any(bot, *events, timeout=timeout)
    return data
