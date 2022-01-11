import json
import lib
import random
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from structures.guild import Guild

class Fun(commands.Cog):

    ROLL_MAX_SIDES = 1000000000000
    ROLL_MAX_ROLLS = 100

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="8ball", aliases=["flip", "quote", "reassure", "roll"])
    @commands.guild_only()
    async def old(self, context):
        """
        Migrated command, so just display a message for now.

        :param context: Discord context
        """
        return await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(
        name="8ball",
        description="Ask the magic 8ball a question",
        options=[
            create_option(
                name="question",
                description="What is your question for the magic 8ball?",
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
    ])
    async def _8ball(self, context: SlashContext, question: str):
        """
        Ask the magic 8-ball a question.

        :param SlashContext context: SlashContext object
        :param str question: The question the user is asking
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('8ball'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        guild_id = context.guild_id

        # Pick a random answer
        i: int = random.randrange(21)
        answer: str = lib.get_string(f"8ball:{i}", guild_id)

        # Send the message
        await context.send(
            context.author.mention + ', ' + lib.get_string('8ball:yourquestion', guild_id).format(question) + answer)

    @cog_ext.cog_slash(
        name="flip",
        description="Flip a coin"
    )
    async def flip(self, context: SlashContext):
        """
        Flips a coin.

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('flip'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        guild_id = context.guild_id

        # Random number between 1-2 to choose heads or tails.
        rand = random.randrange(2)
        side = 'heads' if rand == 0 else 'tails'

        # Send the message.
        await context.send(lib.get_string('flip:' + side, guild_id))

    @cog_ext.cog_slash(
        name="quote",
        description="Generate a random motivational quote"
    )
    async def quote(self, context: SlashContext):
        """
        A random motivational quote to inspire you.

        :param SlashContext context: SlashContext object
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('quote'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        guild_id = context.guild_id

        # Load the JSON file with the quotes
        quotes = lib.get_asset('quotes', guild_id)

        # Choose a random quote.
        max = len(quotes) - 1
        quote = quotes[random.randint(1, max)]

        # Send the message
        await context.send(format(quote['quote'] + ' - *' + quote['name'] + '*'))

    @cog_ext.cog_slash(
        name="reassure",
        description="Send a random reassuring message to a user or yourself",
        options=[
            create_option(
                name="who",
                description="Who do you want to reassure?",
                option_type=SlashCommandOptionType.USER,
                required=False
            )
    ])
    async def reassure(self, context: SlashContext, who: str = None):
        """
        Reassures you that everything will be okay.

        :param SlashContext context: SlashContext object
        :param str|None who: The name of the user to reassure
        :rtype: void
        """
        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('reassure'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        guild_id = context.guild_id

        # If no name passed through, default to the author of the command.
        if who is None:
            mention = context.author.mention
        else:
            mention = who.mention

        # Load the JSON file with the quotes.
        messages = lib.get_asset('reassure', guild_id)

        # Pick a random message.
        max = len(messages) - 1
        quote = messages[random.randint(1, max)]

        # Send the message.
        await context.send(mention + ', ' + format(quote))

    @cog_ext.cog_slash(
        name="roll",
        description="Roll some dice",
        options=[
            create_option(
                name="dice",
                description="What dice do you want to roll? Format: {number}d{sides}, e.g. 1d20, 2d8, etc... Default: 1d6",
                option_type=SlashCommandOptionType.STRING,
                required=False
            )
    ])
    async def roll(self, context, dice: str = '1d6'):
        """
        Rolls a dice between 1-6, or 1 and a specified number (max 100). Can also roll multiple dice at once (max 100) and get the total.

        :param SlashContext context: SlashContext object
        :param str dice: The dice to roll, e.g. 1d6, 2d10, etc...
        :rtype: void
        """

        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer()

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('roll'):
            return await context.send(lib.get_string('err:disabled', context.guild_id))

        guild_id = context.guild_id

        # Make sure the format is correct (1d6).
        try:
            sides = int(dice.split('d')[1])
            rolls = int(dice.split('d')[0])
        except Exception as e:
            await context.send(lib.get_string('roll:format', guild_id));
            return

        # Make sure the sides and rolls are valid.
        if sides < 1:
            sides = 1
        elif sides > self.ROLL_MAX_SIDES:
            sides = self.ROLL_MAX_SIDES

        if rolls < 1:
            rolls = 1
        elif rolls > self.ROLL_MAX_ROLLS:
            rolls = self.ROLL_MAX_ROLLS

        total = 0
        output = ''

        # Roll the dice {rolls} amount of times.
        for x in range(rolls):
            val = random.randint(1, sides)
            total += val
            output += ' [ ' + str(val) + ' ] '

        # Now print out the total.
        output += '\n**' + lib.get_string('roll:total', guild_id) + str(total) + '**';

        # Send message.
        await context.send(output)

def setup(bot):
    """
    Add the cog to the bot
    :param bot: Discord bot
    :rtype void:
    """
    bot.add_cog(Fun(bot))
