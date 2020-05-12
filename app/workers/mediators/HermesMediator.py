from sanic import Sanic
import jwt
import os
import uuid
import asyncio

from functools import partial
from threading import Lock

from typing import Dict, Callable, Awaitable, Tuple, Generator, List

from app.wrappers import Pipeline, Gmail
from app.db import TaskTypes
from . import BaseMediator
from . import users


class HermesMediator(BaseMediator):
    '''
    Mediator to track and chain from Hermes scraping pipeline

    Methods:
    --------
    fetched_messages
        Property that returns the number of fetched messages

    _get_last_message
        Fetches the last message scraped for a specific user

    _chunk_message_bundles(chunk_size: int, query_limit: int)
        Fetches all message ids for a specific user that are not
        already stored in the db. Will only fetch message ids up
        to the specified limit.

    _enqueue_chunks(chunk_gen: Generator[List[str], None, None],
                    window_size: int,
                    max_workers: int
                    )
        Takes a chunk generator and sends it to be
        processed in a parallel task queue. The window size
        corresponds to the bundle size for batch Gmail http
        requests and max_workers corresponds to the maximum
        number of parallel worker threads

    tracking_callback(task_details: Tuple[str, int])
        Thread safe callback for parallel processing threads
        to keep track of their progress and status

    wrap_pipeline(chunk_size: int,
                  query_limit: int,
                  window_size: int,
                  max_workers: int
                  )
        Main interface for chunking and parallelizing the gmail scrape

    log_after_complete
        waits for the chunks to finish processing, then
        updates the Task table to reflect the success and 
        finish time of the whole Hermes pipeline



    '''

    def __init__(self,
                 app: Sanic,
                 user_uuid: str,
                 TaskType: TaskTypes,
                 interface: Pipeline
                 ) -> None:
        super().__init__(app.database, user_uuid, TaskType)
        self.app = app
        self.interface = interface
        self.chunk_count = 0
        self.total_messages = 0
        self.finished_bundles = list()  # List[Tuple[interface_id, msg_count]]
        self._lock = Lock()

    @property
    def fetched_messages(self):
        counter = 0
        for bundle in self.finished_bundles:
            counter += bundle[1]

        return counter

    async def _get_last_message(self) -> str:
        ''' Looks up and returns the most recent msg_id for a particular user '''

        query = '''SELECT message_id FROM message_objs WHERE owner = :owner ORDER BY last_fetch desc'''
        row = await self.database.fetch_one(query=query, values={"owner": self.user_uuid})

        if row is not None:
            return row['message_id']
        else:
            return

    async def _chunk_message_bundles(self,
                                     chunk_size: int,
                                     query_limit: int,
                                     ) -> Generator[List[str], None, None]:
        '''
        Chunks bundles of messages and returns a generator that
        yields lists of msg id strings.
        '''

        # Fetch most recent message
        last_message = await self._get_last_message()
        # Get a list of all message ids and the count of all message ids from Gmail
        msg_ids, msg_count = await self.interface.queryGmail(last_message, query_limit)
        self.total_messages = msg_count

        # Create a generator to bundle the message ids into chunks
        bundle_gen = self.interface._bundler(msg_ids, chunk_size)

        return bundle_gen

    async def _enqueue_chunks(self,
                              chunk_gen: Generator[List[str], None, None],
                              window_size: int,
                              max_workers: int,
                              ) -> None:


        for chunk in chunk_gen:
            # Don't queue empty lists
            if len(chunk) == 0:
                continue
            # Make an id to track progress on the different processes
            tracking_id = uuid.uuid4
            parallel_interface = self.interface._clone_interface(str(tracking_id))
            routine = partial(parallel_interface.hermes,
                              chunk,
                              window_size,
                              max_workers,
                              self.user_uuid,
                              self.tracking_callback
                              )

            await self.app.long_queue.put(routine)
            self.chunk_count += 1

    async def tracking_callback(self, task_details: Tuple[str, int]) -> None:
        '''
        Thread safe callback to update the status of different parallel processes.

        Params:
        -------
        task_details: Tuple[str, int]
            The first tuple element is the uuid associated with a sub-task
            The second tuple element is the number of fetched messages
        '''
        if self._lock.locked():
            await asyncio.sleep(3)

        else:
            try:
                self._lock.acquire()
                self.finished_bundles.append(task_details)
            except Exception as e:
                print(f'something went wrong: {e}')

            finally:
                self._lock.release()


    async def wrap_pipeline(self,
                            chunk_size: int = 1000,
                            query_limit: int = 2000,
                            window_size: int = 15,
                            max_workers: int = 4,
                            tracked: bool = False) -> None:
        '''
        Task wrapper for chunked pipeline execution

        Params:
        -------
        chunk_size: int = 1000
            Number of message ids in chunk to bundle and fetch from Gmail API
        query_limit: int = 2000
            Max number of message ids to gather and query
        window_size: int = 15
            Size of bundle to fetch from Gmail API
        max_workers: int = 4
            Max number of worker threads to run in executor
        '''
        bundle_gen = await self._chunk_message_bundles(chunk_size, query_limit)
        await self._enqueue_chunks(bundle_gen, window_size, max_workers)

        if tracked:
            await self.log_after_complete()

    async def log_after_complete(self):
        while True:
            if self.chunk_count > len(self.finished_bundles):
                await asyncio.sleep(3)
                continue
            else:
                break

        await self._finalize_task()
