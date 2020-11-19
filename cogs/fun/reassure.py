import random, lib, discord, json
from discord.ext import commands

# debugging
from pprint import pprint
from inspect import getmembers

class Reassure(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reassure")
    @commands.guild_only()
    async def reassure(self, context, who=None):
        """
        Reassures you that everything will be okay.

        Examples: !reassure
        """

        guild_id = context.guild.id

        # If no name passed through, default to the author of the command
        if who is None:
            mention = context.message.author.mention
        else:

            user = context.guild.get_member_named(who)

            # If we couldn't find the user, display an error
            if user is None:
                await context.send(lib.get_string('err:nouser', guild_id) + ' (There is a known issue with the reassure command, as well as the leaderboards in the Event and XP commands. We are waiting for Discord to respond to an email to get these fixed)')
                return

            mention = user.mention

        # Load the JSON file with the quotes
        quotes = lib.get_asset('reassure', guild_id)

        max = len(quotes) - 1
        quote = quotes[random.randint(1, max)]

        # Send the message
        await context.send( mention + ', ' + format(quote) )

def setup(bot):
    bot.add_cog(Reassure(bot))