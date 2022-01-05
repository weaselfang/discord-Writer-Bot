import random, lib, json
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option
from structures.guild import Guild
class Reassure(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reassure")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(name="reassure",
                       description="Send a random reassuring message to a user or yourself",
                       options=[
                           create_option(name="who",
                                         description="Who do you want to reassure?",
                                         option_type=SlashCommandOptionType.STRING,
                                         required=False)
                       ])
    async def reassure(self, context: SlashContext, who: str = None):
        """
        Reassures you that everything will be okay.

        :param SlashContext context: SlashContext object
        :param str|None who: The name of the user to reassure
        :rtype: void
        """
        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('reassure'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        guild_id = context.guild_id

        # If no name passed through, default to the author of the command.
        if who is None:
            mention = context.author.mention
        else:

            # We must now mention the user directly, as we can't easily lookup users any more.
            if not who.startswith('<@!') or not who.endswith('>'):
                return await context.send( lib.get_string('reassure:nomention', guild_id) )

            mention = who

        # Load the JSON file with the quotes.
        messages = lib.get_asset('reassure', guild_id)

        # Pick a random message.
        max = len(messages) - 1
        quote = messages[random.randint(1, max)]

        # Send the message.
        await context.send( mention + ', ' + format(quote) )

def setup(bot):
    bot.add_cog(Reassure(bot))