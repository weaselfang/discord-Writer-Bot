import math
from typing import List, Optional

from discord.ext import commands
from discord_slash.cog_ext import cog_subcommand
from discord_slash.context import SlashContext, InteractionContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from validator_collection import checkers

import lib
from structures.guild import Guild
from structures.project import Project
from structures.user import User


class ProjectCommand(commands.Cog):
    """
    The project command allows you to create different projects and store word counts against them separately.
    They also integrate with the `wrote` and `sprint` commands, allowing you to define words written against a chosen project.
    (See the help information for those commands for more info).
    """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @cog_subcommand(
        base="project",
        name="create",
        description="Create a new project",
        options=[
            create_option(
                name="shortname",
                description="shortname of the project you want to configure",
                required=True,
                option_type=SlashCommandOptionType.STRING,
            ),
            create_option(
                name="title",
                description="title of the project you want to configure",
                required=True,
                option_type=SlashCommandOptionType.STRING,
            )
        ]
    )
    async def project_create(self, context: SlashContext, shortname: str, title: str):
        """Create a new project"""
        if not Guild(context.guild).is_command_enabled('project'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        shortname = shortname.lower()

        # Make sure that the title is less than 100 chars
        if len(title) > 100:
            return await context.send(context.author.mention + ', '
                                      + lib.get_string('project:err:length', context.guild_id))

        # Make sure they don't already have a project with this shortname
        if Project.get(context.author_id, shortname) is not None:
            return await context.send(context.author.mention + ', '
                                      + lib.get_string('project:err:exists', context.guild_id)
                                      .format(shortname))

        # Create the project
        Project.create(context.author_id, shortname, title)
        return await context.send(context.author.mention + ', '
                                  + lib.get_string('project:created', context.guild_id)
                                  .format(title, shortname))

    @cog_subcommand(
        base="project",
        name="list",
        description="List user projects",
        options=[
            create_option(
                name="status",
                description="display only projects with this status",
                option_type=SlashCommandOptionType.STRING,
                required=False,
                choices=[
                    create_choice(status, status) for status in Project.STATUS_EMOTES.keys()
                ]
            ),
            create_option(
                name="genre",
                description="set the genre of the project",
                option_type=SlashCommandOptionType.STRING,
                required=False,
                choices=[
                    create_choice(genre, genre) for genre in Project.GENRE_EMOTES.keys()
                ]
            )
        ]
    )
    async def project_list(self, context: SlashContext, status: str = None, genre: str = None):
        """View a list of the user's projects"""
        if not Guild(context.guild).is_command_enabled('project'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        await context.defer()
        return await self._draw_projects(
            context,
            None if status is None else [status],
            None if genre is None else [genre]
        )

    @classmethod
    async def _draw_projects(cls, context: InteractionContext, status: Optional[List[str]] = None,
                             genre: Optional[List[str]] = None):
        projects = Project.all(user=context.author_id)

        # If they have no projects, then we can't display them.
        if len(projects) < 1:
            return await context.send(context.author.mention + ', '
                                      + lib.get_string('project:noprojects', context.guild_id))

        filter_string: str = ""

        if status is not None:
            projects = filter(lambda project: project.status in status, projects)
            filter_string += ', '.join(
                [lib.get_string(f'project:status:{s}', context.guild_id) for s in status]
            )

        if genre is not None:
            projects = filter(lambda project: project.genre in genre, projects)
            genres_string = ', '.join(
                [lib.get_string(f'project:genre:{g}', context.guild_id) for g in genre]
            )
            if len(filter_string) > 0 and len(genres_string) > 0:
                filter_string += '; ' + genres_string

        if not len(filter_string) > 0:
            filter_string = lib.get_string('all', context.guild_id)

        # add list header
        message = context.author.mention + ', '
        message += lib.get_string('project:list', context.guild_id).format(filter_string)
        message += '\n\n'.join([project.abbrev(context) for project in projects])

        buffer = ""
        for line in message.splitlines(keepends=True):
            if len(buffer) + len(line) > 2000:
                await context.send(buffer)
                # reset buffer after flushing
                buffer = ""

            buffer += line

        # send any remaining lines
        if len(buffer) > 0:
            await context.send(buffer)

    @cog_subcommand(
        base="project",
        name="set",
        description="Change info of a project. see also `/project update` and `/project rename`",
        options=[
            create_option(
                name="shortname",
                description="shortname of the project you want to configure",
                required=True,
                option_type=SlashCommandOptionType.STRING,
            ),
            create_option(
                name="description",
                description="Sets the description/blurb of the project",
                option_type=SlashCommandOptionType.STRING,
                required=False
            ),
            create_option(
                name="genre",
                description="set the genre of the project",
                option_type=SlashCommandOptionType.STRING,
                required=False,
                choices=[
                    create_choice(genre, genre) for genre in Project.GENRE_EMOTES.keys()
                ]
            ),
            create_option(
                name="status",
                description="set the status of the project",
                option_type=SlashCommandOptionType.STRING,
                required=False,
                choices=[
                    create_choice(status, status) for status in Project.STATUS_EMOTES.keys()
                ]
            ),
            create_option(
                name="link",
                description="Sets the hyperlink for your project's web/store page",
                option_type=SlashCommandOptionType.STRING,
                required=False
            ),
            create_option(
                name="image",
                description="Sets the thumbnail picture link to use for this project",
                option_type=SlashCommandOptionType.STRING,
                required=False
            )
        ]
    )
    async def project_set(self, context: SlashContext, shortname: str, description: str = None,
                          genre: str = None, status: str = None, link: str = None,
                          image: str = None):
        await context.defer()
        if not Guild(context.guild).is_command_enabled('project'):
            return await context.send(lib.get_string('err:disabled', context.guild.id))

        project: Project = Project.get(context.author_id, shortname)
        if not project:
            return await context.send(context.author.mention + ', '
                                      + lib.get_string('project:err:noexists', context.guild_id)
                                      .format(shortname))

        message = context.author.mention + ', '
        message += lib.get_string('project:set:header', context.guild_id).format(shortname)

        delim = '\n\t'

        if description is not None:
            # Description cannot be longer than 200 words.
            words = len(description.split(' '))
            if words > 200:
                return await context.send(
                    context.author.mention + ', '
                    + lib.get_string('project:err:desc:length', context.guild_id).format(words)
                )
            project.description = description
            message += delim + lib.get_string('project:description', context.guild_id)
        if genre is not None:
            # Make sure the genre is valid.
            if genre not in Project.GENRE_EMOTES.keys():
                return await context.send(
                    context.author.mention + ', '
                    + lib.get_string('project:err:genre', context.guild_id)
                    .format(genre, ', '.join(Project.GENRE_EMOTES.keys()))
                )
            project.genre = genre
            message += delim + lib.get_string('project:genre', context.guild_id).format(
                lib.get_string(f'project:genre:{genre}', context.guild_id)
            )

        if status is not None:
            # Make sure the status is valid.
            if status not in Project.STATUS_EMOTES.keys():
                return await context.send(
                    context.author.mention + ', ' +
                    lib.get_string('project:err:status', context.guild_id)
                    .format(status, ', '.join(Project.STATUS_EMOTES.keys())))

            # If we are marking it finished or published for the first time, add xp.
            if (status == 'finished' or status == 'published') and not project.is_complete():
                xp = math.ceil(project.words / 100)
                xp = max(10, min(xp, 5000))
                await User(context.author_id, context.guild_id).add_xp(xp)
                await context.send(
                    context.author.mention + ', '
                    + lib.get_string('project:completed', context.guild_id).format(project.name, xp)
                )

            project.status = status
            message += delim + lib.get_string('project:status', context.guild_id).format(
                lib.get_string(f'project:status:{status}', context.guild_id))
        if link is not None:
            # Check it's a valid link.
            if not checkers.is_url(link):
                return await context.send(
                    context.author.mention + ', '
                    + lib.get_string('project:err:link', context.guild_id)
                    .format(link)
                )

            project.link = link
            message += delim + lib.get_string('project:link', context.guild_id).format(link)
        if image is not None:
            # Check it's a valid link.
            if not checkers.is_url(image):
                return await context.send(
                    context.author.mention + ', '
                    + lib.get_string('project:err:link', context.guild_id).format(image)
                )

            project.image = image
            message += delim + lib.get_string('project:image', context.guild_id).format(link)

        if not message.endswith(':'):
            return await context.reply(message)
        else:
            return await context.reply(
                context.author.mention + ', '
                + lib.get_string('project:err:nothingtoset', context.guild_id)
            )

    @cog_subcommand(
        base="project",
        name="view",
        options=[
                create_option(
                    name="shortname",
                    description="shortname of the project",
                    option_type=SlashCommandOptionType.STRING,
                    required=True
                )
            ]
    )
    async def project_view(self, context: SlashContext, shortname: str):
        """View a specific project"""
        await context.defer()

        project = Project.get(context.author_id, shortname)
        if not project:
            return await context.send(
                context.author.mention + ', '
                + lib.get_string('project:err:noexists', context.guild_id).format(shortname)
            )

        # Display the embedded message response for this project.
        return await context.reply(embed=project.embed(context))

    @cog_subcommand(
        base="project",
        name="delete",
        description="Delete a project",
        options=[
            create_option(
                name="shortname",
                description="shortname of the project to delete",
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
        ]
    )
    async def project_delete(self, context: SlashContext, shortname: str):
        """Delete a project"""
        await context.defer()
        # Make sure the project exists first
        project = Project.get(context.author_id, shortname)
        if not project:
            return await context.send(
                context.author.mention + ', '
                + lib.get_string('project:err:noexists', context.guild_id).format(shortname)
            )

        # Delete it.
        project.delete()
        return await context.send(
            context.author.mention + ', '
            + lib.get_string('project:deleted', context.guild_id)
            .format(project.name, project.shortname)
        )

    @cog_subcommand(
        base="project",
        name="rename",
        description="Change the title or shortname of a project. see also `/project set`",
        options=[
            create_option(
                name="old_shortname",
                description="The old/current shortname of the project you want to rename.",
                option_type=SlashCommandOptionType.STRING,
                required=True
            ),
            create_option(
                name="new_shortname",
                description="The new shortname for the project. Defaults to the old one.",
                option_type=SlashCommandOptionType.STRING,
                required=False
            ),
            create_option(
                name="new_title",
                description="The new title for the project. Defaults to the old one.",
                option_type=SlashCommandOptionType.STRING,
                required=False
            )
        ]
    )
    async def project_rename(self, context: SlashContext, old_shortname: str,
                             new_shortname: str = None, new_title: str = None):
        """Change the title or shortname of a project"""
        await context.defer()

        # Make sure the project exists
        project = Project.get(context.author_id, old_shortname)
        if not project:
            return await context.send(
                context.author.mention + ', '
                + lib.get_string('project:err:noexists', context.guild_id).format(old_shortname)
            )

        # Get the original title.
        old_title = project.name

        # if they gave the same shortname, they shouldn't have specified the argument.
        if new_shortname == old_shortname:
            new_shortname = None
        if new_title == old_title:
            new_title = None

        if new_shortname is None and new_title is None:
            return await context.reply(f'{context.author.mention}, nothing to set!')

        # Make sure they don't already have one with that new shortname.
        if new_shortname is not None and Project.get(context.author_id, new_shortname) is not None:
            return await context.send(
                context.author.mention + ', '
                + lib.get_string('project:err:exists', context.guild_id).format(new_shortname)
            )

        if new_shortname is None:
            new_shortname = old_shortname
        if new_title is None:
            new_title = old_title

        new_shortname = new_shortname.lower()

        # Rename it.
        project.rename(new_shortname, new_title)
        return await context.send(
            context.author.mention + ', '
            + lib.get_string('project:renamed', context.guild_id)
            .format(old_title, old_shortname, new_title, new_shortname)
        )

    @cog_subcommand(
        base="project",
        name="update",
        description="Update project word count",
        options=[
            create_option(
                name="shortname",
                description="shortname of the project to update",
                option_type=SlashCommandOptionType.STRING,
                required=True
            ),
            create_option(
                name="wc",
                description="new absolute project word count (see `/wrote` for incrementing)",
                option_type=SlashCommandOptionType.INTEGER,
                required=True
            )
        ]
    )
    async def project_update(self, context: SlashContext, shortname: str, wc: int):
        """Update project word count"""
        # Make sure the project exists.
        project = Project.get(context.author_id, shortname)
        if not project:
            return await context.send(
                context.author.mention + ', '
                + lib.get_string('project:err:noexists', context.guild_id).format(shortname)
            )

        # Update the word count.
        project.words = wc
        return await context.send(
            context.author.mention + ', '
            + lib.get_string('project:updated', context.guild_id)
            .format(wc, project.name, project.shortname)
        )

    @commands.command(name="project")
    @commands.guild_only()
    async def old(self, context):
        return await context.send(lib.get_string('err:slash', context.guild.id))


def setup(bot):
    bot.add_cog(ProjectCommand(bot))
