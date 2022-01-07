import discord, lib
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from structures.guild import Guild
from structures.user import User
from structures.wrapper import CommandWrapper

class Reset(commands.Cog, CommandWrapper):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reset")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(name="reset",
                       description="Reset some or all of your user statistics",
                       options=[
                           create_option(name="statistic",
                                         description="What statistic do you want to reset? (This cannot be undone afterwards)",
                                         option_type=SlashCommandOptionType.STRING,
                                         required=True,
                                         choices=[
                                             create_choice(name="WPM Personal Best", value="pb"),
                                             create_choice(name="Words Written", value="wc"),
                                             create_choice(name="Experience", value="xp"),
                                             create_choice(name="Projects", value="projects"),
                                             create_choice(name="Everything", value="all")
                                         ])
                       ])
    async def reset(self, context: SlashContext, statistic: str = None):
        """
        Lets you reset your statistics/records.

        :param SlashContext context: SlashContext object
        :param str statistic: The statistic to reset
        :rtype: void
        """
        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer(hidden=True)

        # No need to check if command is disabled, as this is a user-specific command.

        # Get the user.
        user = User(context.author.id, context.guild_id, context)

        output = ''

        # Personal Best
        if statistic == 'pb':
            user.update_record('wpm', 0)
            output = lib.get_string('reset:pb', user.get_guild())

        elif statistic == 'wc':
            user.update_stat('total_words_written', 0)
            output = lib.get_string('reset:wc', user.get_guild())

        elif statistic == 'xp':
            await user.update_xp(0)
            output = lib.get_string('reset:xp', user.get_guild())

        elif statistic == 'projects':
            user.reset_projects()
            output = lib.get_string('reset:projects', user.get_guild())

        elif statistic == 'all':
            user.reset()
            output = lib.get_string('reset:done', user.get_guild())

        return await context.send( output, hidden=True )


def setup(bot):
    bot.add_cog(Reset(bot))
