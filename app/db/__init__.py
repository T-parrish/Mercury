import os
from databases import Database
from sqlalchemy import MetaData, create_engine
from .EnumTypes import PermissionLevel, PartOfConvo, TaskTypes, 

database = Database(
    os.getenv('DATABASE_URL', 'postgresql://postgres:rofl-copters@localhost/hermes')
)

engine = create_engine(str(database.url))
metadata = MetaData(bind=engine)

from .Users import users, User
from .ScrapeData import message_objs, comm_nodes, entities
from .Tasks import tasks
from .Graph import interactions, graph_nodes, interaction_groups

metadata.create_all(engine)
