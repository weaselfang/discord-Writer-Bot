import discord, lib, math
from discord.ext import commands
from structures.user import User
from structures.wrapper import CommandWrapper
from validator_collection import checkers

class Project(commands.Cog, CommandWrapper):

    def __init__(self, bot):
        self.bot = bot
        self._supported_commands = ['create', 'delete', 'rename', 'update', 'view', 'list', 'status', 'genre', 'description', 'link', 'image', 'img']
        self._statuses = ['planning', 'progress', 'editing', 'published', 'finished', 'abandoned']
        self._genres = ['fantasy', 'scifi', 'romance', 'horror', 'fiction', 'nonfiction', 'short', 'mystery', 'thriller', 'crime', 'erotic', 'comic']
        self._arguments = [
            {
                'key': 'cmd',
                'prompt': 'project:argument:cmd',
                'required': True,
                'check': lambda content: content in self._supported_commands,
                'error': 'project:err:argument:cmd'
            }
        ]

    @commands.command(name="project")
    @commands.guild_only()
    async def project(self, context, cmd=None, *opts):
        """
        The project command allows you to create different projects and store word counts against them separately. They also integrate with the `wrote` and `sprint` commands, allowing you to define words written against a chosen project. (See the help information for those commands for more info).

        Examples:
            `project create sword The Sword in the Stone` - Creates a new project with the shortname "sword" (used to reference the project when you want to update it), and the full title "The Sword in the Stone".
            `project delete sword` - Deletes the project with the shortname "sword"
            `project rename sword sword2 The Sword in the Stone Two` - Renames the project with the shortname "sword" to - shortname:sword2, title:The Sword in the Stone Two (If you want to keep the same shortname but change the title, just put the same shortname, e.g. `project rename sword sword The Sword in the Stone Two`.
            `project update sword 65000` - Sets the word count for the project with the shortname "sword" to 65000.
            `project list` - Views a list of all your projects.
            `project list status published` - Views a list of all your projects with the `published` status.
            `project list genre fantasy` - Views a list of all your projects with the `fantasy` genre.
            `project view sword` - Views the information about the project with the shortname "sword".
            `project status sword published` - Sets the status of the project to `published`.
            `project genre sword fantasy` - Sets the genre of the project to `fantasy`.
            `project description sword Young boy finds sword, becomes king` - Sets the description/blurb of the project.
            `project link sword http://website.com/your-book` - Sets the hyperlink for your project's web/store page.
            `project img sword http://website.com/picture.png` - Sets the thumbnail picture to use for this project.
        """
        user = User(context.message.author.id, context.guild.id, context)

        # Check the arguments were all supplied and get a dict list of them and their values, after any prompts
        args = await self.check_arguments(context, cmd=cmd)
        if not args:
            return

        # Overwrite the variables passed in, with the values from the prompt and convert to lowercase
        cmd = args['cmd'].lower()

        # Make sure some options have been sent through
        if len(opts) == 0 and cmd != 'view' and cmd != 'list':
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:options', user.get_guild()))

        # Check which command is being run and run it.
        # Since the options can have spaces in them, we need to send the whole thing through as a list and then work out what is what in the command.
        if cmd == 'create':
            return await self.run_create(context, opts)
        elif cmd == 'delete':
            return await self.run_delete(context, opts)
        elif cmd == 'rename':
            return await self.run_rename(context, opts)
        elif cmd == 'update':
            return await self.run_update(context, opts)
        elif cmd == 'view':
            return await self.run_view(context, opts)
        elif cmd == 'list':
            return await self.run_list(context, opts)
        elif cmd == 'status':
            return await self.run_status(context, opts)
        elif cmd == 'genre':
            return await self.run_genre(context, opts)
        elif cmd == 'description':
            return await self.run_description(context, opts)
        elif cmd == 'link':
            return await self.run_link(context, opts)
        elif cmd == 'image' or cmd == 'img':
            return await self.run_image(context, opts)

    async def run_image(self, context, opts):
        """
        Update the image link of a project
        @param context:
        @param opts:
        @return:
        """
        user = User(context.message.author.id, context.guild.id, context)
        shortname = opts[0].lower() if opts else None
        img = opts[1] if len(opts) > 1 else None

        # Make sure the project exists.
        project = user.get_project(shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(shortname))

        # Check it's a valid image link.
        if not checkers.is_url(img) and img is not None:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:link', user.get_guild()).format(img))

        project.set_image(img)
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:image', user.get_guild()))

    async def run_link(self, context, opts):
        """
        Update the hyperlink of a project
        @param context:
        @param opts:
        @return:
        """
        user = User(context.message.author.id, context.guild.id, context)
        shortname = opts[0].lower() if opts else None
        link = opts[1] if len(opts) > 1 else None

        # Make sure the project exists.
        project = user.get_project(shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(shortname))

        # Check it's a valid link.
        if not checkers.is_url(link) and link is not None:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:link', user.get_guild()).format(link))

        project.set_link(link)
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:link', user.get_guild()).format(link))

    async def run_description(self, context, opts):
        """
        Update the description of a project
        @param context:
        @param opts:
        @return:
        """
        user = User(context.message.author.id, context.guild.id, context)
        shortname = opts[0].lower()
        description = " ".join(opts[1:])

        # Make sure the project exists.
        project = user.get_project(shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(shortname))

        # Description cannot be longer than 200 words.
        words = description.split(' ')
        if len(words) > 200:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:desc:length', user.get_guild()).format(len(words)))

        project.set_description(description)
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:description', user.get_guild()))

    async def run_genre(self, context, opts):
        """
        Update the genre of a project
        @param context:
        @param opts:
        @return:
        """
        user = User(context.message.author.id, context.guild.id, context)
        shortname = opts[0].lower() if opts else None
        genre = opts[1].lower() if len(opts) > 1 else None

        # Make sure the project exists.
        project = user.get_project(shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(shortname))

        # Make sure the genre is valid.
        if not genre in self._genres:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:genre', user.get_guild()).format(genre, ', '.join(self._genres)))

        project.set_genre(genre)
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:genre', user.get_guild()).format(lib.get_string('project:genre:'+genre, user.get_guild())))

    async def run_status(self, context, opts):
        """
        Update the status of a project
        @param context:
        @param opts:
        @return:
        """
        user = User(context.message.author.id, context.guild.id, context)
        shortname = opts[0].lower() if opts else None
        status = opts[1].lower() if len(opts) > 1 else None

        # Make sure the project exists.
        project = user.get_project(shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(shortname))

        # Make sure the status is valid.
        if not status in self._statuses:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:status', user.get_guild()).format(status, ', '.join(self._statuses)))

        # If we are marking it finished or published for the first time, add xp.
        if (status == 'finished' or status == 'published') and not project.is_complete():
            xp = math.ceil(project.get_words() / 100)
            if xp < 10:
                xp = 10
            elif xp > 5000:
                xp = 5000
            await user.add_xp(xp)
            await context.send(user.get_mention() + ', ' + lib.get_string('project:completed', user.get_guild()).format(project.get_title(), xp))

        project.set_status(status)
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:status', user.get_guild()).format(lib.get_string('project:status:'+status, user.get_guild())))

    async def run_list(self, context, opts = None):
        """
        View a list of the user's projects
        @param context:
        @param opts:
        @return:
        """
        user = User(context.message.author.id, context.guild.id, context)

        by = opts[0].lower() if opts else None
        filter = opts[1].lower() if len(opts) > 1 else None

        # If supplied, make sure the filters are valid.
        if by is not None and by not in ['status', 'genre']:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:filter:type', user.get_guild()))

        if by == 'status':
            options = self._statuses
        elif by == 'genre':
            options = self._genres

        if by is not None and filter not in options:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:filter', user.get_guild()).format(', '.join(options)))

        projects = user.get_projects(by, filter)

        # If they have no projects, then we can't display them.
        if not projects:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:noprojects', user.get_guild()))

        message = ''

        for project in projects:

            message += '**' + project.get_name() + '** (' + project.get_shortname() + ') [' + str(
                "{:,}".format(project.get_words())) + ' '+lib.get_string('words', user.get_guild()).lower()+']\n'
            message += project.get_status_emote()
            if project.get_genre() is not None:
                message += '\t' + project.get_genre_emote()
            message += '\n\n'

        filter_string = lib.get_string('project:'+by+':'+filter, user.get_guild()) if filter is not None else lib.get_string('all', user.get_guild())

        # Project lists can get very long. If it is over 2000 characters, we need to split it.
        if len(message) >= 2000:
            return await self.split_send(context, user, lib.get_string('project:list', user.get_guild()).format(filter_string) + message)
        else:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:list', user.get_guild()).format(filter_string) + message)

    async def run_view(self, context, opts):
        """
        View a specific project
        :return:
        """
        user = User(context.message.author.id, context.guild.id, context)

        # Make sure the project exists.
        if not opts:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:empty', user.get_guild()))

        shortname = opts[0].lower()
        project = user.get_project(shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(shortname))

        # Display the embedded message response for this project.
        return await project.display(context)

    async def run_update(self, context, opts):
        """
        Update a project's word count
        :param context:
        :param opts:
        :return:
        """
        user = User(context.message.author.id, context.guild.id, context)

        shortname = opts[0].lower()
        amount = opts[1] if len(opts) > 1 else None

        # Make sure the amount is valid.
        amount = lib.is_number(amount)
        if not amount:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:amount', user.get_guild()))

        # Make sure the project exists.
        project = user.get_project(shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(shortname))

        # Update the word count.
        project.update(amount)
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:updated', user.get_guild()).format(amount, project.get_name(), project.get_shortname()))

    async def run_rename(self, context, opts):
        """
        Rename a project
        :param context:
        :param opts:
        :return:
        """
        user = User(context.message.author.id, context.guild.id, context)

        original_shortname = opts[0].lower()
        new_shortname = opts[1].lower()
        new_title = " ".join(opts[2:])

        # Make sure the project exists
        project = user.get_project(original_shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(original_shortname))

        # Make sure they don't already have one with that new shortname.
        project_with_new_shortname = user.get_project(new_shortname)
        if project_with_new_shortname is not None and project_with_new_shortname.get_id() != project.get_id():
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:exists', user.get_guild()).format(new_shortname))

        # Get the original title.
        original_title = project.get_name()

        # Rename it.
        project.rename(new_shortname, new_title)
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:renamed', user.get_guild()).format(original_title, original_shortname, new_title, new_shortname))


    async def run_delete(self, context, opts):
        """
        Try to delete a project with the given shortname
        :param context:
        :param opts:
        :return:
        """
        user = User(context.message.author.id, context.guild.id, context)

        # Make sure the project exists first
        shortname = opts[0].lower()
        project = user.get_project(shortname)
        if not project:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:noexists', user.get_guild()).format(shortname))

        # Delete it.
        project.delete()
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:deleted', user.get_guild()).format(project.get_name(), project.get_shortname()))

    async def run_create(self, context, opts):
        """
        Try to create a project with the given names
        :param context:
        :param shortname:
        :param title:
        :return:
        """
        user = User(context.message.author.id, context.guild.id, context)

        # Get the shortname and title out of the argument list.
        shortname = opts[0].lower()
        title = " ".join(opts[1:]) # Every argument after the first one, joined with spaces.

        # Make sure the shortname and title are set.
        if len(shortname) == 0 or len(title) == 0:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:names', user.get_guild()))

        # Make sure that the title is less than 100 chars
        if len(title) > 100:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:length', user.get_guild()))

        # Make sure they don't already have a project with this shortname
        project = user.get_project(shortname)
        if project is not None:
            return await context.send(user.get_mention() + ', ' + lib.get_string('project:err:exists', user.get_guild()).format(shortname))

        # Create the project
        user.create_project(shortname, title)
        return await context.send(user.get_mention() + ', ' + lib.get_string('project:created', user.get_guild()).format(title, shortname))


def setup(bot):
    bot.add_cog(Project(bot))