from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime, ARRAY, Text, JSON, Enum

from sqlalchemy.dialects.postgresql import UUID

from . import PartOfConvo
from . import metadata

# Stores the message ids and thread ids for every message
# in a user's inbox, used later to keep track of last data pull
# and to run other operations without having to re-pull the data from the googs
message_objs = Table(
    "message_objs", metadata,
    Column("owner", UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False),
    Column("message_id", String(length=20), primary_key=True),
    Column("thread_id", String(length=20)),
    Column("last_fetch", DateTime)
)

# Each message is parsed into a comm node, tracks the
# parsed message body, labels, and date of each message
comm_nodes = Table(
    "comm_nodes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("message_id", String(length=20), ForeignKey('message_objs.message_id', ondelete="CASCADE")),
    Column("html_body", Text()),
    Column("text_body", Text()),
    Column("mimetypes", ARRAY(String(length=100))),
    Column("ip_address", String(length=100)),
    Column("subject", Text()),
    Column("date", DateTime),
    Column("keywords", JSON),
    Column("labels", ARRAY(String(length=100)))
)

# Entities are created for each party in each conversation
# Tracks the name, domain, and email in every instance
# Tracks the message keywords if the entity is the message originatory
entities = Table(
    "entities", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(length=200)),
    Column("name", String(length=200)),
    Column("domain", String(length=200)),
    Column("msg_id", String(length=20), ForeignKey('message_objs.message_id', ondelete="CASCADE")),
    Column('poc', Enum(PartOfConvo))
)
