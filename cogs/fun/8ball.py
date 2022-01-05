import random
import lib
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option
from structures.guild import Guild

class EightBall(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="8ball")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(name="8ball",
                       description="Ask the magic 8ball a question",
                       options=[
                           create_option(name="question",
                                         description="What is your question for the magic 8ball?",
                                         option_type=SlashCommandOptionType.STRING,
                                         required=True)
                       ])
    async def _8ball(self, context: SlashContext, question: str):
        """
        Ask the magic 8-ball a question.

        :param SlashContext context: SlashContext object
        :param str question: The question the user is asking
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('8ball'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        guild_id = context.guild_id

        # Pick a random answer
        i: int = random.randrange(21)
        answer: str = lib.get_string(f"8ball:{i}", guild_id)

        # Send the message
        await context.send(context.author.mention + ', ' + lib.get_string('8ball:yourquestion', guild_id).format(question) + answer)


def setup(bot):
    bot.add_cog(EightBall(bot))
