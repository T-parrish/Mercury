import asyncio
from typing import Optional, Union, List, Dict

from googleapiclient.discovery import build
from ..helpers.clock import coClock, clock
from .BaseWrapper import BaseWrapper, WrapperOpts
from ..data_structures.CommNode import CommNodeBuildManager, CommNode


class Gmail(BaseWrapper):
    '''
    Subclass to facilitate List requests with the Gmail API

    Attributes:
    -----------
        creds: any
            Google Oauth2 credential object with appropriate scopes

        max_results: int
            Number of results to grab

    Methods:
    --------
        getSingleMessage(self, msg_id: str)
            Gets a single message from Gmail api and
            creates a comm node for testing + debugging

        queryGmail(self, action: WrapperOpts)
            Queries the Gmail api within a predefined scope of actions:
            LABELS - pulls a list of labels
            MESSAGES - pulls a list of messages
            THREADS - pulls a list of threads

    '''

    def __init__(self, creds: any, max_results: Optional[int] = 5) -> None:
        super().__init__(creds, max_results)


    async def getSingleMessage(self, msg_id: str) -> CommNode:
        '''
        Gets a single message from Gmail api by message ID,
        generates a comm node and returns it for testing / debugging.

        Params:
        -------
            msg_id: str
                Gmail message id string to Query for

        '''
        try:
            response = self.service.users().messages().get(userId=self.userId, id=msg_id).execute()

            comm_node = CommNodeBuildManager.construct(response)
        except Exception as e:
            msg = f'Errory querying Gmail API for msg {msg_id} \nError: {e}\n\n'
            return msg

        return comm_node

    @coClock
    async def queryGmail(self,
                         action: WrapperOpts,
                         limit: int = 500,
                         ) -> Union[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]:
        '''
        Queries the Gmail api within a predefined scope of actions.

        Parameters:
        -----------
            action: WrapperOpts
                The query type to run against the Gmail API
            limit: int
                The max number of entries to be pulled from paginated API
                increments by 100

        Returns:
        --------
            Union[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]
                A list of dicts or a dict with a string key mapped dict list
        '''
        query = self.wrappers[action]

        try:
            response = query.execute()
        except Exception as e:
            print(f'Error querying Gmail api: {e}')
            return list()

        msg_objs = []
        if 'messages' in response:
            msg_objs.extend(response['messages'])

        while 'nextPageToken' in response:
            # break the loop if we pulled more than the limit
            if len(msg_objs) >= limit:
                return msg_objs

            try:
                page_token = response['nextPageToken']

                response = self.service.users().messages().list(
                    userId=self.userId,
                    pageToken=page_token
                ).execute()

                msg_objs.extend(response['messages'])

            except Exception as e:
                print(f'\nError paginating over results from {action}: \n{e}\n')
                return msg_objs


        if len(msg_objs) > 0:
            return msg_objs
        else:
            return response
