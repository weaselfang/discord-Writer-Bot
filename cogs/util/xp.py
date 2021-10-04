import discord
import lib
from discord.ext import commands
from structures.guild import Guild
from structures.user import User
from structures.guild import Guild

class XP(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def xp(self, context, who='me'):
        """
        Checks your Experience Points and Level. Use the 'top' flag to see the top 10 on this server.
        Examples:
            !xp - Shows your level/xp
            !xp top - Shows the top 10 users on this server
        """
        if not Guild(context.guild).is_command_enabled('xp'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        guild_id = context.guild.id
        user_id = context.message.author.id

        if who == 'top':

            title = context.guild.name + ' - ' + lib.get_string('xp:leaderboard', guild_id)
            embed = discord.Embed(title=title, color=discord.Color.red(), description=None)
            embed.add_field(name=lib.get_string('xp:leaderboard', guild_id), value='Leaderboard temporarily disabled until a fix can be implemented', inline=False)
            return await context.send(embed=embed)

        else:
            user = User(user_id, guild_id)
            xp = user.get_xp()

            # Either display a message saying they have no XP, or display the XP bar for the user
            if xp is None:
                output = context.message.author.mention + ', ' + lib.get_string('xp:noxp', guild_id)
            else:
                output = context.message.author.mention + ', ' + lib.get_string('youare', guild_id) + ' ' + user.get_xp_bar()

        await context.send(output)

def setup(bot):
    bot.add_cog(XP(bot))