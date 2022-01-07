import discord, lib, pytz
from datetime import datetime, timezone
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from structures.user import User
from structures.wrapper import CommandWrapper
from structures.guild import Guild

class MySetting(commands.Cog, CommandWrapper):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mysetting")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_subcommand(
        base="mysetting",
        name="list",
        description="List all of your current settings on the bot"
    )
    async def mysetting_list(self, context: SlashContext):
        """
        Display a list of the user's settings

        :param SlashContext context: SlashContext object
        :rtype: void
        """
        await self.run(context, 'list')

    @cog_ext.cog_subcommand(
        base="mysetting",
        name="update",
        description="Update the value of one of your settings on the bot",
        options=[
            create_option(name="setting", description="The name of the setting to update", option_type=SlashCommandOptionType.STRING, choices=[
                create_choice(name="Timezone", value="timezone"),
                create_choice(name="Max WPM", value="maxwpm")
            ], required=True),
            create_option(name="value", description="The value to set", option_type=SlashCommandOptionType.STRING, required=True)
        ]
    )
    async def mysetting_update(self, context: SlashContext, setting: str, value: str):
        """
        Update a user's setting on the bot

        :param SlashContext context: SlashContext object
        :param str setting: Name of the setting
        :param str value: Value to set
        :rtype: void
        """
        await self.run(context, setting, value)

    async def run(self, context: SlashContext, setting: str = None, value: str = None):
        """
        This is the actual method which runs the action requested

        :param SlashContext context: SlashContext object
        :param str|None setting: Name of the setting
        :param str|None value: Value to set
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer(hidden=True)

        # No need to check if guild has disabled this command. It's a user-specific command.

        # Get the user.
        user = User(context.author.id, context.guild_id, context)

        # If we want to list the setting, do that instead.
        if setting == 'list':
            settings = user.get_settings()
            output = '```ini\n';
            if settings:
                for setting, value in settings.items():
                    output += setting + '=' + str(value) + '\n'
            else:
                output += lib.get_string('setting:none', user.get_guild())
            output += '```'
            return await context.send(output, hidden=True)


        # If the setting is timezone convert the value
        if setting == 'timezone':
            try:
                timezone = pytz.timezone(value)
                time = datetime.now(timezone)
                offset = datetime.now(timezone).strftime('%z')
                await context.send( lib.get_string('event:timezoneupdated', user.get_guild()).format(value, time.ctime(), offset), hidden=True )
            except pytz.exceptions.UnknownTimeZoneError:
                await context.send(lib.get_string('mysetting:timezone:help', user.get_guild()), hidden=True)
                return

        elif setting == 'maxwpm':
            # Must be a number.
            value = lib.is_number(value)
            if not value or value <= 0:
                return await context.send(lib.get_string('mysetting:err:maxwpm', user.get_guild()), hidden=True)

        # Update the setting and post the success message
        user.update_setting(setting, value)
        await context.send( lib.get_string('mysetting:updated', user.get_guild()).format(setting, value), hidden=True )

def setup(bot):
    bot.add_cog(MySetting(bot))