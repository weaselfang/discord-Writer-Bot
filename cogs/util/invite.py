import discord, lib
from discord.ext import commands
from structures.guild import Guild

class Invite(commands.Cog):

    @commands.command(name='invite')
    @commands.guild_only()
    async def invite(self, context):
        """
        Displays an embed with and invite link
        """
        if not Guild(context.guild).is_command_enabled('invite'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        config=lib.get('./settings.json')
        invite_embed=discord.Embed(title='Invite Link', color=652430, url=config.invite_url)
        invite_embed.add_field(name='Click the title for the invite link!', value="Use the Above link to invite the bot to your servers!")

        await context.send(embed=invite_embed)


def setup(bot):
    bot.add_cog(Invite(bot))
