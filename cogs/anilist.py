from __future__ import annotations
from datetime import datetime
from typing import Any

import discord
from discord.ext import tasks, commands
from utils import utc_as_timezone


class Anilist(commands.Cog):
    """Shows info about an anime using anilist"""
    url = "https://graphql.anilist.co"
    query = """
query ($id: Int, $last: Int) {
  User(id: $id) {
    name
    avatar {
      large
    }
    siteUrl
  }
  Page(page: 1) {
    activities(userId: $id, type: ANIME_LIST, sort: ID_DESC, createdAt_greater: $last) {
      ... on ListActivity {
        id
        type
        status
        progress
        createdAt
        media {
          id
          type
          bannerImage
          siteUrl
          title {
            userPreferred
          }
          coverImage {
            large
          }
        }
      }
    }
  }
}
    """
    channel: discord.TextChannel

    async def init(self):
        await self.bot.wait_until_ready()
        self.channel = await self.bot.fetch_channel(self.config.getint('channel')) # type: ignore
        self.fetch_activity.start()

    def cog_unload(self):
        self.fetch_activity.cancel()

    @tasks.loop(minutes=10)
    async def fetch_activity(self):
        """Fetches new anilist activity."""
        await self.bot.wait_until_ready()
        
        last = 0
        async for msg in self.channel.history():
            if not msg.embeds:
                continue
            e = msg.embeds[0]
            if msg.embeds and e.title == 'anilist status' and e.timestamp:
                dt = utc_as_timezone(e.timestamp)
                last = int(dt.timestamp())
                break

        data = await self.fetch_anilist(
            self.query, 
            {'id': self.config.getint('userid'), 'last': last}
        )

        user = data['User']
        for activity in reversed(data['Page']['activities']):
            # temporary disable of manga:
            if activity['type'] == 'manga':
                continue
            
            anime = f"[{activity['media']['title']['userPreferred']}]({activity['media']['siteUrl']})"
            if activity['progress']:
                description = f"{activity['status']} {activity['progress']} of {anime}"
            else:
                description = f"{activity['status']} {anime}"
            
            embed = discord.Embed(
                title="anilist status",
                description=description,
                color=discord.Color.green(),
                timestamp=datetime.fromtimestamp(activity['createdAt']).astimezone()
            ).set_author(
                name=user['name'],
                url=user['siteUrl'],
                icon_url=user['avatar']['large']
            ).set_thumbnail(
                url=activity['media']['coverImage']['large']
            ).set_footer(
                text=f"{'anime' if activity['type']=='ANIME_LIST' else 'manga'} activity",
                icon_url="https://anilist.co/img/icons/android-chrome-512x512.png"
            )
            await self.channel.send(embed=embed)

            self.logger.info(f"Updated anilist activity {activity['id']}")

    async def fetch_anilist(self, query: str, variables: dict, **kwargs) -> Any:
        """Fetches data from anilist api."""
        payload = {'query': query, 'variables': variables}
        async with self.bot.session.post(self.url, json=payload, **kwargs) as r:
            data = await r.json()
        return data['data']


def setup(bot):
    bot.add_cog(Anilist(bot))
