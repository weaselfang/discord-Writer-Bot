import lib, random
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option
from structures.guild import Guild

class Roll(commands.Cog):

    MAX_SIDES = 1000000000000
    MAX_ROLLS = 100

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="roll")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

    @cog_ext.cog_slash(name="roll", description="Roll some dice", options=[
        create_option(name="dice",
                      description="What dice do you want to roll? Format: {number}d{sides}, e.g. 1d20, 2d8, etc... Default: 1d6",
                      option_type=SlashCommandOptionType.STRING,
                      required=False)
    ])
    async def roll(self, context, dice: str ='1d6'):
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
            await context.send( lib.get_string('roll:format', guild_id) );
            return

        # Make sure the sides and rolls are valid.
        if sides < 1:
            sides = 1
        elif sides > self.MAX_SIDES:
            sides = self.MAX_SIDES

        if rolls < 1:
            rolls = 1
        elif rolls > self.MAX_ROLLS:
            rolls = self.MAX_ROLLS

        total = 0
        output = ''

        # Roll the dice {rolls} amount of times.
        for x in range(rolls):

            val = random.randint(1, sides)
            total += val
            output += ' [ '+str(val)+' ] '

        # Now print out the total.
        output += '\n**'+lib.get_string('roll:total', guild_id) + str(total) + '**';

        # Send message.
        await context.send( output )



def setup(bot):
    bot.add_cog(Roll(bot))