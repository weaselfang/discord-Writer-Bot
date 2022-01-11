import discord
import json
import lib
import os
import pytz
import random
import time
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from structures.db import Database
from structures.guild import Guild
from structures.user import User

class Utils(commands.Cog):
    """
    Utility slash commands
    """

    def __init__(self, bot):
        self.bot = bot
        self.__db = Database.instance()

    @commands.command(name="info", aliases=["admin", "mysetting", "ping", "profile", "reset", "setting"])
    @commands.guild_only()
    async def old(self, context):
        """
        Migrated command, so just display a message for now.

        :param context: Discord context
        """
        return await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(
        name="admin",
        description="Run admin commands on the bot",
        options=[
            create_option(
                name="command",
                description="What command do you want to run?",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                choices=[
                    create_choice(
                        name="Status",
                        value="status"
                    )
            ]),
            create_option(
                name="value",
                description="Value to set",
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
        ]
    )
    async def admin(self, context: SlashContext, command: str, value: str):
        """
        Runs admin commands on the bot

        :param SlashContext context: SlashContext object
        :param str command: The command to run
        :param str value: The value to set
        :rtype: mixed
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer(hidden=True)

        # Make sure it is me.
        user = User(context.author.id, context.guild_id, context=context, bot=self.bot)
        if not user.is_owner():
            return await context.send('Invalid permissions. Must be bot owner.')

        if command == 'status':
            await self.change_bot_status(value)

        await context.send("Done", hidden=True)

    async def change_bot_status(self, value: str):
        """
        Change the bot's status

        :param SlashContext context: SlashContext object
        :param str value: The value to set
        :rtype: void
        """
        await self.bot.change_presence(activity=discord.Game(value))

    @cog_ext.cog_slash(
        name="info",
        description="Display information and statistics about the bot"
    )
    async def info(self, context: SlashContext):
        """
        Displays information and statistics about the bot.

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('info'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        now = time.time()
        uptime = int(round(now - self.bot.start_time))
        guild_id = context.guild_id
        config = self.bot.config
        sprints = self.__db.get('sprints', {'completed': 0}, ['COUNT(id) as cnt'])['cnt']

        # Begin the embedded message
        embed = discord.Embed(title=lib.get_string('info:bot', guild_id), color=3447003,
                              description=lib.get_string('info:bot', guild_id))
        embed.add_field(name=lib.get_string('info:version', guild_id), value=config.version, inline=True)
        embed.add_field(name=lib.get_string('info:uptime', guild_id), value=str(timedelta(seconds=uptime)),
                        inline=True)
        embed.add_field(name=lib.get_string('info:owner', guild_id), value=str(self.bot.app_info.owner), inline=True)

        # Statistics
        stats = []
        stats.append('• ' + lib.get_string('info:servers', guild_id) + ': ' + format(len(self.bot.guilds)))
        stats.append('• ' + lib.get_string('info:sprints', guild_id) + ': ' + str(sprints))
        stats.append('• ' + lib.get_string('info:helpserver', guild_id) + ': ' + config.help_server)
        stats = '\n'.join(stats)

        embed.add_field(name=lib.get_string('info:generalstats', guild_id), value=stats, inline=False)

        # Developer Info
        git = {}
        git['branch'] = os.popen(r'git rev-parse --abbrev-ref HEAD').read().strip()
        git['rev'] = os.popen(r'git log --pretty=format:"%h | %ad | %s" --date=short -n 1').read().strip()

        dev = []
        dev.append(lib.get_string('info:dev:branch', guild_id) + ': ' + format(git['branch']))
        dev.append(lib.get_string('info:dev:repo', guild_id) + ': ' + format(config.src))
        dev.append(lib.get_string('info:dev:patch', guild_id) + ': ' + format(config.patch_notes))
        dev.append(lib.get_string('info:dev:change', guild_id) + ':\n\t' + format(git['rev']))
        dev = '\n'.join(dev)

        embed.add_field(name=lib.get_string('info:dev', guild_id), value=dev, inline=False)

        # Send the message
        await context.send(embed=embed)

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
        await self.run_mysetting(context, 'list')

    @cog_ext.cog_subcommand(
        base="mysetting",
        name="update",
        description="Update the value of one of your settings on the bot",
        options=[
            create_option(
                name="setting",
                description="The name of the setting to update",
                option_type=SlashCommandOptionType.STRING,
                choices=[
                    create_choice(name="Timezone", value="timezone"),
                    create_choice(name="Max WPM", value="maxwpm")
                ],
                required=True
            ),
            create_option(
                name="value",
                description="The value to set",
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
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
        await self.run_mysetting(context, setting, value)

    async def run_mysetting(self, context: SlashContext, setting: str = None, value: str = None):
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
                await context.send(
                    lib.get_string('event:timezoneupdated', user.get_guild()).format(value, time.ctime(), offset),
                    hidden=True)
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
        await context.send(lib.get_string('mysetting:updated', user.get_guild()).format(setting, value), hidden=True)

    @cog_ext.cog_slash(
        name="ping",
        description="Displays latency between client and bot"
    )
    async def ping(self, context: SlashContext):
        """
        Displays latency between client and bot

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('ping'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        # Work out the latency and send the message back.
        latency = round(self.bot.latency * 1000, 2)
        return await context.send('Pong! ' + str(latency) + 'ms')

    @cog_ext.cog_slash(
        name="profile",
        description="Display your Writer-Bot profile information and statistics"
    )
    async def profile(self, context: SlashContext):
        """
        Displays your Writer-Bot profile information and statistics.

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('profile'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        user = User(context.author.id, context.guild.id, context)
        profile = {
            'lvlxp': user.get_xp_bar(),
            'words': user.get_stat('total_words_written'),
            'words_sprints': user.get_stat('sprints_words_written'),
            'sprints_started': user.get_stat('sprints_started'),
            'sprints_completed': user.get_stat('sprints_completed'),
            'sprints_won': user.get_stat('sprints_won'),
            'challenges_completed': user.get_stat('challenges_completed'),
            'daily_goals_completed': user.get_stat('daily_goals_completed'),
            'weekly_goals_completed': user.get_stat('weekly_goals_completed'),
            'monthly_goals_completed': user.get_stat('monthly_goals_completed'),
            'yearly_goals_completed': user.get_stat('yearly_goals_completed'),
        }

        embed = discord.Embed(
            title=context.author.display_name,
            color=3066993,
            description=lib.get_string('profile:your', user.get_guild())
        )

        embed.add_field(name=lib.get_string('profile:lvlxp', user.get_guild()), value=profile['lvlxp'], inline=True)
        embed.add_field(name=lib.get_string('profile:words', user.get_guild()), value=profile['words'], inline=True)
        embed.add_field(name=lib.get_string('profile:wordssprints', user.get_guild()), value=profile['words_sprints'], inline=True)
        embed.add_field(name=lib.get_string('profile:sprintsstarted', user.get_guild()), value=profile['sprints_started'], inline=True)
        embed.add_field(name=lib.get_string('profile:sprintscompleted', user.get_guild()), value=profile['sprints_completed'], inline=True)
        embed.add_field(name=lib.get_string('profile:sprintswon', user.get_guild()), value=profile['sprints_won'], inline=True)
        embed.add_field(name=lib.get_string('profile:challengescompleted', user.get_guild()), value=profile['challenges_completed'], inline=True)
        embed.add_field(name=lib.get_string('profile:dailygoalscompleted', user.get_guild()), value=profile['daily_goals_completed'], inline=True)
        embed.add_field(name=lib.get_string('profile:weeklygoalscompleted', user.get_guild()), value=profile['weekly_goals_completed'], inline=True)
        embed.add_field(name=lib.get_string('profile:monthlygoalscompleted', user.get_guild()), value=profile['monthly_goals_completed'], inline=True)
        embed.add_field(name=lib.get_string('profile:yearlygoalscompleted', user.get_guild()), value=profile['yearly_goals_completed'], inline=True)

        # Send the embedded message
        await context.send(embed=embed)

    @cog_ext.cog_slash(
        name="reset",
        description="Reset some or all of your user statistics",
        options=[
            create_option(
                name="statistic",
                description="What statistic do you want to reset? (This cannot be undone afterwards)",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                choices=[
                 create_choice(name="WPM Personal Best", value="pb"),
                 create_choice(name="Words Written", value="wc"),
                 create_choice(name="Experience", value="xp"),
                 create_choice(name="Projects", value="projects"),
                 create_choice(name="Everything", value="all")
                ]
            )
        ]
    )
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

        return await context.send(output, hidden=True)

    @cog_ext.cog_subcommand(
        base="setting",
        name="list",
        description="List all of the current settings for this server"
    )
    async def setting_list(self, context: SlashContext):
        """
        List all of the current settings for this server

        :param SlashContext context: SlashContext object
        :rtype: void
        """
        await self.run_setting(context, 'list')

    @cog_ext.cog_subcommand(
        base="setting",
        name="update",
        description="Update the value of one of the server settings",
        options=[
            create_option(
                name="setting",
                description="The name of the setting to update",
                option_type=SlashCommandOptionType.STRING,
                choices=[
                    create_choice(name="Language", value="lang"),
                    create_choice(name="Sprint End Delay Time (Minutes)", value="sprint_delay_end"),
                    create_choice(name="Enable Command", value="enable"),
                    create_choice(name="Disable Command", value="disable")
                ],
                required=True),
            create_option(
                name="value",
                description="The value to set",
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
        ]
    )
    async def setting_update(self, context: SlashContext, setting: str, value: str):
        """
        Update a one of the server settings

        :param SlashContext context: SlashContext object
        :param str setting: Name of the setting
        :param str value: Value to set
        :rtype: void
        """
        await self.run_setting(context, setting, value)

    async def run_setting(self, context, setting: str = None, value: str = None):
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
            return await context.send(lib.get_string('setting:err:sprint_delay_end', guild.get_id()))

        elif setting == 'lang' and not lib.is_supported_language(value):
            return await context.send(lib.get_string('setting:err:lang', guild.get_id()).format(
                    ', '.join(lib.get_supported_languages())))

        elif setting in ['disable', 'enable']:
            if not (value in self.bot.all_commands):
                return await context.send(lib.get_string('setting:err:disable', guild.get_id()).format(value))
            elif value in ['setting', 'help', 'admin', 'mysetting']:  # Don't allow disabling these commands
                return await context.send(lib.get_string('setting:err:disableSelf', guild.get_id()))
            else:
                guild.disable_enable_command(value, setting == 'disable')
                return await context.send(lib.get_string('setting:disable', guild.get_id()).format(setting,
                                                                                                         value))

        guild.update_setting(setting, value)
        return await context.send(lib.get_string('setting:updated', guild.get_id()).format(setting, value))


def setup(bot):
    """
    Add the cog to the bot
    :param bot: Discord bot
    :rtype void:
    """
    bot.add_cog(Utils(bot))