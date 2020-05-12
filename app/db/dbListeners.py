import aioredis
import os
from sanic_session import Session, AIORedisSessionInterface

from databases import Database

session = Session()

async def start_db(app, loop):
    ''' before server starts '''

    try:
        app.database = Database(
            os.getenv(
                'DATABASE_URL',
                'postgresql://postgres:rofl-copters@localhost/hermes'
            )
        )

        await app.database.connect()
    except Exception as e:
        print('Error connecting to database')

    app.redis = await aioredis.create_redis_pool(
        os.getenv(
            'REDIS_URL',
            'redis://localhost'
        )
    )
    # init extensions fabrics
    session.init_app(app, interface=AIORedisSessionInterface(app.redis))

async def stop_db(app, loop):
    ''' after server stops '''
    await app.database.disconnect()
