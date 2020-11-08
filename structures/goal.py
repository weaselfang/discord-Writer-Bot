import lib, time
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
            next = user.calculate_user_reset_time(record['type'])

            lib.debug('Setting next ' + record['type'] + ' goal reset time for ' + str(record['user']) + ' to: ' + str(next))
            self.__db.update('user_goals', {'completed': 0, 'current': 0, 'reset': next}, {'id': record['id']})

        return True

