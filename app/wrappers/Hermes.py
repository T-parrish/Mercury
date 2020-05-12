import time
import asyncio
import concurrent.futures

from typing import Optional, List, Generator
from functools import partial
from httplib2 import Http

from ..helpers.clock import coClock, clock
from .BaseWrapper import BaseWrapper
from ..data_structures.CommNode import CommNode, CommNodeBuildManager, CommNodeBuilder

from queue import Queue

class Hermes(BaseWrapper):
    '''
    Sub-class to facilitate scraping and parsing individual messages from gmail api

    Attributes:
    -----------
        creds: any
            Google Oauth2 credential object with appropriate scopes

        query_list: List[str]
            list of msg id strings to pass back through the executioner

        throttle_coefficient: float
            scales the sleep timing on subsequent bundle requests

    Methods:
    --------
        hermes(self, record_list: List[Postgres Records], window_size: int)
            data scraping and processing chain for gmail messages

        _enqueue(self, bundle_gen: Generator[str, None, None], queue: Queue)
            returns the bundle size and populates the main work queue

        _batcher(self, id_bundle: List[str])
            takes a list of msg_ids and bundles them into a
            batch httprequest object. The callback re-populates
            the query_list instance attribute

        _bundler(record_list: List[str], window_size: int)
            generator function that takes a list of msg_id
            strings and bundles it into chunks
            of size == window_size

    '''
    __slots__ = ['comm_nodes', 'query_list', 'message_count', 'throttle_coefficient']

    def __init__(self, creds: any, throttle_coefficient: float) -> None:
        super().__init__(creds)
        self.comm_nodes = []
        self.query_list = list()
        self.message_count = 0
        self.throttle_coefficient = throttle_coefficient


    async def hermes(self,
                     record_list: List['Record'],
                     window_size: int,
                     ) -> None:
        '''
        Bundles message ids and requests the messages from google using ThreadPool

        Args:
        ------
            record_list: List[Postgres Records]
                list of strings corresponding to an email in your inbox

            window_size: int
                size of bundle to query Gmail api in batches

        '''

        # container to store batch request objects
        queue = Queue()
        loop = asyncio.get_event_loop()

        # Initial query list from postgres
        self.query_list = [record['message_id'] for record in record_list]
        self.message_count = self.message_count + len(self.query_list)

        t0 = time.perf_counter()

        attempt = 0

        while True:
            # Increment attempt variable to further throttle subsequent queries
            attempt += 1
            routine = partial(self._executioner, queue, attempt)

            try:
                # Generator function to package the ids into bundles of size == window_size
                bundle_generator = self._bundler(self.query_list, window_size)
                bundle_count = self._enqueue(bundle_generator, queue)

                if bundle_count <= 1:
                    break

            except Exception as e:
                print(f'error populating queue: {e}')
                break

            # Set query_list attribute to an empty list after filling queue
            # So that it can be re-populated by the batch callback
            self.query_list = list()

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                futures = [
                    loop.run_in_executor(pool, routine)
                    for _ in range(0, bundle_count)
                ]
                result = await asyncio.gather(*futures)

        t1 = time.perf_counter() - t0

        # clear msg_ids and free memory
        del self.query_list

        out_msg = f'\nIt takes {t1} seconds to get {self.message_count} messages \
                    \nnumber of messages downloaded: {len(self.comm_nodes)} \
                    \nnumber of attempts: {attempt}'

        print(out_msg)

        return self.comm_nodes

    def _enqueue(self, bundle_gen: Generator[str, None, None], queue: Queue) -> int:
        bundle_count = 0

        while True:
            try:
                bundle = next(bundle_gen)
                bundle_count += 1
                queue.put(self._batcher(bundle))
            except StopIteration:
                break

        return bundle_count

    # @clock
    def _executioner(self, queue: Queue, attempt: int = 1) -> str:
        '''
        Worker that Executes the bundle query to Gmail API on a separate thread

        Params:
        -------
           queue: Queue[Batch Request Objects]
               Reference to a thread-safe queue data structure
            attempt:
                Number of times this query has failed
        '''
        sleep_modifier = .1 + (attempt * self.throttle_coefficient)
        time.sleep(sleep_modifier)
        http = Http()
        try:
            batch = queue.get()
            batch.execute(http=http)
        except Exception as e:
            print(f'Error executing batch query: {e}')
            return

        return 'finished processing batch'


    def _batcher(self,
                 id_bundle: List[str],
                 ) -> any:
        '''
        takes bundles of msg ids and bundles them into an http batch request

        Params:
        -------
           id_bundle: List[str]
               a list of msg id strings of length == window_size

        Returns:
        --------
           HTTP batch request object to be stored in a queue for execution

        Callback:
        --------
           collaback:
                gets a request_id & & (response || exception)
                sends the message id of failed requests back to query_list

        '''
        def collaback(request_id: str,
                      response: any,
                      exception: Exception,
                      *args,
                      **kwargs):

            '''General callback for the batch request'''
            if exception is None:
                
                self.comm_nodes.append(CommNodeBuildManager.construct(response))

            else:
                # If there's an error, add the id back to the query_list
                target = id_bundle[int(request_id)-1]
                self.query_list.append(target)

                print(f'request_id throwing error: {request_id}\nthrowing batch back to the queue: {id_bundle[int(request_id)-1]}\nException: {exception}\n')

        batch = self.service.new_batch_http_request(callback=collaback)

        for msg_id in id_bundle:
            batch.add(self.service.users()
                      .messages()
                      .get(userId=self.userId, id=msg_id))

        return batch

    @staticmethod
    def _bundler(record_list: List[str],
                 window_size: int
                 ) -> List[str]:
        ''' Bundles message ids of size == window_size with a generator function '''
        i = 0

        while i + window_size <= len(record_list):
            yield record_list[i:i+window_size]
            i += window_size

        yield record_list[i:-1]
