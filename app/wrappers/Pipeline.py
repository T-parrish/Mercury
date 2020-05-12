import time
import asyncio
import concurrent.futures
import random

from typing import Optional, List, Generator, Dict, Union, Tuple, Awaitable, Callable, Optional
from functools import partial
from httplib2 import Http

from .BaseWrapper import BaseWrapper, WrapperOpts
from ..data_structures.CommNode import CommNode, CommNodeBuildManager, CommNodeBuilder

from queue import Queue

class Pipeline(BaseWrapper):
    '''
    Sub-class to handle full message scraping and parsing pipeline asynchronously

    Attributes:
    -----------
        creds: any
            Google Oauth2 credential object with appropriate scopes

        comm_nodes: List[CommNode]
            List of messages that have been fully cleaned and parsed

        query_list: List[str]
            List of msg id strings to pass back through the executioner

        throttle_coefficient: float
            Scales the sleep timing on subsequent bundle requests

        message_count: int
            Number of messages returned by gmail query

        message_ids: List[Dict[str, str]]
            List of message id dictionaries returned by gmail query

    Methods:
    --------
        _bundler(record_list: List[str], window_size: int)
            generator function that takes a list of msg_id
            strings and bundles it into chunks
            of size == window_size
        _clean_ids(self, msg_res: List[Dict[str,str]])
            Takes a list of dictionaries containing msg_id
            from gmail query and returns a list of msg_id strings
        _clone_interface(self)
            Returns a copy of the Pipeline interface to allow for splitting the hermes workload on different worker processes
        queryGmail(self, most_recent: str, limit: Optional[int] = 500)
            queries Gmail for a list of message id dictionaries
            and returns a list of msg_id strings

        hermes(self, record_list: List[Postgres Records], window_size: int)
            data scraping and processing chain for gmail messages

        _enqueue(self, bundle_gen: Generator[str, None, None], queue: Queue)
            returns the bundle size and populates the main work queue

        _batcher(self, id_bundle: List[str])
            takes a list of msg_ids and bundles them into a
            batch httprequest object. The callback re-populates
            the query_list instance attribute


    '''
    __slots__ = ['comm_nodes', 'query_list', 'message_count', 'throttle_coefficient', 'message_ids', 'interface_id']

    def __init__(self,
                 creds: Dict[str, Union[str, List[str]]],
                 throttle_coefficient: float,
                 interface_id: Optional[str] = '',
                 ) -> None:
        super().__init__(creds)
        self.comm_nodes = list()
        self.query_list = list()
        self.message_count = 0
        self.throttle_coefficient = throttle_coefficient
        self.message_ids = list()
        self.interface_id = interface_id


    @staticmethod
    def _clean_ids(msg_res: List[Dict[str, str]]) -> List[str]:
        ''' Returns a list of msg id strings from a list of dictionaries '''
        output = [msg['id'] for msg in msg_res]
        return output

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

    def _clone_interface(self, interface_id: str) -> 'Pipeline':
        return Pipeline(self.creds, self.throttle_coefficient, interface_id)


    async def queryGmail(self,
                         most_recent: Optional[str],
                         limit: int = 500,
                         ) -> Tuple[List[Dict[str, str]], int]:
        '''
        Queries the Gmail api for a list of message_ids

        Parameters:
        -----------
            most_recent: str
                most recently pulled msg_id for a particular user
            limit: int
                The max number of entries to be pulled from paginated API
                increments by 100

        Returns:
        --------
            Union[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]
                A list of dicts or a dict with a string key mapped dict list
        '''
        query = self.service.users().messages().list(userId=self.userId)

        try:
            response = query.execute()
        except Exception as e:
            print(f'Error querying Gmail api: {e}')
            return list()

        msg_ids = []
        if 'messages' in response:
            msg_ids.extend(self._clean_ids(response['messages']))

        while 'nextPageToken' in response:
            # if the most recently pulled message is in the
            # previous batch of 100 msg_ids, break the loop
            if most_recent and most_recent in set(msg_ids):
                break

            # break the loop if we pulled more than the limit
            if len(msg_ids) >= limit:
                break

            try:
                page_token = response['nextPageToken']

                response = self.service.users().messages().list(
                    userId=self.userId,
                    pageToken=page_token
                ).execute()

                msg_ids.extend(self._clean_ids(response['messages']))

            except Exception as e:
                print(f'\nError paginating over results from {action}: \n{e}\n')
                return msg_ids


        return msg_ids, len(msg_ids)

    async def hermes(self,
                     message_list: List[str],
                     window_size: int,
                     max_workers: int,
                     user_id: str,
                     callback: Callable[[str, int], None] = None
                     ) -> None:
        '''
        Bundles message ids and requests the messages from google using ThreadPool

        Args:
        ------
            message_list: List[str]
                list of message id strings

            window_size: int
                size of bundle to query Gmail api in batches

            max_workers: int
                Max number of threads to use with the batch http requests

            user_id: str
                uuid of the user running the data pull

            callback: Callable[[str, int], None]
                callback function to track progress across different threads

        '''

        # container to store batch request objects
        queue = Queue()
        loop = asyncio.get_event_loop()

        # list of message ids to bundle and get from Gmail
        self.query_list = message_list
        self.message_count = self.message_count + len(self.query_list)

        t0 = time.perf_counter()

        attempt = 0

        while True:
            # Increment attempt variable to throttle subsequent queries
            attempt += 1
            routine = partial(self._executioner, queue, attempt)

            try:
                # Generator function to package the ids into bundles of size == window_size
                bundle_generator = self._bundler(self.query_list, window_size)
                bundle_count = self._enqueue(bundle_generator, queue)

                if bundle_count <= 1:
                    break

                if attempt > 5:
                    break

            except Exception as e:
                print(f'error populating queue: {e}')
                break

            # Set query_list attribute to an empty list after filling queue
            # So that it can be re-populated by the batch callback
            self.query_list = list()

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
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

        # Use callbacks to track progress of different threads
        if callback is not None:
            await callback((self.interface_id, len(self.comm_nodes)))

        return self.comm_nodes, user_id

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
        # Generate a small random number to sleep for
        sleep_start = random.uniform(0.3, 10**(-4))
        sleep_modifier = sleep_start + (attempt * self.throttle_coefficient)
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
