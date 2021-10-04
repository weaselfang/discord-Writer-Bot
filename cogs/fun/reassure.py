import random, lib, discord, json
from discord.ext import commands
from structures.guild import Guild

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
        if not Guild(context.guild).is_command_enabled('reassure'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        guild_id = context.guild.id

        # If no name passed through, default to the author of the command
        if who is None:
            mention = context.message.author.mention
        else:

            # We must now mention the user directly, as we can't easily lookup users any more
            if not who.startswith('<@!') or not who.endswith('>'):
                return await context.send( lib.get_string('reassure:nomention', guild_id) )

            mention = who

        # Load the JSON file with the quotes
        messages = lib.get_asset('reassure', guild_id)

        max = len(messages) - 1
        quote = messages[random.randint(1, max)]

        # Send the message
        await context.send( mention + ', ' + format(quote) )

def setup(bot):
    bot.add_cog(Reassure(bot))