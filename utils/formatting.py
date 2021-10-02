from __future__ import annotations
from itertools import islice

from typing import Iterable, Iterator, TypeVar, Union

import discord

T = TypeVar("T")


def wrap(*string: str, lang: str = "") -> str:
    """Wraps a string in codeblocks."""
    return f"```{lang}\n" + "".join(string) + "\n```"


def multiline_join(strings: list[str], sep: str = "", prefix: str = "", suffix: str = "") -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return "\n".join(prefix + sep.join(i) + suffix for i in parts)


def grouper(iterable: Iterable[T], chunk_size: int) -> Iterator[list[T]]:
    """Like chunkify but for any iterable"""
    it = iter(iterable)
    while chunk := list(islice(it, chunk_size)):
        yield chunk


def chunkify(
    string: Union[str, Iterable[str]], chunk_size: int = 1980, newlines: bool = True, wrapped: bool = False
) -> list[str]:
    """Takes in a string or a list of lines and splits it into chunks that fit into a single discord message

    You may change the max_size to make this function work for embeds.
    There is a 20 character leniency given to max_size by default.

    If newlines is true the chunks are formatted with respect to newlines as long as that's possible.
    If wrap is true the chunks will be individually wrapped in codeblocks.
    """
    if newlines:
        string = string.split("\n") if isinstance(string, str) else string

        chunks = [""]
        for i in string:
            i += "\n"
            if len(chunks[-1]) + len(i) < chunk_size:
                chunks[-1] += i
            elif len(i) < chunk_size:
                chunks.append(i)
            else:
                chunks.extend(chunkify(i, chunk_size, newlines=False, wrapped=False))
    else:
        string = string if isinstance(string, str) else "\n".join(string)
        chunks = [string[i : i + chunk_size] for i in range(0, len(string), chunk_size)]

    if wrapped:
        chunks = [wrap(i) for i in chunks]

    return chunks


async def send_chunks(
    destination: discord.abc.Messageable, string: Union[str, Iterable[str]], wrapped: bool = False
) -> list[discord.Message]:
    """Sends a long string to a channel"""
    return [await destination.send(chunk) for chunk in chunkify(string, wrapped=wrapped)]
