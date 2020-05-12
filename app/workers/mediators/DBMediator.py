import datetime

from typing import Generator, List, Tuple, Dict
from sqlalchemy.sql import select
from sqlalchemy.dialects.postgresql import insert

from app.db import TaskTypes

from . import BaseMediator



class DBMediator(BaseMediator):
    '''
    Mediator to track and chain graph related tasks

    Methods:
    --------
        loadGraphClusters(self, startDate: datetime, endDate: datetime)
            returns a generator that yields groups of entities clustered by msg_id

    '''

    def __init__(self,
                 database: 'Postgres',
                 user_uuid: str,
                 TaskType: TaskTypes
                 ) -> None:

        super().__init__(database, user_uuid, TaskType)

    async def handleConflicts(self,
                              table_name: str,
                              input_gen: Tuple[str, Generator[Dict[str, any], None, None]]
                              ) -> None:
        '''
        Function to sequentially add rows to Postgres and pass on any rows raise a conflict

        Params:
        ----------
            table_name:str
                string name of the table to target
            input_gen: Tuple[str, Generator[Dict[str, any], None, None]]
                Generator that yields rows of data for a specific table
        '''

        while True:
            try:
                row = next(input_gen)

                stmt = insert(
                    self.table_refs[table_name]
                ).values(**row).on_conflict_do_nothing(
                    index_elements=['email']
                )

                await self.database.execute(stmt)
            except StopIteration:
                break

            except Exception as e:
                print(f'Error saving {table_name} to DB: {e}')
                self._update_errors(e)
                break

            print(f'successfully saved {table_name} to DB')

        return


    async def handleDbInserts(self,
                              input_generators: List[Tuple[str, Generator[Dict[str, any], None, None]]],
                              log_task: bool = True,
                              *args,
                              **kwargs
                              ) -> None:
        '''
        Function that allows for sequential Postgres Table inserts using Generators

        Params:
        --------
        input_generators: List[Tuple[str, Generator[Dict[str, any]]]]
            Takes a list of tuples where the first element is a Table str name and
            The second element is a row Generator to feed Postgres insert data

        '''

        for gen in input_generators:
            if gen[0] == 'graph_nodes':
                await self.handleConflicts(gen[0], gen[1])

            try:
                await self.database.execute_many(
                    query=self.table_refs[gen[0]].insert(),
                    values=gen[1]
                )
                print(f'successfully saved {gen[0]} to DB')

            except Exception as e:
                print(f'Error saving {gen[0]} to DB: {e}')
                self._update_errors(e)
                continue

        if log_task:
            await self._finalize_task()

        return

    async def insertRow(self,
                        table_name: str,
                        row: Dict[str, any],
                        *args,
                        **kwargs
                        ) -> None:

        stmt = insert(
            self.table_refs[table_name]
        ).values(**row)

        try:
            await self.database.execute(stmt)
        except Exception as e:
            print(f'Error saving {table_name} to DB: {e}')
            self._update_errors(e)

        print(f'successfully saved {table_name} to DB')

        return
