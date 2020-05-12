import asyncio
from datetime import datetime
from enum import Enum

import uuid

from typing import Callable, Tuple, Generator, List, Dict, Awaitable, Optional

from itertools import groupby

from sqlalchemy.sql import select, insert, update, join

from . import users, message_objs, comm_nodes, entities, \
    tasks, interactions, interaction_groups, graph_nodes, \
    TaskTypes, form_data, subscriptions

class BaseMediator:
    '''
    Class designed to wrap tasks with task logging and a simple interface for
    different database operations. Mediates task tracking and DB interactions.

    Attributes:
    -----------
        errors: List[str]
            A list of errors thrown during the task
        database: Postgres
            Ref to a Postgres connection
        user_uuid: str
            String representation of the uuid associated with the person
            who ordered this job / task
        task_uuid: str
            String representation of the task's uuid
        TaskType: Enum
            Type of task being tracked
        table_refs: Dict[str, Table]
            Dictionary of str names mapped to their tables


    Methods:
    --------
        @property
        successful(self) -> bool:
            property that returns True if there are no errors and False if there are
        _async_init(self) -> None:
            Creates a new task id and logs the unfinished task in Postgres
        _gen_uuid() -> str:
            Creates a new uuid and returns its string representation
        _update_errors(self, error: Exception) -> None:
            Appends a string representation of an exception message to
            the instance's error container
        _tracked_login(self) -> None:
            Method to track tasks that don't begin with access to a user uuid.
        _finalize_task(self) -> None:
            Logs the finish time, success state, and errors from the task then updates
            the task status in Postgres
    '''
    __slots__ = ['errors', 'database', 'user_uuid',
                 'task_uuid', 'task_type', 'table_refs']

    def __init__(self,
                 database: 'Postgres',
                 user_uuid: str,
                 TaskType: TaskTypes,
                 ) -> None:

        self.errors = list()
        self.database = database
        self.user_uuid = user_uuid
        self.task_uuid = self._gen_uuid()
        self.task_type = TaskType

        # References to db tables so children can inherit
        self.table_refs = {
            'entities': entities,
            'comm_nodes': comm_nodes,
            'msg_objs': message_objs,
            'subscriptions': subscriptions,
            'graph_nodes': graph_nodes,
            'interactions': interactions,
            'interaction_groups': interaction_groups,
            'users': users,
            'tasks': tasks,
        }

    @property
    def successful(self) -> bool:
        return len(self.errors) == 0

    @staticmethod
    def _gen_uuid() -> str:
        return str(uuid.uuid4())

    def _update_errors(self, error: Exception) -> None:
        '''
        Takes a raw exception and appends the str representation of
        the Exception message to the instance's error container
        '''
        self.errors.append(str(error.message))

    async def async_init(self) -> 'Mediator':
        '''
        Asynchronously stores the initial task details in Postgres.
        Returns a Mediator copy with all attributes.
        '''

        new_task = {
            'id': self.task_uuid,
            'owner': self.user_uuid,
            'task_type': self.task_type.name,
            'time_start': datetime.now(),
            'time_finished': None,
            'error': '',
            'success': bool(False),
        }

        insert_stmt = insert(self.table_refs['tasks'], values=new_task)

        try:
            await self.database.execute(insert_stmt)
        except Exception as e:
            self._update_errors(e)
            return None

        return self

    async def _finalize_task(self) -> None:
        '''Private method that logs the task, task error state,
        and task status upon completion'''
        try:
            update_tasks = self.table_refs['tasks'].update(). \
                where(self.table_refs['tasks'].c.id == self.task_uuid). \
                values(
                    time_finished=datetime.now(),
                    error=str(', '.join(self.errors)),
                    success=len(self.errors) == 0)

            await self.database.execute(update_tasks)

        except Exception as e:
            print(f'error updating task: {self.task_uuid} error: {e}')
            self._update_errors(e)
            return

        return
