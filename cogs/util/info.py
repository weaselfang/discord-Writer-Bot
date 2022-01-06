import datetime, discord, json, lib, os, time
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from structures.guild import Guild
from structures.db import Database

class Info(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.__db = Database.instance()

    @commands.command(name="info")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(name="info",
                       description="Display information and statistics about the bot")
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
        embed = discord.Embed(title=lib.get_string('info:bot', guild_id), color=3447003, description=lib.get_string('info:bot', guild_id))
        embed.add_field(name=lib.get_string('info:version', guild_id), value=config.version, inline=True)
        embed.add_field(name=lib.get_string('info:uptime', guild_id), value=str(datetime.timedelta(seconds=uptime)), inline=True)
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
        git['rev'] =  os.popen(r'git log --pretty=format:"%h | %ad | %s" --date=short -n 1').read().strip()

        dev = []
        dev.append(lib.get_string('info:dev:branch', guild_id) + ': ' + format(git['branch']))
        dev.append(lib.get_string('info:dev:repo', guild_id) + ': ' + format(config.src))
        dev.append(lib.get_string('info:dev:patch', guild_id) + ': ' + format(config.patch_notes))
        dev.append(lib.get_string('info:dev:change', guild_id) + ':\n\t' + format(git['rev']))
        dev = '\n'.join(dev)

        embed.add_field(name=lib.get_string('info:dev', guild_id), value=dev, inline=False)

        # Send the message
        await context.send(embed=embed)

def setup(bot):
    bot.add_cog(Info(bot))