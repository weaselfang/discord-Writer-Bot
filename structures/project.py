from typing import Optional, Dict, List
from discord import Color, Embed
from discord_slash.context import InteractionContext
import time
import lib
from structures.db import Database


class Project:
    @classmethod
    def get(cls, user: int, shortname: str) -> Optional['Project']:
        """Try to get a project with a given shortname, for a given user"""
        record = Database.instance().get('projects', {'user': user, 'shortname': shortname})
        if record is None:
            return None
        return Project(record['id'])

    @classmethod
    def all(cls, user: int) -> List['Project']:
        """Get all projects for a user"""
        records = Database.instance().get_all(
            table='projects',
            where={'user': user},
            fields=['id'],
            sort=['name', 'shortname', 'words']
        )

        projects = []
        for record in records:
            projects.append(Project(record['id']))

        return projects

    @classmethod
    def create(cls, user: int, shortname: str, name: str):
        """Create a new project"""
        Database.instance().insert('projects', {'user': user, 'shortname': shortname, 'name': name})

    def __init__(self, project_id):
        self.__db = Database.instance()

        record = self.__db.get('projects', {'id': project_id})
        if record:
            self._id = record['id']
            self._user = record['user']
            self._name = record['name']
            self._shortname = record['shortname']
            self._words = record['words']
            self._status = record['status']
            self._genre = record['genre']
            self._description = record['description']
            self._link = record['link']
            self._image = record['image']
            self._completed = record['completed']

    def get_id(self):
        return self._id

    @property
    def shortname(self) -> str:
        return self._shortname

    @property
    def name(self) -> str:
        return self._name

    def rename(self, shortname: str, name: str):
        """
        Rename a project
        :param str shortname: new shortname
        :param str name: new title
        """
        self._shortname = shortname
        self._name = name
        self.__db.update('projects', {'shortname': shortname, 'name': name}, {'id': self._id})

    @property
    def words(self) -> int:
        return self._words

    @words.setter
    def words(self, amount: int):
        """Update the word count of the project"""
        self._words = amount
        self.__db.update('projects', {'words': amount}, {'id': self._id})

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, description: str):
        """
        Set the project's description.
        @param description:
        @return:
        """
        self.__db.update('projects', {'description': description}, {'id': self._id})

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, status: str):
        """
        Set the project's status.
        @param status:
        @return:
        """
        params = {'status': status}

        # If we are marking it as finished/published and it's not been marked as completed before,
        # add xp.
        if (status == 'finished' or status == 'published') and not self.is_complete():
            # Mark the project as completed.
            params['completed'] = int(time.time())

        self.__db.update('projects', params, {'id': self._id})

    # status : emote
    STATUS_EMOTES: Dict[str, str] = {
        'planning': ':thinking:',
        'progress': ':writing_hand:',
        'editing': ':pencil:',
        'published': ':notebook_with_decorative_cover:',
        'finished': ':white_check_mark:',
        'abandoned': ':wastebasket:',
        'submitted': ':postbox:',
        'rejected': ':x:',
        'hiatus': ':clock4:',
        'rewriting': ':repeat:',
        'accepted': ':ballot_box_with_check:'
    }

    @property
    def status_emote(self) -> str:
        """
        Given the project's status, get the corresponding emote to display
        @return: the emote key (including the delimiting `:`) or an empty string.
        """
        emote: Optional[str] = self.STATUS_EMOTES.get(self._status)
        if emote is not None:
            return emote
        else:
            return ''

    @property
    def genre(self) -> str:
        return self._genre

    @genre.setter
    def genre(self, genre: str):
        """
        Set the project's genre.
        @param genre:
        @return:
        """
        self.__db.update('projects', {'genre': genre}, {'id': self._id})

    # genre : emote
    GENRE_EMOTES = {
        'fantasy': ':man_mage:',
        'scifi': ':ringed_planet:',
        'romance': ':heart:',
        'horror': ':skull:',
        'fiction': ':blue_book:',
        'nonfiction': ':bookmark:',
        'short': ':shorts:',
        'mystery': ':detective:',
        'thriller': ':scream:',
        'crime': ':oncoming_police_car:',
        'erotic': ':hot_pepper:',
        'comic': ':art:',
        'action': ':gun:',
        'drama': ':performing_arts:',
        'fanfic': ':art:',
        'sfw': ':green_circle:',
        'nsfw': ':red_circle:',
        'seminsfw': ':orange_circle:',
        'literary': ':notebook_with_decorative_cover:',
        'adventure': ':mountain_snow:',
        'suspense': ':worried:',
        'ya': ':adult:',
        'kids': ':children_crossing:',
        'academic': ':books:',
        'challenge': ':mountain:',
    }

    @property
    def genre_emote(self) -> str:
        """
        Given the project's genre, get the corresponding emote to display
        @return: the emote key (including the delimiting `:`) or an empty string.
        """
        emote: Optional[str] = self.GENRE_EMOTES.get(self._status)
        if emote is not None:
            return emote
        else:
            return ''

    @property
    def image(self) -> Optional[str]:
        """
        The project's image URL
        """
        return self._image if self._image != '' else None

    @image.setter
    def image(self, img: str):
        """Set the project's image link."""
        self.__db.update('projects', {'image': img}, {'id': self._id})

    @property
    def link(self) -> Optional[str]:
        """The hyperlink for your project's web/store page"""
        return self._link if self._link != '' else None

    @link.setter
    def link(self, link: str):
        """Sets the hyperlink for your project's web/store page"""
        self.__db.update('projects', {'link': link}, {'id': self._id})

    def delete(self):
        """Delete the project"""
        return self.__db.delete('projects', {'id': self._id})

    def abbrev(self, context: InteractionContext) -> str:
        return (
            f'{self.status_emote} **{self.name}** ({self.shortname}) ['
            + "{:,}".format(self.words) + ' ' + lib.get_string('words', context.guild_id).lower()
            + ']' + self.genre_emote
        )

    def embed(self, context: InteractionContext) -> Embed:
        """Create an embed displaying this project"""
        words = str("{:,}".format(self.words))

        desc = self.description
        if desc is None:
            desc = lib.get_string('project:nodesc', context.guild_id)

        embed: Embed
        if self.link is not None:
            embed = Embed(
                title=self.name,
                color=Color.green(),
                description=desc,
                url=self.link
            )
        else:
            embed = Embed(
                title=self.name,
                color=Color.green(),
                description=desc
            )

        if self.image is not None:
            embed.set_thumbnail(url=self.image)

        embed.add_field(
            name=lib.get_string('status', context.guild_id),
            value=(
                self.status_emote + ' '
                + lib.get_string(f'project:status:{self.status}', context.guild_id)
            ),
            inline=True
        )

        if self.genre is not None:
            embed.add_field(
                name=lib.get_string('genre', context.guild_id),
                value=(
                    self.genre_emote + ' '
                    + lib.get_string(f'project:genre:{self.genre}', context.guild_id)
                ),
                inline=True
            )

        embed.add_field(
            name=lib.get_string('wordcount', context.guild_id),
            value=words,
            inline=True
        )

        return embed

    def is_complete(self) -> bool:
        return self._completed > 0
