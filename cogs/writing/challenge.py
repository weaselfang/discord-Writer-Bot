import random
import re
import lib
import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from structures.db import Database
from structures.guild import Guild
from structures.user import User

DIFFICULTY_EASY = 0
DIFFICULTY_NORMAL = 1
DIFFICULTY_HARD = 2
DIFFICULTY_HARDCORE = 3
DIFFICULTY_INSANE = 4

class Challenge(commands.Cog):

    WPM={'min': 5, 'max': 30}
    TIMES={'min': 5, 'max': 60}

    def __init__(self, bot):
        self.bot = bot
        self.__db = Database.instance()

    @commands.command(name="challenge")
    @commands.guild_only()
    async def old(self, context):
        """
        Migrated command, so just display a message for now.

        :param context: Discord context
        """
        return await context.send(lib.get_string('err:slash', context.guild_id))

    @cog_ext.cog_subcommand(
        base="challenge",
        name="start",
        description="Generate a writing challenge to complete",
        options=[
            create_option(
                name="difficulty",
                description="How difficult should the challenge be?",
                option_type=SlashCommandOptionType.INTEGER,
                required=False,
                choices=[
                    create_choice(DIFFICULTY_EASY, 'Easy'),
                    create_choice(DIFFICULTY_NORMAL, 'Normal'),
                    create_choice(DIFFICULTY_HARD, 'Hard'),
                    create_choice(DIFFICULTY_HARDCORE, 'Hardcore'),
                    create_choice(DIFFICULTY_INSANE, 'Insane'),
                ]
            ),
            create_option(
                name="length",
                description="How many minutes should the challenge be for? (minimum: 5, maximum: 60)",
                option_type=SlashCommandOptionType.INTEGER,
                required=False,
            )
        ])
    async def start(self, context: SlashContext, difficulty: int = None, length: int = None):
        """
        Generates a random writing challenge for you. e.g. "Write 400 words in 15 minutes".
        You can add the flags "easy", "normal", "hard", "hardcore", or "insane" to choose a pre-set wpm,
        or add your chosen wpm (words per minute) as the flag, suffixed with "wpm", eg. "30wpm",
        or you can specify a time instead by adding a the time in minutes, suffixed with a "m", e.g. "15m".

        If you do not specify any flags with the command, the challenge will be completely random.

        :param SlashContext context: SlashContext object
        :param int difficulty: Difficulty level
        :param int length: Challenge length in mins
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('challenge'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        # Run the start challenge.
        await self.run_challenge(context, difficulty, length)

    @cog_ext.cog_subcommand(
        base="challenge",
        name="cancel",
        description="Cancel the current writing challenge",
    )
    async def cancel(self, context: SlashContext):
        """
        Cancel the current writing challenge

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('challenge'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        # Cancel the challenge.
        await self.run_cancel(context)

    @cog_ext.cog_subcommand(
        base="challenge",
        name="complete",
        description="Mark the current writing challenge as completed",
    )
    async def complete(self, context: SlashContext):
        """
        Mark the current writing challenge as completed

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('challenge'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        # Complete the challenge.
        await self.run_complete(context)

    async def run_challenge(self, context: SlashContext, difficulty: int, length: int):
        """
        Start the challenge

        :param SlashContext context: SlashContext object
        :param int difficulty: Difficulty level
        :param int length: Challenge length in mins
        :rtype: void
        """

        user = User(context.author_id, context.guild_id, context)

        challenge = user.get_challenge()

        # If they already have a challenge running, display the info.
        if challenge:
            output = lib.get_string('challenge:accepted', user.get_guild()) + '\n**' + \
                     challenge['challenge'] + '**\n' + \
                     lib.get_string('challenge:tocomplete', user.get_guild())
            await context.send(f'{context.author.mention}, {output}')
            return

        # First create a random WPM and time and then adjust if they are actually specified
        wpm = random.randint(self.WPM['min'], self.WPM['max'])
        time = random.randint(self.TIMES['min'], self.TIMES['max'])

        # If they specified a difficulty, use that instead.
        if difficulty is not None:

            # Convert the flag to the corresponding WPM
            if difficulty == DIFFICULTY_EASY:
                wpm = random.randint(3, 5)
            elif difficulty == DIFFICULTY_NORMAL:
                wpm = random.randint(10, 15)
            elif difficulty == DIFFICULTY_HARD:
                wpm = random.randint(20, 30)
            elif difficulty == DIFFICULTY_HARDCORE:
                wpm = random.randint(35, 45)
            elif difficulty == DIFFICULTY_INSANE:
                wpm = random.randint(50, 60)

        # If they specified a valid length, use that instead.
        if length is not None and length >= self.TIMES['min'] and length <= self.TIMES['max']:
            time = length

        # Calculate the word goal and xp it will grant.
        goal = wpm * time
        xp = self.calculate_xp(wpm)

        # Set the challenge.
        challenge = lib.get_string('challenge:challenge', user.get_guild()).format(words=goal, mins=time, wpm=wpm)
        user.set_challenge(challenge, xp)

        # Display a message confirming it.
        output = lib.get_string('challenge:accepted', user.get_guild()) + '\n**' + challenge + '**\n' + lib.get_string('challenge:tocomplete', user.get_guild())

        await context.send(context.author.mention + ', ' + output)

    def calculate_xp(self, wpm):
        """
        Calculate the XP to give for the challenge, based on the words per minute.

        :param int wpm: Words per minute
        :rtype: int
        """
        if wpm <= 5:
            return 20
        elif wpm <= 15:
            return 40
        elif wpm <= 30:
            return 75
        elif wpm <= 45:
            return 100
        elif wpm > 45:
            return 150

    async def run_complete(self, context: SlashContext):
        """
        Mark the current challenge as completed.

        :param SlashContext context:
        :rtype: void
        """

        user = User(context.author_id, context.guild_id, context)

        # Do they have an active challenge to mark as complete?
        challenge = user.get_challenge()
        if challenge:

            # Update the challenge with the time completed
            user.complete_challenge(challenge['id'])

            # Add the XP
            await user.add_xp(challenge['xp'])

            # Increment the challenges_completed stat
            user.add_stat('challenges_completed', 1)

            output = lib.get_string('challenge:completed', user.get_guild()) + ' **' + challenge['challenge'] + '**          +' + str(challenge['xp']) + 'xp'

        else:
            output = lib.get_string('challenge:noactive', user.get_guild())

        await context.send(f'{context.author.mention}, {output}')

    async def run_cancel(self, context: SlashContext):
        """
        Cancel the current challenge

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        user = User(context.author_id, context.guild_id, context)
        challenge = user.get_challenge()

        if challenge:
            user.delete_challenge()
            output = lib.get_string('challenge:givenup', user.get_guild())
        else:
            output = lib.get_string('challenge:noactive', user.get_guild())

        await context.send(f'{context.author.mention}, {output}')



def setup(bot):
    bot.add_cog(Challenge(bot))