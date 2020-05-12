import jwt
import os
import uuid

from datetime import datetime

from typing import Dict, Union, List

from app.db import TaskTypes, User
from . import BaseMediator
from . import users

from sqlalchemy.sql import select, insert

import google.oauth2.credentials


class AuthMediator(BaseMediator):
    '''
    Mediator to track login and user creation tasks

    Attributes:
    -----------
        hermes_user: Dict[str, Union[str, int]]
            User object authenticated and loaded into memory
        salt: str
            Salt used to hash passwords with Bcrypt algorithm. Needed to
            check hashes of stored password and input password to determine
            whether or not the entered password is valid for the user

    Methods:
    --------
        handle_jwt(self, access_token: str) -> AuthMediator:
            Takes a JWT access token and attempts to retrieve the user from
            Postgres. If the user isn't there, create a new user. Either way,
            store the resulting user as an instance attribute and return self.
        create_new_user(self)

    '''

    __slots__ = ['hermes_user', 'message']

    def __init__(self,
                 database: 'Postgres',
                 user_uuid: str,
                 TaskType: TaskTypes,
                 salt: str,
                 ) -> None:

        super().__init__(database, user_uuid, TaskType)
        self.hermes_user = None
        self.message = ''

    @staticmethod
    async def fetch_pg_user(email: str) -> Dict[str, Union[str, int]]:
        '''Fetches a User from Postgres by email address'''
        query = 'SELECT * FROM users WHERE users.email = :email'
        pg_user = await self.database.fetch_one(
            query=query,
            values={'email': email}
        )

        return pg_user

    async def log_in(self, email: str, password: str) -> 'AuthMediator':
        try:
            user = await self.fetch_pg_user(email)
        except Exception as e:
            print(f'Error fetching user from DB: {}', e)
            return self

        if not user:
            self.message = 'No user found with that email'
            return self

        # Initialize the default User object
        user_obj = User()

        # If the entered password == the password in the DB, store
        # the user data from Postgres in the User object and return the User object
        if user_obj.check_password(password,
                                   user['password'],
                                   os.getenv('BCRYPT_SALT', None)):
            self.hermes_user = User(
                user['id'],
                user['email'],
                password,
                user['name'],
                user['permission_level'],
                user['last_fetch'],
                user['creds']
            )

            return self.hermes_user
        else:
            self.message = 'Error logging in.'
            return self


    async def handle_jwt(self, access_token: str) -> 'AuthMediator':
        '''
        Wraps the logic of finding or creating a
        User when using an JWT auth strategy
        '''

        jwt_user = jwt.decode(access_token, os.getenv('JWT_SECRET', None))
        pg_user = fetch_pg_user(jwt_user.get('email'))


        if not pg_user:
            self.message = 'no user found with this token'
            return self

        else:
            # Otherwise, set the user id as an instance attribute
            # and track the login time for that user
            self.user_uuid = str(pg_user['id'])
            await self._track_login()

            self.hermes_user = pg_user

        return self

    async def create_new_user(self,
                              email: str,
                              name: str,
                              verified: bool,
                              phone: int,
                              *args,
                              **kwargs,
                              ) -> 'AuthMediator':
        '''
        Create a new User uuid and change the task_type
        to NEW USER and initialize a wrapper to track the task of
        creating a new user
        '''

        user_uuid = uuid.uuid4()  # Generate new user UUID
        self.user_uuid = str(user_uuid)  # set the str UUID on the mediator
        self.task_type = TaskTypes['NEW_USER']  # Track user-creation task

        try:
            insert_stmt = '''
            INSERT INTO users
            VALUES(:id, :email, :name, :permission, :verified, :phone, :last_fetch)
            '''
            new_user = {"id": self.user_uuid, 'email': email,
                        'name': name, 'permission': 'BASE',
                        'verified': verified, 'phone': phone,
                        'last_fetch': datetime.now()}

            await self.database.execute(
                query=insert_stmt,
                values=new_user
            )

            #  if the data is saved to DB successfully, set the user object
            #  on the mediator
            self.hermes_user = new_user

        except Exception as e:
            self._update_errors(e)

        return self

    async def update_credentials(self, creds: Dict[str, Union[str, List[str]]]) -> 'AuthMediator':
        try:
            update_user = self.table_refs['users'].update(). \
                where(self.table_refs['users'].c.id == self.user_uuid). \
                values(
                    token=creds['token'],
                    refresh_token=creds['refresh_token'],
                    token_uri=creds['token_uri'],
                    client_id=creds['client_id'],
                    client_secret=creds['client_secret'],
                    scopes=creds['scopes']
            )

            await self.database.execute(update_user)

        except Exception as e:
            self._update_errors(e)

        # update the credentials on the User object and set it on the mediator
        self.hermes_user = self.hermes_user.update_creds(creds)
        await self._finalize_task()

        return self
