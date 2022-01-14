import lib
import time
from discord.ext import commands
from structures.generator import NameGenerator
from structures.user import User
from structures.wrapper import CommandWrapper
from structures.guild import Guild
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice

SUPPORTED_TYPES = {
    'char': 'Character',
    'place': 'Place',
    'land': 'Land',
    'idea': 'Idea',
    'book': 'Book',
    'book_fantasy': 'Fantasy Book',
    'book_horror': 'Horror Book',
    'book_hp': 'Harry Potter Book',
    'book_mystery': 'Mystery Book',
    'book_rom': 'Romance Book',
    'book_sf': 'Sci-Fi Book',
    'prompt': 'Prompt',
    'face': 'Face',
    'question_char': 'Character-building question',
    'question_world': 'World-building question',
}

class Generate(commands.Cog, CommandWrapper):

    def __init__(self, bot):
        self.bot = bot
        self._urls = {
            'face': 'https://thispersondoesnotexist.com/image'
        }

    @cog_ext.cog_slash(
        name="generate",
        description="Random generator for character names, place names, land names, book titles, story ideas, prompts.",
        options=[
            create_option(
                name="type",
                description="What to generate",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                choices=[
                    create_choice(
                        name=name,
                        value=value
                    ) for value, name in SUPPORTED_TYPES.items()
                ]
            ),
            create_option(
                name="amount",
                description="How many items to generate",
                required=False,
                option_type=SlashCommandOptionType.INTEGER
            ),
            create_option(
                name="hidden",
                description="Should the response be in a hidden message?",
                option_type=SlashCommandOptionType.BOOLEAN,
                required=False
            )
        ]
    )
    async def generate(self, context: SlashContext, type: str, amount: int = None,
                       hidden: bool = False):
        """
        Random generator for various things (character names, place names, land names, book titles, story ideas, prompts).
        Define the type of item you wanted generated and then optionally, the amount of items to generate.

        :param SlashContext context: Slash command context
        :param str type: Type of generation to do
        :param int amount: Amount of items to get
        :param bool hidden: Should the response be hidden to other users
        :rtype void:
        """
        # Send "bot is thinking" message, to avoid failed commands if latency is high.
        await context.defer(hidden=hidden)

        # Make sure the guild has this command enabled.
        if not Guild(context.guild).is_command_enabled('generate'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        user = User(context.author_id, context.guild.id, context)

        # If no amount specified, use the default
        if amount is None:
            amount = NameGenerator.DEFAULT_AMOUNT

        # For faces, we want to just call an API url.
        if type == 'face':
            return await context.send(self._urls['face'] + '?t=' + str(int(time.time())))

        generator = NameGenerator(type, context)
        results = generator.generate(amount)
        join = '\n'

        # For prompts, add an extra line between them.
        if type == 'prompt':
            join += '\n'

        names = join.join(results['names'])

        return await context.send(user.get_mention() + ', ' + results['message'] + names)

    @commands.command(name="generate")
    @commands.guild_only()
    async def old(self, context):
        await context.send(lib.get_string('err:slash', context.guild.id))

def setup(bot):
    bot.add_cog(Generate(bot))
