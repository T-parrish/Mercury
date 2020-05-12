import os
import time

from enum import Enum
from typing import Optional, Union, List, Dict, Generator

from functools import partial

from googleapiclient.discovery import build
from httplib2 import Http

from ..helpers.clock import coClock, clock

import asyncio
from asyncio import Semaphore

import concurrent.futures

from queue import Queue

class WrapperOpts(Enum):
    '''
    Wrapper options to pull from different parts of the gmail API:
    Attributes:
    -----------
        LABELS = 1
        MESSAGES = 2
        THREADS = 3
    '''

    LABELS = 1
    MESSAGES = 2
    THREADS = 3

class BaseWrapper:
    '''
    Base Class interface to provide an easier mechanism to interact with Gmail API

    Attributes:
    -----------
        creds: any
            Google Oauth2 credential object with appropriate scopes

        max_results: int
            Number of results to grab

    Methods:
    --------
        _genServiceObjs(self)
            Helper method to generate service object and query wrappers

    '''
    __slots__ = ['creds', 'userId', 'maxResults', 'wrappers', 'service']

    def __init__(self, creds: any, max_results: Optional[int] = 5) -> None:
        self.creds = creds
        self.userId = 'me'
        self.maxResults = max_results
        self.wrappers = {}
        self.service = None


        if self.creds:
            self._genServiceObjs()
        else:
            raise Exception('you must authorize before initializing this object')


    def _genServiceObjs(self) -> None:
        '''
        Helper function to generate a gmail api service object when
        Gmail wrapper is instantiated with creds. Also stores a few
        convenience methods for accessing specific portions of the gmail api.
        '''
        service = build(
            os.environ.get('API_SERVICE_NAME'),
            os.environ.get('API_VERSION'),
            credentials=self.creds
        )

        self.service = service

        self.wrappers = {
            WrapperOpts(1): service.users().labels().list(userId=self.userId),
            WrapperOpts(2): service.users().messages().list(userId=self.userId),
            WrapperOpts(3): service.users().threads().list(userId=self.userId,
                                                           maxResults=self.maxResults),
        }
