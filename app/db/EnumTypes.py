import enum

class PermissionLevel(enum.Enum):
    '''
    NONE = 1
    BASE = 2
    PAID = 3
    ADMIN = 4
    SUPER = 5
    '''
    NONE = 1
    BASE = 2
    PAID = 3
    ADMIN = 4
    SUPER = 5

class PartOfConvo(enum.Enum):
    ''''
    FROM = 1
    TO = 2
    CC = 3
    BCC = 4
    '''
    FROM = 1
    TO = 2
    CC = 3
    BCC = 4

class TaskTypes(enum.Enum):
    '''
    DB_INSERT = 1
    DB_LOOKUP = 2
    DB_UPDATE = 3
    SCRAPE = 4
    USER_NODES = 5
    AUTHENTICATE = 6
    NEW_USER = 7
    '''
    DB_INSERT = 1
    DB_LOOKUP = 2
    DB_UPDATE = 3
    HERMES = 4
    USER_NODES = 5
    AUTHENTICATE = 6
    NEW_USER = 7
