import random
import lib
import discord
from discord.ext import commands
from structures.guild import Guild

class Flip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def flip(self, context):
        """
        Flips a coin.

        Examples: !flip
        """
        if not Guild(context.guild).is_command_enabled('flip'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        guild_id = context.guild.id
        rand = random.randrange(2)
        side = 'heads' if rand == 0 else 'tails'

        await context.send( lib.get_string('flip:'+side, guild_id) )



def setup(bot):
    bot.add_cog(Flip(bot))