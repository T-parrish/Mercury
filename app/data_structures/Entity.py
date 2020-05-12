from typing import AbstractSet
from enum import Enum
from collections import namedtuple


class POC(Enum):
    '''
    Part of Conversation for each Entity in message

    Options:
    --------
        TO = 1
        FROM = 2
        CC = 3
        BCC = 4
    '''
    TO = 1
    FROM = 2
    CC = 3
    BCC = 4

class Entity(namedtuple('Entity', ['email', 'name', 'domain', 'msg_id', 'poc'])):
    __slots__ = ()
    '''
    Data structure to store the different entities in each message.

    Attributes:
    -----------
        email: str
            cleaned email address
        name: str
            name collected from message communications
        domain: str
            domain of the message communication
        msg_id: str
            Id reference to gmail message
        poc: POC
            Part of conversation
    '''
    email: str
    name: str
    domain: str
    msg_id: str
    poc: POC
