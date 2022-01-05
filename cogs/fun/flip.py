import lib, random
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from structures.guild import Guild

class Flip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="flip")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(name="flip", description="Flip a coin")
    async def flip(self, context: SlashContext):
        """
        Flips a coin.

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('flip'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        guild_id = context.guild_id

        # Random number between 1-2 to choose heads or tails.
        rand = random.randrange(2)
        side = 'heads' if rand == 0 else 'tails'

        # Send the message.
        await context.send( lib.get_string('flip:'+side, guild_id) )



def setup(bot):
    bot.add_cog(Flip(bot))