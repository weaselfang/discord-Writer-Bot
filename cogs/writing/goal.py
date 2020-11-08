import discord, lib, time
from discord.ext import commands
from structures.db import Database
from structures.user import User
from structures.wrapper import CommandWrapper

class Goal(commands.Cog, CommandWrapper):

    def __init__(self, bot):
        self.bot = bot
        self.__db = Database.instance()
        self._arguments = [
            {
                'key': 'option',
                'prompt': 'goal:argument:option',
                'required': True
            },
            {
                'key': 'value',
                'required': False
            }
        ]
        self.types = ['daily', 'weekly', 'monthly', 'yearly']

    @commands.command(name="goal")
    @commands.guild_only()
    async def goal(self, context, option=None, type=None, value=None):
        """
        Sets a daily goal which resets every 24 hours at midnight in your timezone.

        Examples:
            !goal - Print a table of all your goals, with their progress and next reset time.
            !goal check daily - Checks how close you are to your daily goal
            !goal set weekly 500 - Sets your weekly goal to be 500 words per day
            !goal cancel monthly - Deletes your monthly goal
            !goal time daily - Checks how long until your daily goal resets
        """
        user = User(context.message.author.id, context.guild.id, context)

        # If no option is sent and we just do `goal` then display a table of all their goals.
        if option is None:
            return await self.run_check_all(context)

        # Otherwise, we must specify a type.
        if type is None or type not in self.types:
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:invalidtype', user.get_guild()))

        if option == 'set':
            return await self.run_set(context, type, value)
        elif option == 'cancel' or option == 'delete' or option == 'reset':
            return await self.run_cancel(context, type)
        elif option == 'time':
            return await self.run_time(context, type)
        elif option == 'check':
            return await self.run_check(context, type)
        else:
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:invalidoption', user.get_guild()))

    async def run_check_all(self, context):
        """
        Print a table of all the user's goals.
        @param context:
        @return:
        """

        now = int(time.time())
        user = User(context.message.author.id, context.guild.id, context)
        embed = discord.Embed(title=lib.get_string('goals', user.get_guild()), color=10038562)

        for type in self.types:

            goal = user.get_goal(type)
            if goal is not None:
                progress = user.get_goal_progress(type)
                left = lib.secs_to_days(goal['reset'] - now)
                text = lib.get_string('goal:yourgoal', user.get_guild()).format(type, goal['goal']) +  "\n"
                text += lib.get_string('goal:status', user.get_guild()).format(progress['percent'], type, progress['current'], progress['goal']) + "\n"
                text += lib.get_string('goal:timeleft', user.get_guild()).format(left, type)
            else:
                text = None

            embed.add_field(name=lib.get_string('goal:'+type, user.get_guild()), value=text, inline=False)

        # Send the message
        await context.send(embed=embed)

    async def run_time(self, context, type):
        """
        Check how long until the goal resets
        :param context:
        :param type:
        :return:
        """
        user = User(context.message.author.id, context.guild.id, context)

        # Get the goal of this type for this user
        goal = user.get_goal(type)
        if goal:

            now = int(time.time())
            reset = goal['reset']
            left = lib.secs_to_days(reset - now)
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:timeleft', user.get_guild()).format(left, type))

        else:
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:nogoal', user.get_guild()).format(type, type))



    async def run_cancel(self, context, type):

        user = User(context.message.author.id, context.guild.id, context)
        user.delete_goal(type)
        return await context.send(user.get_mention() + ', ' + lib.get_string('goal:givenup', user.get_guild()))

    async def run_set(self, context, type, amount):

        user = User(context.message.author.id, context.guild.id, context)

        # Check if we can convert the amount to an int
        amount = lib.is_number(amount)
        if not amount:
            return await context.send(user.get_mention() + ', ' + lib.get_string('err:validamount', user.get_guild()))

        # Set the user's goal
        user.set_goal(type, amount)
        timezone = user.get_setting('timezone') or 'UTC'

        reset_every = '?'
        if type == "daily":
            reset_every = 'day'
        elif type == "weekly":
            reset_every = 'week'
        elif type == "monthly":
            reset_every = 'month'
        elif type == "yearly":
            reset_every = 'year'

        return await context.send(user.get_mention() + ', ' + lib.get_string('goal:set', user.get_guild()).format(type, amount, reset_every, timezone))

    async def run_check(self, context, type):

        user = User(context.message.author.id, context.guild.id, context)

        user_goal = user.get_goal(type)
        if user_goal:
            progress = user.get_goal_progress(type)
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:status', user.get_guild()).format(progress['percent'], type, progress['current'], progress['goal']))
        else:
            return await context.send(user.get_mention() + ', ' + lib.get_string('goal:nogoal', user.get_guild()).format(type, type))


def setup(bot):
    bot.add_cog(Goal(bot))