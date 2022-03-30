import discord, lib, time, math
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from structures.db import Database
from structures.user import User
from structures.guild import Guild

GOAL_TYPE_DAILY = 'daily'
GOAL_TYPE_WEEKLY = 'weekly'
GOAL_TYPE_MONTHLY = 'monthly'
GOAL_TYPE_YEARLY = 'yearly'

GOAL_TYPES = [GOAL_TYPE_DAILY, GOAL_TYPE_WEEKLY, GOAL_TYPE_MONTHLY, GOAL_TYPE_YEARLY]

class Goal(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.__db = Database.instance()

    @commands.command(name="goal")
    @commands.guild_only()
    async def old(self, context):
        """
        Migrated command, so just display a message for now.
        :param context: Discord context
        """
        return await context.send(lib.get_string('err:slash', context.guild.id))

    async def pre_command_checks(self, context: SlashContext):
        """
        Run pre-command checks, to avoid duplication of code.
        @return:
        """
        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('goal'):
            await context.send(lib.get_string('err:disabled', context.guild_id))
            return False

        return True

    @cog_ext.cog_subcommand(
        base="goal",
        name="set",
        description="Set a writing goal",
        options=[
            create_option(
                name="type",
                description="Type of goal to set",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                choices=[
                    create_choice(name=value, value=value) for value in GOAL_TYPES
                ]
            ),
            create_option(
                name="value",
                description="Word count to set for the goal",
                option_type=SlashCommandOptionType.INTEGER,
                required=True
            )
        ]
    )
    async def goal_set(self, context: SlashContext, type: str, value: int):

        # Run the pre-command checks.
        if await self.pre_command_checks(context) is False:
            return

        return await self.run_set(context, type, value)

    @cog_ext.cog_subcommand(
        base="goal",
        name="check",
        description="Check one or all of your writing goals",
        options=[
            create_option(
                name="type",
                description="Type of goal to check. If not specified, will check all goals.",
                option_type=SlashCommandOptionType.STRING,
                required=False,
                choices=[
                    create_choice(name=value, value=value) for value in GOAL_TYPES
                ]
            )
        ]
    )
    async def goal_check(self, context: SlashContext, type: str = None):

        # Run the pre-command checks.
        if await self.pre_command_checks(context) is False:
            return

        return await self.run_check(context, type)

    @cog_ext.cog_subcommand(
        base="goal",
        name="delete",
        description="Delete one of your writing goals",
        options=[
            create_option(
                name="type",
                description="Type of goal to delete",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                choices=[
                    create_choice(name=value, value=value) for value in GOAL_TYPES
                ]
            )
        ]
    )
    async def goal_delete(self, context: SlashContext, type: str):

        # Run the pre-command checks.
        if await self.pre_command_checks(context) is False:
            return

        return await self.run_cancel(context, type)

    @cog_ext.cog_subcommand(
        base="goal",
        name="time",
        description="Check the time left for one of your writing goals",
        options=[
            create_option(
                name="type",
                description="Type of goal to check",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                choices=[
                    create_choice(name=value, value=value) for value in GOAL_TYPES
                ]
            )
        ]
    )
    async def goal_time(self, context: SlashContext, type: str):

        # Run the pre-command checks.
        if await self.pre_command_checks(context) is False:
            return

        return await self.run_time(context, type)

    @cog_ext.cog_subcommand(
        base="goal",
        name="update",
        description="Update the word count value of a writing goal, without affecting your XP or other goals.",
        options=[
            create_option(
                name="type",
                description="Type of goal to set",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                choices=[
                    create_choice(name=value, value=value) for value in GOAL_TYPES
                ]
            ),
            create_option(
                name="value",
                description="Word count to set for the goal",
                option_type=SlashCommandOptionType.INTEGER,
                required=True
            )
        ]
    )
    async def goal_update(self, context: SlashContext, type: str, value: int):

        # Run the pre-command checks.
        if await self.pre_command_checks(context) is False:
            return

        return await self.run_update(context, type, value)

    @cog_ext.cog_subcommand(
        base="goal",
        name="history",
        description="Check your your history for one of your writing goals",
        options=[
            create_option(
                name="type",
                description="Type of goal to check the history of",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                choices=[
                    create_choice(name=value, value=value) for value in GOAL_TYPES
                ]
            )
        ]
    )
    async def goal_history(self, context: SlashContext, type: str):

        # Run the pre-command checks.
        if await self.pre_command_checks(context) is False:
            return

        return await self.run_history(context, type)

    async def run_update(self, context, type, amount):
        """
        Update the value of a goal, without affecting the others or updating XP, etc...
        Useful for if you want to record the writing you have done, before you started using Writer-Bot.
        @param context:
        @param type:
        @param amount:
        @return:
        """
        user = User(context.author_id, context.guild_id, context)

        type_string = lib.get_string('goal:' + type, user.get_guild())
        user_goal = user.get_goal(type)

        # Check if we can convert the amount to an int
        amount = lib.is_number(amount)
        if not amount:
            return await context.send(user.get_mention() + ', ' + lib.get_string('err:validamount', user.get_guild()))

        # Set the goal's current amount.
        if user_goal and user.update_goal(type, amount):
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:updated', user.get_guild()).format(type_string, amount))
        else:
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:nogoal', user.get_guild()).format(type_string, type))

    async def run_history(self, context, type):
        """
        Get the user's goal history, so they can look back and see how they did for previous goals
        @param context:
        @param type:
        @return:
        """
        user = User(context.author_id, context.guild_id, context)

        type_string = lib.get_string('goal:' + type, user.get_guild()).lower()
        history = user.get_goal_history(type)

        # Build embedded response.
        embed = discord.Embed(title=lib.get_string('goal:history', user.get_guild()).format(type_string), color=10038562)

        # Loop through each history record.
        for record in history:

            title = record['date']
            text = str(record['result']) + '/' + str(record['goal'])
            text += ' :white_check_mark:' if record['completed'] else ''
            embed.add_field(name=title, value=text, inline=False)

        await context.send(embed=embed)

    async def run_check_all(self, context):
        """
        Print a table of all the user's goals.
        @param context:
        @return:
        """

        now = int(time.time())
        user = User(context.author_id, context.guild_id, context)
        embed = discord.Embed(title=lib.get_string('goals', user.get_guild()), color=10038562)

        for type in GOAL_TYPES:

            type_string = lib.get_string('goal:'+type, user.get_guild())
            goal = user.get_goal(type)

            if goal is not None:

                progress = user.get_goal_progress(type)
                seconds_left = goal['reset'] - now
                left = lib.secs_to_days(seconds_left)
                current_wordcount = progress['current']
                goal_wordcount = progress['goal']
                words_remaining = goal_wordcount - current_wordcount

                # If someone has already met their goal, we don't want to calculate how many words they have left
                if words_remaining <= 0:
                    words_remaining = 0

                text = lib.get_string('goal:yourgoal', user.get_guild()).format(type_string, goal['goal']) +  "\n"
                text += lib.get_string('goal:status', user.get_guild()).format(progress['percent'], type_string, current_wordcount, goal_wordcount) + "\n"
                text += lib.get_string('goal:timeleft', user.get_guild()).format(lib.format_secs_to_days(seconds_left), type_string)

                if type != GOAL_TYPE_DAILY:
                    days = left['days']
                    # if someone has, for instance, 3 days 2 hours, count that as 4 days (remainder of today + 3 days)
                    hours = left['hours']
                    days = days + (1 if hours > 0 else 0)
                    if words_remaining > 0:
                        average_wordcount_needed = math.ceil(words_remaining / (1 if days == 0 else days))
                        text += "\n" + lib.get_string('goal:rate', user.get_guild()).format(average_wordcount_needed, type_string)

                if words_remaining == 0:
                    # They met their goal!
                    text += "\n" + lib.get_string('goal:met:noxp', user.get_guild()).format(type_string, goal_wordcount)

            else:
                text = None

            embed.add_field(name=type_string, value=text, inline=False)

        # Send the message
        await context.send(embed=embed)
    #
    async def run_time(self, context, type):
        """
        Check how long until the goal resets
        :param context:
        :param type:
        :return:
        """
        user = User(context.author_id, context.guild_id, context)

        # Get the goal of this type for this user
        goal = user.get_goal(type)
        if goal:

            now = int(time.time())
            reset = goal['reset']
            left = lib.format_secs_to_days(reset - now)
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:timeleft', user.get_guild()).format(left, type))

        else:
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:nogoal', user.get_guild()).format(type, type))

    async def run_cancel(self, context, type):

        user = User(context.author_id, context.guild_id, context)

        user.delete_goal(type)
        return await context.send(user.get_mention() + ', ' + lib.get_string('goal:givenup', user.get_guild()).format(type))

    async def run_set(self, context, type, amount):

        user = User(context.author_id, context.guild_id, context)

        # Check if we can convert the amount to an int
        amount = lib.is_number(amount)
        if not amount:
            return await context.send(user.get_mention() + ', ' + lib.get_string('err:validamount', user.get_guild()))

        # Set the user's goal
        user.set_goal(type, amount)
        timezone = user.get_setting('timezone') or 'UTC'

        reset_every = lib.get_string('goal:set:'+type, user.get_guild())
        return await context.send(user.get_mention() + ', ' + lib.get_string('goal:set', user.get_guild()).format(type, amount, reset_every, timezone))

    async def run_check(self, context, type = None):

        if type is None:
            return await self.run_check_all(context)

        user = User(context.author_id, context.guild_id, context)

        type_string = lib.get_string('goal:' + type, user.get_guild())

        user_goal = user.get_goal(type)
        if user_goal:
            progress = user.get_goal_progress(type)
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:status', user.get_guild()).format(progress['percent'], type_string, progress['current'], progress['goal']))
        else:
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:nogoal', user.get_guild()).format(type_string, type))


def setup(bot):
    bot.add_cog(Goal(bot))