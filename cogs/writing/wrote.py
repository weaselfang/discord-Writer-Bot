import lib
from discord.ext import commands
from discord_slash import SlashContext, cog_ext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option
from structures.db import Database
from structures.event import Event
from structures.project import Project
from structures.user import User
from structures.guild import Guild

class Wrote(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.__db = Database.instance()

    @cog_ext.cog_slash(
        name="wrote",
        description="Adds to your total words written statistic",
        options=[
            create_option(
                name="amount",
                description="How many words did you write?",
                option_type=SlashCommandOptionType.INTEGER,
                required=True
            ),
            create_option(
                name="project",
                description="Shortname of the project you're writing in",
                option_type=SlashCommandOptionType.STRING,
                required=False
            )
        ],
        connector={"project": "shortname"}
    )
    async def wrote(self, context: SlashContext, amount: int, shortname: str = None):
        """
        Adds to your total words written statistic.

        Examples:
            !wrote 250 - Adds 250 words to your total words written
            !wrote 200 sword - Adds 200 words to your Project with the shortname "sword". (See: Projects for more info).
        """
        await context.defer()

        if not Guild(context.guild).is_command_enabled('wrote'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        user = User(context.author_id, context.guild_id, context)

        message = None

        # If they were writing in a Project, update its word count.
        if shortname is not None:

            project = Project.get(context.author_id, shortname.lower())

            # Make sure the project exists.
            if not project:
                return await context.send(context.author.mention + ', ' + lib.get_string('project:err:noexists', context.guild_id).format(shortname))

            project.words += amount

            written_stat = user.get_stat('total_words_written')
            if written_stat is None:
                written_stat = 0
            total = int(written_stat) + int(amount)

            message = lib.get_string('wrote:addedtoproject', context.guild_id).format(amount, project.name, project.words, total)

        # # Is there an Event running?
        event = Event.get_by_guild(context.guild_id)
        if event and event.is_running():
            event.add_words(user.get_id(), amount)

        # Increment their words written statistic
        user.add_stat('total_words_written', amount)

        # Update their words towards their goals
        await user.add_to_goals(amount)

        # Output message
        if message is None:
            total = user.get_stat('total_words_written')
            message = lib.get_string('wrote:added', context.guild_id).format(str(amount), str(total))

        await context.send(context.author.mention + ', ' + message)

    @commands.command(name="wrote")
    @commands.guild_only()
    async def old(self, context):
        """
        Adds to your total words written statistic.

        Examples:
            !wrote 250 - Adds 250 words to your total words written
            !wrote 200 sword - Adds 200 words to your Project with the shortname "sword". (See: Projects for more info).
        """
        await context.send(lib.get_string('err:slash', context.guild.id))

def setup(bot):
    bot.add_cog(Wrote(bot))
