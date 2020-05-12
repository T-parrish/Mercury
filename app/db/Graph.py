from sqlalchemy import Table, Column, String, ForeignKey, DateTime, Numeric, Integer, Enum

from sqlalchemy.dialects.postgresql import UUID

from . import metadata, PartOfConvo

interaction_groups = Table(
    "interaction_groups", metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('parent_node', String(100), ForeignKey('graph_nodes.email')),
    Column('interaction_id', UUID(as_uuid=True), ForeignKey('interactions.id', ondelete="CASCADE")),
    Column("owner", UUID(as_uuid=True), ForeignKey('users.id'), nullable=False),
)

# SELECT * FROM interaction_group
# LEFT JOIN graph_nodes ON interaction_group.parent_node == graph_nodes.email
# FULL JOIN interactions on interaction_group.interaction_id == interactions.id
# WHERE owner == curr_user.id


# Each interaction between node U and node V with a timestamp and score
interactions = Table(
    "interactions", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("date", DateTime),
    Column("date_string", String(length=25)),
    Column("message_id", ForeignKey('message_objs.message_id', ondelete="CASCADE")),
    Column("node_u", ForeignKey('graph_nodes.email')),
    Column("node_v", ForeignKey('graph_nodes.email')),
    Column("conn_type", Enum(PartOfConvo)),
    Column("score", Numeric(6, 4))
)

# Each data node in the graph stores relevent data and
# references to all observed Interactions (graph neighbors)
# from its own perspective
graph_nodes = Table(
    "graph_nodes", metadata,
    Column("email", String(length=100), primary_key=True, unique=True),
    Column("name", String(length=100)),
    Column("domain", String(length=50)),
)
