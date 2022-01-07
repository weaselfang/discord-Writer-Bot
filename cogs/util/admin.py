import discord, lib
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from structures.user import User
from structures.wrapper import CommandWrapper

class Admin(commands.Cog, CommandWrapper):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="admin",
                       description="Run admin commands on the bot",
                       options=[
                           create_option(name="command",
                                         description="What command do you want to run?",
                                         option_type=SlashCommandOptionType.STRING,
                                         required=True,
                                         choices=[
                                             create_choice(name="Status", value="status")
                                         ]),
                           create_option(name="value",
                                         description="Value to set",
                                         option_type=SlashCommandOptionType.STRING,
                                         required=True)
                       ])
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
            await self.run_status(context, value)

        await context.send("Done", hidden=True)


    async def run_status(self, context: SlashContext, value: str):
        """
        Change the bot's status

        :param SlashContext context: SlashContext object
        :param str value: The value to set
        :rtype: void
        """
        await self.bot.change_presence(activity=discord.Game(value))

def setup(bot):
    bot.add_cog(Admin(bot))