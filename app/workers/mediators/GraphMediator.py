import datetime

from typing import Generator, List, Tuple
from sqlalchemy.sql import select, insert, join

from itertools import groupby

from app.db import TaskTypes

from . import BaseMediator
from . import entities, comm_nodes, graph_nodes, interactions


class GraphMediator(BaseMediator):
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

    async def loadGraphClusters(self,
                                startDate: datetime,
                                endDate: datetime
                                ) -> Generator[List['Record'], None, None]:
        '''
        Method to query Postgres for entity and comm node data filtered by date

        Params:
        -------
            startDate: datetime
                A datetime object to filter the data by
            endDate: datetime
                End date for query

        Returns:
        --------
            A generator function that yields lists of Postgres
            records grouped by Row message id
        '''

        query = '''
            SELECT
                entities.msg_id,
                entities.email,
                entities.name,
                entities.domain,
                entities.poc,
                comm_nodes.date,
                comm_nodes.keywords,
                comm_nodes.labels,
                comm_nodes.text_body,
                comm_nodes.html_body
            FROM
                entities

            LEFT JOIN comm_nodes ON entities.msg_id = comm_nodes.message_id

            WHERE comm_nodes.date 	BETWEEN :startDate
                                    AND :endDate


            ORDER BY entities.msg_id;
        '''

        rows = await self.database.fetch_all(query=query,
                                             values={'startDate': startDate,
                                                     'endDate': endDate})

        # Generator that yields comm_node / entity grouped by msg_id
        grouped_gen = (list(g) for k, g in groupby(rows, lambda x: x['msg_id']))

        await self._finalize_task()

        # Returns the cluster generator to build the user nodes in the graph worker
        return grouped_gen, self.user_uuid
