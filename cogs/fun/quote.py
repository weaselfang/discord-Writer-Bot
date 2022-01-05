import random, lib, json
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from structures.guild import Guild

class Quote(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quote")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(name="quote", description="Generate a random motivational quote")
    async def quote(self, context: SlashContext):
        """
        A random motivational quote to inspire you.

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('quote'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        guild_id = context.guild_id

        # Load the JSON file with the quotes
        quotes = lib.get_asset('quotes', guild_id)

        # Choose a random quote.
        max = len(quotes) - 1
        quote = quotes[random.randint(1, max)]

        # Send the message
        await context.send( format(quote['quote'] + ' - *' + quote['name'] + '*') )

def setup(bot):
    bot.add_cog(Quote(bot))