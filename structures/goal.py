import lib, pytz, time
from structures.db import Database
from structures.user import User

class Goal:

    def __init__(self):
        self.__db = Database.instance()
        pass

    async def task_reset(self, bot):
        """
        The scheduled task to reset user goals at midnight
        :param bot:
        :return:
        """
        # Find all the user_goal records which are due a reset
        now = int(time.time())

        records = self.__db.get_all_sql('SELECT * FROM user_goals WHERE reset <= %s', [now])
        for record in records:

            # Calculate the next reset time for the goal, depending on its type.
            user = User(record['user'], 0)
            try:
                user.reset_goal(record)
            except pytz.exceptions.UnknownTimeZoneError:
                lib.out('[ERROR] Invalid timezone (' + user.get_setting('timezone') + ') for user ' + str(record['user']))

        return True

