from typing import Optional, Dict, List, Set, Tuple, AbstractSet, Generator
from collections import namedtuple, Counter
from datetime import datetime
from itertools import permutations
from ..helpers import noArgClock

import uuid

from .Entity import POC


class Cluster(namedtuple('Cluster', ['msg_id', 'date', 'conn_u',
                                     'name', 'domain', 'msg_originator',
                                     'conn_v', 'connection_type', 'score'])):
    __slots__ = ()
    '''
    Each tuple represents a perspective on a message transaction, with one being
    generated for each permutation of entities clustered in a conversation

    Attributes:
    -----------
        from_perspective_email: str
            cleaned email address of the entity from which this cluster is being observed
        date: datetime
            datetime object
        name: str
            name collected from message communications
        domain: str
            domain of the message communication
        msg_id: str
            Id reference to gmail message
        msg_from: str
            email address for message originator
        msg_to: str
            email address for the direct message recipient
        connection_type: POC
            type of connection between nodes
        score: float
            weight of the connection
    '''
    msg_id: str             # msg ID
    date: datetime          # datetime object
    conn_u: str             # email perspective 'self'
    name: str               # entity name
    domain: str             # domain name
    msg_originator: str     # who originated the message
    conn_v: str             # conn between orig and 'other' from perspective of 'self'
    connection_type: POC    # type of connection between prev 2
    score: float            # score of the connection

class GraphNode(namedtuple('GraphNode', ['owner', 'email', 'name',
                                         'domain', 'observed_interactions'])):
    __slots__ = ()

    owner: str                  # string uuid to map node to owner
    email: str                  # string email of node
    name: str                   # string name of node
    domain: str                 # domain of node
    observed_interactions: str  # string uuid to map interactions to nodes

class Interaction(namedtuple('Interaction', [
    'interaction_key', 'date', 'date_string',
        'message_id', 'node_u', 'node_v', 'conn_type', 'score'])):
    __slots__ = ()

    interaction_key: str        # string uuid to map interactions to node
    date: datetime              # datetime object of corresponding interaction
    date_string: str            # string representation of date to pass via json to NEXT
    message_id: str             # Gmail api message id reference
    node_u: str                 # string email of 'self' node
    node_v: str                 # string email of 'other' node
    conn_type: POC              # type of connection between _u and _v
    score: float                # calculated score of interaction


class UserNode:
    __slots__ = ['email', 'names', 'domain', 'edges', 'owner']

    def __init__(self,
                 email: str = '',
                 name: str = '',
                 domain: str = '',
                 interaction: str = '',
                 owner: str = '',
                 ) -> None:
        self.email = email
        self.names = list()
        self.names.append(name.strip())
        self.domain = domain
        self.edges = [interaction]
        self.owner = owner

        print(f'initializing: {name}')

    '''
    Initial state for a User Node

    Attributes:
    -----------
        email: str
            email address of the node (unique)
        name: Set[str]
            set of all names associated with the email address
        domain: str
            domain of the email address
        edges: List[str]
            list of all UUID strings associated with interactions
            related to this node
        owner: str
            String representation of owner UUID

    Methods:
    --------
        enrich_data(name: str, interaction: str) -> UserNode:
            adds name to name set and interaction to interaction array, returns itself.
        _get_name() -> str:
            Creates a counter from the list of scraped names and returns the most common
    '''

    def doSomething(self) -> None:
        pass

    def enrich_data(self,
                    name: str,
                    interaction: str
                    ) -> 'UserNode':
        self.edges.append(interaction)
        if len(name.strip()) > 0:
            self.names.append(name.strip())

        return self

    def _get_name(self) -> str:
        name_freq = Counter(self.names)

        return name_freq.most_common(1)[0][0]

class UserNodeBuilder:
    def __init__(self) -> None:
        self.user = UserNode()
        self.connections = set()
        self.clusters = 0
        self.interactions = list()
        self.graph = {}

    def _score_interaction(self, connection: Cluster) -> float:
        pass

    def _gen_permutations(self,
                          cluster: List['Record'],
                          originator: 'Record'
                          ) -> None:

        clean_cluster = cluster


        score = 1.0

        # Brute force baby
        # Safety mechanism for cases where there are
        # tons of people in a message chain.
        # Will probably need to find a better solution later.
        if len(cluster) > 10:
            clean_cluster = cluster[:10]

        try:
            # Generate all permutations of people in one message transaction
            permutes = permutations(clean_cluster, r=2)
            _flipper = 1

            for pair in permutes:
                _u = 0
                _v = 1
                copied = set(['CC', 'BCC'])

                for _ in range(0, 2):
                    connection_type = ''
                    # Logs CC -> CC relationship rather than CC -> FROM
                    if pair[_u]['poc'] in copied:
                        connection_type = pair[_u]['poc']
                    if pair[_v]['poc'] in copied:
                        connection_type = pair[_v]['poc']

                    else:
                        connection_type = pair[_v]['poc']

                    connection = Cluster(
                        pair[_u]['msg_id'],  # msg ID
                        pair[_u]['date'],    # datetime object
                        pair[_u]['email'],   # email perspective 'self'
                        pair[_u]['name'],    # entity name
                        pair[_u]['domain'],  # domain name
                        originator,          # who originated the message
                        pair[_v]['email'],   # conn between orig and 'other' from perspective of 'self'
                        connection_type,     # type of connection between prev 2
                        score                # score of the connection
                    )

                    # bit flip to change perspective (╯°□°)╯︵ ┻━┻
                    _v ^= _flipper
                    _u ^= _flipper

                    self.connections.add(connection)
        except Exception as e:
            print(f'Error creating permutations and clusters: {e}')

    def handleClusters(self,
                       cluster_gen: Generator[List['Record'], None, None]
                       ) -> None:
        while True:
            try:
                cluster = next(cluster_gen)
                self.clusters += 1
            except StopIteration:
                break

            # Could either add a message originator field to Entities
            # or iterate over them to find the necessary info with filter
            originator = list(filter(lambda x: x['poc'] == 'FROM', cluster))

            #  If there isn't an originator, move to the next cluster
            if len(originator) == 0:
                continue

            # Heavily CPU bound, could probably paralellize this
            # in background tasks by chunking the generators and
            # sending to different instances of UserNodeBuilder
            self._gen_permutations(cluster, originator[0]['email'])


        msg_out = f'Number of nodes: {len(self.connections)} \
                    Number of clusters: {self.clusters}'

        print(msg_out)
        return self

    def process_nodes(self, owner_uuid: str) -> None:
        node_set = set()
        for conn in iter(self.connections):
            interaction_uuid = str(uuid.uuid4())
            inter = Interaction(
                interaction_uuid, conn.date,
                conn.date.strftime("%m/%d/%Y, %H:%M:%S"),
                conn.msg_id, conn.conn_u,
                conn.conn_v, conn.connection_type, conn.score
            )

            if conn.conn_u not in self.graph.keys():
                new_user_node = UserNode(
                    conn.conn_u,
                    conn.name,
                    conn.domain,
                    interaction_uuid,
                    owner_uuid

                )
                self.graph[conn.conn_u] = new_user_node

            if conn.conn_u in self.graph.keys():
                self.graph[conn.conn_u].enrich_data(conn.name, interaction_uuid)

            self.interactions.append(inter)

        return self

    def _rate_connection(self) -> float:
        pass

