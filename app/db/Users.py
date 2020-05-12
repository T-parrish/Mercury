import os
import bcrypt
import google.oauth2.credentials

from sqlalchemy import Table, Column, String, ForeignKey, DateTime, Enum, Boolean, ARRAY

from sqlalchemy.dialects.postgresql import UUID

from . import PermissionLevel, metadata

# Table of Hermes users - eg top level product users
# Used to filter comm nodes by 'owner' of the data
users = Table(
    "users", metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, unique=True),
    Column("email", String(length=100), unique=True, nullable=False),
    Column("name", String(length=100)),
    Column("permission_level", Enum(PermissionLevel), nullable=False),
    Column("last_fetch", DateTime),
    Column("token", String()),
    Column("refresh_token", String()),
    Column("token_uri", String()),
    Column("client_id", String()),
    Column("client_secret", String()),
    Column("scopes", ARRAY(String()))
)


class User:
    '''
    User Object

    Methods:
        @staticmethod
        _encrypt_password(input_pass: str, salt: str)
            takes an input password and a salt to hash the password

        @staticmethod
        check_password(input_pass: str, hashed_pass: str, salt: str)
            checks whether the hashed input password
            is == a previously hashed password
            using a salt. If true, the password is a match.

        @property
        oauth_credentials()
            Returns the Google oauth2 credential object to use
            with Google APIs

    '''

    __slots__ = ['id', 'email', 'password', 'name', 'permission_level', 'last_fetch', 'creds']

    def __init__(self,
                 id: str = None,
                 email: str = None,
                 password: str = None,
                 name: str = '',
                 permission_level: PermissionLevel = PermissionLevel['NONE'],
                 last_fetch: DateTime = None,
                 creds: Dict[str, Union[str, int]]) = {}:

        self.email = email
        if password is not None:
            self.password = _encrypt_password(password, os.getenv('BCRYPT_SALT', None))
        else:
            self.password = None
        self.name = name
        self.permission_level = PermissionLevel['NONE']
        self.last_fetch = last_fetch,
        self.creds = creds


    @staticmethod
    def _encrypt_pasword(input_pass: str, salt: str) -> str:
        '''hashes a password with a salt to be stored in a database'''
        return bcrypt.hashpw(input_pass, salt)

    @staticmethod
    def check_password(input_pass: str, hashed_pass: str, salt: str) -> bool:
        '''returns True if the entered password is correct'''
        return bcrypt.hashpw(input_pass, salt) == hashed_pass

    @property
    def oauth_credentials(self) -> Dict[str, Union[str, List[str]]]:
        ''' Returns Google oauth2 credentials derived from token dict'''
        if not self.hermes_user:
            return {}

        creds = {'token': self.creds['token'],
                 'refresh_token': self.creds['refresh_token'],
                 'token_uri': self.creds['token_uri'],
                 'client_id': self.creds['client_id'],
                 'client_secret': self.creds['client_secret'],
                 'scopes': self.creds['scopes']}

        return google.oauth2.credentials.Credentials(**creds)

    def update_creds(self, creds: Dict[str, Union[str, int]]) -> 'User':
        self.creds = creds
        return self
