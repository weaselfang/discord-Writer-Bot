import time
from datetime import datetime
from typing import Optional

from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext, ComponentContext, InteractionContext
from discord_slash.model import ComponentType, SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow

import lib
from structures.guild import Guild
from structures.project import Project
from structures.sprint import Sprint
from structures.task import Task
from structures.user import User

PROJECT_SELECTOR_ID = 'sprint_select_project'

class SprintCommand(commands.Cog):
    DEFAULT_LENGTH = 20  # 20 minutes
    DEFAULT_DELAY = 2  # 2 minutes
    MAX_LENGTH = 60  # 1 hour
    MAX_DELAY = 60 * 24  # 24 hours
    WPM_CHECK = 150  # If WPM exceeds this amount, check that the user meant to submit that many words

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(
        base="sprint",
        name="for",
        description="Start a sprint",
        options=[
            create_option(
                name="length",
                description="length",
                option_type=SlashCommandOptionType.INTEGER,
                required=True
            ),
            create_option(
                name="in",
                description="start the sprint in x time from now. NOTE: `in` and `at` are "
                            "mutually exclusive!",
                option_type=SlashCommandOptionType.INTEGER,
                required=False
            ),
            create_option(
                name="at",
                description="start the sprint at a given time past the hour. NOTE: `in` and `at` "
                            "are mutually exclusive!",
                option_type=SlashCommandOptionType.INTEGER,
                required=False
            )
        ],
        # `in` is a reserved identifier in Python
        connector={'in': 'start'}
    )
    async def sprint_for(self, context: SlashContext, length: int, start: int = None,
                         at: int = None):
        """
        Try to start a sprint on the server.

        :param SlashContext context: Context in which this command was called.
        :param int length: Length of time (in minutes) the sprint should last.
        :param int start: Time in minutes from now, that the sprint should start.
        :param int at: Time in minutes past the hour, that the sprint should start.
        """
        # in case that the command takes a lot of time
        await context.defer()

        if not Guild(context.guild).is_command_enabled('sprint'):
            return await context.reply(
                lib.get_string('err:disabled', context.guild_id),
                hidden=True
            )

        user = User(context.author_id, context.guild_id, context)
        sprint = Sprint(context.guild_id)

        # Check if sprint is finished but not marked as completed, in which case we can mark it as complete
        if sprint.is_finished() and sprint.is_declaration_finished():
            # Mark the sprint as complete
            await sprint.complete()
            # Reload the sprint object, as now there shouldn't be a pending one
            sprint = Sprint(context.guild_id)

        # If a sprint is currently running, we cannot start a new one
        if sprint.exists():
            return await context.send(context.author.mention + ', ' + lib.get_string('sprint:err:alreadyexists', context.guild_id))

        # Check sprint length
        # If the length argument is not valid, use the default
        if 0 > length or self.MAX_LENGTH < length:
            length = self.DEFAULT_LENGTH

        # Figure out when sprint starts
        delay: int = 0

        # Make sure that the user didn't enter both `at` and `in`
        if start is not None and at is not None:
            return context.send(context.author.mention + ', ' + lib.get_string('sprint:err:for:exclusive', context.guild_id))

        # ensure that delay is in valid range
        if start is not None:
            if start < 0 or start > self.MAX_DELAY:
                delay = self.DEFAULT_DELAY
            else:
                delay = start

        if at is not None:
            # Make sure the user has set their timezone, otherwise we can't calculate it.
            timezone = user.get_setting('timezone')
            user_timezone = lib.get_timezone(timezone)
            if not user_timezone:
                return await context.send(context.author.mention + ', ' + lib.get_string('err:notimezone', context.guild_id))

            if 0 > at or at > 60:
                return await context.send(context.author.mention + ', ' + lib.get_string('sprint:err:for:at', context.guild_id))

            # Now using their timezone and the minute they requested, calculate when that should be.
            delay = (60 + at - datetime.now(user_timezone).minute) % 60

        # Calculate the start and end times based on the current timestamp
        now = int(time.time())
        start_time = now + (delay * 60)
        end_time = start_time + (length * 60)

        # Create the sprint
        sprint = Sprint.create(
            guild=context.guild_id,
            channel=context.channel.id,
            start=start_time,
            end=end_time,
            end_reference=end_time,
            length=length,
            createdby=context.author_id,
            created=now
        )

        # Join the sprint
        sprint.join(context.author_id)

        # Increment the user's stat for sprints created
        user.add_stat('sprints_started', 1)

        # Are we starting immediately or after a delay?
        if delay == 0:
            # Immediately. That means we need to schedule the end task.
            Task.schedule(sprint.TASKS['end'], end_time, 'sprint', sprint.get_id())
            return await sprint.post_start(context)
        else:
            # Delay. That means we need to schedule the start task, which will in turn schedule the end task once it's run.
            Task.schedule(sprint.TASKS['start'], start_time, 'sprint', sprint.get_id())
            return await sprint.post_delayed_start(context)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="join",
        description="Join sprint",
        options=[
            create_option(
                name="initial",
                option_type=SlashCommandOptionType.INTEGER,
                required=True,
                description="Initial word count"
            ),
            create_option(
                name="project",
                option_type=SlashCommandOptionType.STRING,
                required=False,
                description="Project to sprint in"
            )
        ],
        connector={'project': 'shortname'}
    )
    async def sprint_join(self, context: SlashContext, initial: int, shortname: str = None):
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        if sprint.is_user_sprinting(context.author_id):

            # Update the sprint_users record. We set their current_wc to the same as starting_wc here, otherwise if they join with, say 50 and their current remains 0
            # then if they run a status, or in the ending calculations, it will say they wrote -50.
            sprint.update_user(context.author_id, start=initial, current=initial, sprint_type=None)
            # Send message back to channel letting them know their starting word count was updated
            await context.send(context.author.mention + ', ' + lib.get_string('sprint:join:update', context.guild_id).format(initial))

        else:
            # Join the sprint
            sprint.join(context.author_id, starting_wc=initial, sprint_type=None)

            # Send message back to channel letting them know their starting word count was updated
            await context.send(context.author.mention + ', ' + lib.get_string('sprint:join', context.guild_id).format(initial))

        # If they are sprinting in a project, send that message as well.
        if shortname is not None:
            await self._set_project(context, shortname)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="join-no-wc",
        description="Join a sprint without counting words",
        options=[
            create_option(
                name="project",
                option_type=SlashCommandOptionType.STRING,
                required=False,
                description="Project to sprint in"
            )
        ],
        connector={'project': 'shortname'}
    )
    async def sprint_join_no_wc(self, context: SlashContext, shortname: str = None):
        """
        Join a sprint without counting words

        :param SlashContext context: context this command was invoked in.
        :param str shortname: Project shortname
        """
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        if sprint.is_user_sprinting(context.author_id):
            sprint.update_user(context.author_id, start=0, current=0, sprint_type=Sprint.SPRINT_TYPE_NO_WORDCOUNT)
        else:
            sprint.join(context.author_id, starting_wc=0, sprint_type=Sprint.SPRINT_TYPE_NO_WORDCOUNT)

        await context.send(
            context.author.mention + ', ' + lib.get_string('sprint:join:update:no_wordcount', context.guild_id))

        # If they are sprinting in a project, send that message as well.
        if shortname is not None:
            await self._set_project(context, shortname)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="join-same",
        description="Join a sprint from where you left off last sprint"
    )
    async def sprint_join_same(self, context: SlashContext):
        """
        Join this sprint with the same project as last sprint and with the ending wc.

        :param SlashContext context: context this command was invoked in.
        """
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        # Okay, check for their most recent sprint record
        most_recent = user.get_most_recent_sprint(sprint)
        if most_recent is None:
            return await self.sprint_join.func(context, 0)

        starting_wc = most_recent['ending_wc']
        project_id = most_recent['project']
        sprint_type = most_recent['sprint_type']

        if sprint_type == Sprint.SPRINT_TYPE_NO_WORDCOUNT:
            return await self.sprint_join_no_wc.func(self=self, context=context)

        await self.sprint_join.func(self=self, context=context, initial=starting_wc)
        return await self._set_project(context, project_id=project_id)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="wc",
        description="Declare total word count",
        options=[
            create_option(
                name="amount",
                description="How many words do you have written at the end of this sprint? (including initial wc)",
                option_type=SlashCommandOptionType.INTEGER,
                required=True)
        ]
    )
    async def sprint_wc(self, context: SlashContext, amount: int):
        """
        Declare user's current word count for the sprint
        :param SlashContext context: context this command was invoked in.
        :param int amount: how many words the user has
        """
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        # If the user is not sprinting, then again, just display that error
        if not await self._check_is_in_sprint(context, sprint):
            return

        # If the sprint hasn't started yet, display error
        if not sprint.has_started():
            return await context.send(
                context.author.mention + ', ' +
                lib.get_string('sprint:err:notstarted', context.guild_id))

        # Get the user's sprint info
        user_sprint = sprint.get_user_sprint(context.author_id)

        # If they joined without a word count, they can't add one.
        if user_sprint['sprint_type'] == Sprint.SPRINT_TYPE_NO_WORDCOUNT:
            return await context.send(
                context.author.mention + ', ' +
                lib.get_string('sprint:err:nonwordcount', context.guild_id))

        # If the declared value is less than they started with, then that is an error.
        if amount < int(user_sprint['starting_wc']):
            diff = user_sprint['current_wc'] - amount
            return await context.send(
                context.author.mention + ', ' +
                lib.get_string('sprint:err:wclessthanstart', context.guild_id)
                .format(amount, user_sprint['starting_wc'], diff))

        return await self._increment_words(context, sprint, user, amount)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="wrote",
        description="Declare words written this sprint",
        options=[
            create_option(
                name="amount",
                description="How many words did you write *in this sprint*? (not including your starting wc)",
                option_type=SlashCommandOptionType.INTEGER,
                required=True)
        ]
    )
    async def sprint_wrote(self, context: SlashContext, amount: int):
        """
        Declare how many words you wrote this sprint (ie a calculation)

        :param SlashContext context: context this command was invoked in.
        :param int amount: how many words you wrote.
        """
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        # If the user is not sprinting, then again, just display that error
        # If the sprint hasn't started yet, display error
        if not (await
                self._check_is_in_sprint(context, sprint) and await
                self._check_sprint_started(context, sprint)):
            return

        # Get the user's sprint info
        user_sprint = sprint.get_user_sprint(context.author_id)

        # If they joined without a word count, they can't add one.
        if user_sprint['sprint_type'] == Sprint.SPRINT_TYPE_NO_WORDCOUNT:
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:err:nonwordcount', context.guild_id))

        # Add that to the current word count, to get the new value
        new_amount: int = int(user_sprint['current_wc']) + amount

        return await self._increment_words(context, sprint, user, new_amount)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="cancel",
        description="Cancel a sprint"
    )
    async def sprint_cancel(self, context: SlashContext):
        """
        Cancel a running sprint on the server
        :param SlashContext context: context this command was invoked in.
        """
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        # If they do not have permission to cancel this sprint, display an error
        if int(sprint.get_createdby()) != context.author_id and context.author.permissions_in(
                context.channel).manage_messages is not True:
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:err:cannotcancel', context.guild_id))

        # Get the users sprinting and create an array of mentions
        users = sprint.get_users()
        notify = sprint.get_notifications(users)

        # Cancel the sprint
        sprint.cancel(context)

        # Display the cancellation message
        message = lib.get_string('sprint:cancelled', context.guild_id)
        message = message + ', '.join(notify)
        return await context.send(message)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="end",
        description="End a sprint"
    )
    async def sprint_end(self, context: SlashContext):
        """
        Manually force the sprint to end (if the cron hasn't posted the message) and ask for final word counts
        :param SlashContext context: context this command was invoked in.
        """
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        # If they do not have permission to cancel this sprint, display an error
        if int(sprint.get_createdby()) != context.author_id and context.author.permissions_in(
                context.channel).manage_messages is not True:
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:err:cannotend', context.guild_id))

        # If the sprint hasn't started yet, it can't be ended.
        if not await self._check_sprint_started(context, sprint):
            return

        # Change the end reference to now, otherwise wpm calculations will be off, as it will use the time in the future when it was supposed to end.
        sprint.update_end_reference(int(time.time()))

        # Since we are forcing the end, we should cancel any pending tasks for this sprint
        Task.cancel('sprint', sprint.get_id())

        # We need to set the bot into the sprint object, as we will need it when trying to get the guild object
        sprint.set_bot(self.bot)
        return await sprint.end(context)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="leave",
        description="Leave a sprint"
    )
    async def sprint_leave(self, context: SlashContext):
        """
        Leave the sprint
        :param SlashContext context: context this command was invoked in.
        """
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        # Remove the user from the sprint
        sprint.leave(context.author_id)

        await context.send(
            context.author.mention + ', ' + lib.get_string('sprint:leave', context.guild_id))

        # If there are now no users left, cancel the whole sprint
        if len(sprint.get_users()) == 0:
            # Cancel the sprint
            sprint.cancel(context)

            # Decrement sprints_started stat for whoever started this one
            creator = User(sprint.get_createdby(), sprint.get_guild())
            creator.add_stat('sprints_started', -1)

            # Display a message letting users know
            return await context.send(lib.get_string('sprint:leave:cancelled', context.guild_id))

    @cog_ext.cog_subcommand(
        base="sprint",
        name="time",
        description="Get how long is left in the sprint"
    )
    async def sprint_time(self, context: SlashContext):
        """
        Get how long is left in the sprint
        :param SlashContext context: context this command was invoked in.
        """
        # in case that the command takes a lot of time
        await context.defer()

        if not Guild(context.guild).is_command_enabled('sprint'):
            return await context.reply(
                lib.get_string('err:disabled', context.guild_id),
                hidden=True
            )

        sprint = Sprint(context.guild_id)

        # If there is no active sprint, then just display an error
        if not sprint.exists():
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:err:noexists', context.guild_id))

        now = int(time.time())

        # If the sprint has not yet started, display the time until it starts
        if not sprint.has_started():
            left = lib.secs_to_mins(sprint.get_start() - now)
            return await context.send(
                context.author.mention + ', ' +
                lib.get_string('sprint:startsin', context.guild_id).format(left['m'], left['s']))

        # If it's currently still running, display how long is left
        elif not sprint.is_finished():
            left = lib.secs_to_mins(sprint.get_end() - now)
            return await context.send(
                context.author.mention + ', ' +
                lib.get_string('sprint:timeleft', context.guild_id).format(left['m'], left['s']))

        # If it's finished but not yet marked as completed, we must be waiting for word counts
        elif sprint.is_finished():
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:waitingforwc', context.guild_id))

    @cog_ext.cog_subcommand(
        base="sprint",
        name="status",
        description="Get your status in the current sprint"
    )
    async def sprint_status(self, context: SlashContext):
        """
        Get the user's status in this sprint
        :param SlashContext context: context this command was invoked in.
        """
        user: User
        sprint: Sprint
        err: bool
        user, sprint, err = await SprintCommand._common_init(context)
        if err:
            return

        # If the user is not sprinting, then again, just display that error
        if not sprint.is_user_sprinting(context.author_id):
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:err:notjoined', context.guild_id))

        # If the sprint hasn't started yet, display error
        if not await self._check_sprint_started(context, sprint):
            return

        # If they are sprinting, then display their current status.
        user_sprint = sprint.get_user_sprint(context.author_id)

        # Build the variables to be passed into the status string
        now = int(time.time())
        current = user_sprint['current_wc']
        written = current - user_sprint['starting_wc']
        seconds = now - user_sprint['timejoined']
        elapsed = round(seconds / 60, 1)
        wpm = Sprint.calculate_wpm(written, seconds)
        left = round((sprint.get_end() - now) / 60, 1)

        return await context.send(
            context.author.mention + ', ' +
            lib.get_string('sprint:status', context.guild_id)
            .format(current, written, elapsed, wpm, left)
        )

    @cog_ext.cog_subcommand(
        base="sprint",
        name="pb",
        description="Get the user's personal best for sprinting"
    )
    async def sprint_pb(self, context: SlashContext):
        """
        Get the user's personal best for sprinting
        :param SlashContext context: context this command was invoked in.
        :return:
        """
        # in case that the command takes a lot of time
        await context.defer()

        if not Guild(context.guild).is_command_enabled('sprint'):
            return await context.reply(
                lib.get_string('err:disabled', context.guild_id),
                hidden=True
            )

        user = User(context.author_id, context.guild_id, context)
        record = user.get_record('wpm')

        if record is None:
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:pb:none', context.guild_id))
        else:
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:pb', context.guild_id).format(int(record)))

    @cog_ext.cog_subcommand(
        base="sprint",
        name="notify",
        description="Set whether you will be notified of upcoming sprints on this server",
        options=[
            create_option(
                name="notify",
                description="Whether or not to notify",
                option_type=SlashCommandOptionType.INTEGER,
                required=True,
                choices=[
                    create_choice(
                        name="Notify",
                        value=1
                    ),
                    create_choice(
                        name="Do not notify",
                        value=0
                    )
                ]
            )
        ]
    )
    async def sprint_notify(self, context: SlashContext, notify: int):
        """
        Set a user to be notified of upcoming sprints on this server.
        :param SlashContext context: context this command was invoked in.
        """
        # in case that the command takes a lot of time
        await context.defer()

        if not Guild(context.guild).is_command_enabled('sprint'):
            return await context.reply(
                lib.get_string('err:disabled', context.guild_id),
                hidden=True
            )

        user = User(context.author_id, context.guild_id, context)
        user.set_guild_setting('sprint_notify', str(notify))
        message = context.author.mention + ', '
        if notify == 1:
            message += lib.get_string('sprint:notified', context.guild_id)
        else:
            message += lib.get_string('sprint:forgot', context.guild_id)
        return await context.send(message)

    @cog_ext.cog_subcommand(
        base="sprint",
        name="purge",
        description="Purge any users who asked for notifications but aren't in the server any more."
    )
    async def sprint_purge(self, context: SlashContext):
        """
        Purge any users who asked for notifications but aren't on the server anymore.
        :param SlashContext context: context this command was invoked in.
        """
        # in case that commands take a long time
        await context.defer(hidden=True)

        if not Guild(context.guild).is_command_enabled('sprint'):
            return await context.reply(
                lib.get_string('err:disabled', context.guild_id),
                hidden=True
            )

        if context.channel.permissions_for(context.author).manage_messages is not True:
            return await context.send(context.author.mention + ', ' +
                                      lib.get_string('sprint:err:purgeperms', context.guild_id))
        purged = await Sprint.purge_notifications(context)
        if purged > 0:
            return await context.send(
                lib.get_string('sprint:purged', context.guild_id).format(purged))
        else:
            return await context.send(lib.get_string('sprint:purged:none', context.guild_id))

    @cog_ext.cog_component(
        components=PROJECT_SELECTOR_ID,
        component_type=ComponentType.select
    )
    async def component_set_project(self, context: ComponentContext):
        # in case that the command takes a lot of time
        await context.defer()

        return await self._set_project(context, shortname=context.selected_options[0])

    @classmethod
    async def _set_project(cls, context: InteractionContext, shortname: str = None,
                           project_id: int = None):
        """
        Internal utility function: Set the project the user wants to sprint in.
        :param SlashContext context: context this command was invoked in.
        """
        user = User(context.author_id, context.guild_id, context)
        sprint = Sprint(context.guild_id)

        project: Optional[Project]

        # If there is no active sprint, then just display an error
        if not sprint.exists():
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:err:noexists', context.guild_id))

        # If the user is not sprinting, then again, just display that error
        if not sprint.is_user_sprinting(context.author_id):
            return await context.send(
                context.author.mention + ', ' + lib.get_string('sprint:err:notjoined', context.guild_id))

        if project_id is None:
            # Did we supply the project by name?
            if shortname is None:
                return
            # If a project shortname is supplied, try to set that as what the user is sprinting for.
            # Convert to lowercase for searching.
            shortname = shortname.lower()

            # Make sure the project exists.
            project = Project.get(user.get_id(), shortname)

            # If that did not yield a valid project, send an error message.
            if project is None:
                return await context.send(
                    context.author.mention + ', ' + lib.get_string('project:err:noexists', context.guild_id).format(shortname))
        else:
            project = Project(project_id)

        sprint.set_project(project.get_id(), context.author_id)
        return await context.send(
            context.author.mention + ', ' +
            lib.get_string('sprint:project', context.guild_id).format(project.name))

    @classmethod
    async def _common_init(cls, context: InteractionContext, hidden: bool = False) -> (User, Sprint, bool):
        if not Guild(context.guild).is_command_enabled('sprint'):
            return await context.reply(
                lib.get_string('err:disabled', context.guild_id),
                hidden=True
            )
        if not context.deferred:
            await context.defer(hidden=hidden)

        user = User(context.author_id, context.guild_id, context)
        sprint = Sprint(context.guild_id)

        # If there is no active sprint, then just display an error
        if not sprint.exists():
            await context.send(context.author.mention + ', ' + lib.get_string(
                'sprint:err:noexists', context.guild_id))
            return None, None, True
        else:
            return user, sprint, False

    @classmethod
    async def _increment_words(cls, context: InteractionContext, sprint: Sprint, user: User,
                               amount: int):
        user_sprint = sprint.get_user_sprint(context.author_id)

        # Is the sprint finished? If so this will be an ending_wc declaration, not a current_wc one.
        col = 'ending' if sprint.is_finished() else 'current'

        # Before we actually update it, if the WPM is huge and most likely an error, just check with them if they meant to put that many words.
        written = amount - int(user_sprint['starting_wc'])
        seconds = int(sprint.get_end_reference()) - user_sprint['timejoined']
        wpm = Sprint.calculate_wpm(written, seconds)

        # Does the user have a configured setting for max wpm to check?
        max_wpm = user.get_setting('maxwpm')
        if not max_wpm:
            max_wpm = cls.WPM_CHECK

        if wpm > int(max_wpm):
            return await context.send(
                context.author.mention + ', ' +
                lib.get_string('sprint:wpm:redeclare', context.guild_id).format(written, wpm),
                hidden=True
            )

        # Update the user's sprint record
        arg = {col: amount}
        sprint.update_user(context.author_id, **arg)

        # Reload the user sprint info
        user_sprint = sprint.get_user_sprint(context.author_id)

        # Which value are we displaying?
        wordcount = user_sprint['ending_wc'] if sprint.is_finished() else user_sprint['current_wc']
        written = int(wordcount) - int(user_sprint['starting_wc'])

        await context.send(
            context.author.mention + ', ' + lib.get_string('sprint:declared', context.guild_id).format(
                wordcount, written))

        # Is the sprint now over and has everyone declared?
        if sprint.is_finished() and sprint.is_declaration_finished():
            Task.cancel('sprint', sprint.get_id())
            await sprint.complete(context)

    @classmethod
    async def _check_sprint_started(cls, context: InteractionContext, sprint: Sprint) -> bool:
        """
        Check that the sprint started
        :param SlashContext context: context this command was invoked in.
        :param Sprint sprint: the sprint on this server.
        :return: True if sprint has started
        """
        if sprint.has_started():
            return True

        await context.send(context.author.mention + ', ' + lib.get_string('sprint:err:notstarted', context.guild_id))
        return False

    @classmethod
    async def _check_is_in_sprint(cls, context: InteractionContext, sprint: Sprint) -> bool:
        if sprint.is_user_sprinting(context.author_id):
            return True

        await context.send(
            context.author.mention + ', ' + lib.get_string('sprint:err:notjoined', context.guild_id))
        return False

    @commands.command(name="sprint", aliases=['spring'])
    @commands.guild_only()
    async def old(self, context):
        """
        Write with your friends and see who can write the most in the time limit!
        When choosing a length and start delay, there are maximums of 60 minutes length of sprint, and 24 hours delay until sprint begins.
        NOTE: The bot checks for sprint changes every 30 seconds, so your start/end times might be off by +-30 seconds or so.

        Run `help sprint` for more extra information, including any custom server settings related to sprints.

        Examples:
            `sprint start` - Quickstart a sprint with the default settings.
            `sprint for 20 in 3` - Schedules a sprint for 20 minutes, to start in 3 minutes.
            `sprint cancel` - Cancels the current sprint. This can only be done by the person who created the sprint, or any users with the MANAGE_MESSAGES permission.
            `sprint join` - Joins the current sprint.
            `sprint join 100` - Joins the current sprint, with a starting word count of 100.
            `sprint join 100 sword` - Joins the current sprint, with a starting word count of 100 and sets your sprint to count towards your Project with the shortname "sword" (See: Projects for more info).
            `sprint join same` - Use the keyword `same` to join the sprint using the same Project and Final Word Count from your most recent sprint.
            `sprint leave` - Leaves the current sprint.
            `sprint project sword` - Sets your sprint to count towards your Project with the shortname "sword" (See: Projects for more info).
            `sprint wc 250` - Declares your final word count at 250.
            `sprint time` - Displays the time left in the current sprint.
            `sprint pb` - Displays your personal best wpm from sprints on this server. Run sprint pb reset to reset your personal best to 0 on the current server.
            `sprint notify` - You will be notified when someone starts a new sprint.
            `sprint forget` - You will no longer be notified when someone starts a new sprint.
            `sprint status` - Shows you your current word count on the sprint.

        **Sprint Tips**
        If you join the sprint with a starting word count, remember to declare your total word count at the end, not just the amount of words you wrote in the sprint.
        e.g. If you joined with 1000 words, and during the sprint you wrote another 500 words, the final word count you should declare would be 1500
        """
        return await context.send(lib.get_string('err:slash', context.guild.id))

def setup(bot):
    bot.add_cog(SprintCommand(bot))
