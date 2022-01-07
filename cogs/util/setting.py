import discord, lib, pytz
from datetime import datetime, timezone
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from structures.guild import Guild
from structures.user import User
from structures.wrapper import CommandWrapper

from pprint import pprint

class Setting(commands.Cog, CommandWrapper):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setting")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_subcommand(
        base="setting",
        name="list",
        description="List all of the current settings for this server",
    )
    async def setting_list(self, context: SlashContext):
        """
        List all of the current settings for this server

        :param SlashContext context: SlashContext object
        :rtype: void
        """
        await self.run(context, 'list')

    @cog_ext.cog_subcommand(
        base="setting",
        name="update",
        description="Update the value of one of the server settings",
        options=[
            create_option(name="setting", description="The name of the setting to update",
                          option_type=SlashCommandOptionType.STRING, choices=[
                    create_choice(name="Language", value="lang"),
                    create_choice(name="Sprint End Delay Time (Minutes)", value="sprint_delay_end"),
                    create_choice(name="Enable Command", value="enable"),
                    create_choice(name="Disable Command", value="disable")
                ], required=True),
            create_option(name="value", description="The value to set", option_type=SlashCommandOptionType.STRING,
                          required=True)
        ],
    )
    async def setting_update(self, context: SlashContext, setting: str, value: str):
        """
        Update a one of the server settings

        :param SlashContext context: SlashContext object
        :param str setting: Name of the setting
        :param str value: Value to set
        :rtype: void
        """
        await self.run(context, setting, value)

    async def run(self, context, setting: str = None, value: str = None):
        """
        The actual method to run the action

        :param SlashContext context: SlashContext object
        :param str setting: Name of the setting
        :param str value: Value to set
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Get the user
        user = User(context.author.id, context.guild_id, context)
        guild = Guild(context.guild)

        # Make sure they have permission to use this.
        if not context.author.guild_permissions.manage_guild:
            return await context.send(lib.get_string('err:permissions', user.get_guild()))

        # If we want to list the setting, do that instead.
        if setting == 'list':
            settings = guild.get_settings()
            output = '```ini\n'
            if settings:
                for setting, value in settings.items():
                    output += setting + '=' + str(value) + '\n'
            else:
                output += lib.get_string('setting:none', guild.get_id())
            output += '```'
            return await context.send(output)


        # Check that the value is valid for the setting they are updating
        elif setting == 'sprint_delay_end' and (not lib.is_number(value) or int(value) < 1):
            return await context.send(user.get_mention() + ', ' + lib.get_string('setting:err:sprint_delay_end', guild.get_id()))

        elif setting == 'lang' and not lib.is_supported_language(value):
            return await context.send(user.get_mention() + ', ' + lib.get_string('setting:err:lang', guild.get_id()).format(', '.join(lib.get_supported_languages())))

        elif setting in ['disable', 'enable']:
            if not (value in self.bot.all_commands):
                return await context.send(user.get_mention() + ', ' + lib.get_string('setting:err:disable', guild.get_id()).format(value))
            elif value in ['setting', 'help', 'admin', 'mysetting']: # Don't allow disabling these commands
                return await context.send(user.get_mention() + ', ' + lib.get_string('setting:err:disableSelf', guild.get_id()))
            else:
                guild.disable_enable_command(value, setting == 'disable')
                return await context.send(user.get_mention() + ', ' + lib.get_string('setting:disable', guild.get_id()).format(setting, value))

        guild.update_setting(setting, value)
        return await context.send(user.get_mention() + ', ' + lib.get_string('setting:updated', guild.get_id()).format(setting, value))

def setup(bot):
    bot.add_cog(Setting(bot))