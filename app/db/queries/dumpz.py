ratio_query = '''
  -- Query to get ratio of communication --
  SELECT DISTINCT sub.name, sum(sub.ratio)
    FROM (
      SELECT
        g_n.name,
        node_u,
        node_v,
        sum(CASE
          WHEN conn_type = 'TO' THEN 1
          WHEN conn_type = 'FROM' THEN -1
          ELSE 0 END) as ratio,
        min(date),
        max(date)
      FROM interactions i
      LEFT JOIN graph_nodes g_n on i.node_u = g_n.email
      GROUP BY g_n.email, node_u, node_v
      ) AS sub
  -- WHERE sub.ratio > -10 and sub.ratio < 10
  GROUP BY sub.name
  ORDER BY sum desc;
'''

full_graph = '''
  SELECT g_n.name, node_u, conn_type, node_v, count(conn_type), min(date), max(date)
  FROM interactions i
  LEFT JOIN graph_nodes g_n on i.node_u = g_n.email
  GROUP BY g_n.email, node_u, node_v, conn_type
  ORDER BY g_n.email, conn_type asc;
'''


not_sure = '''
  select g_n.email, g_n.name, inter.node_u, inter.node_v, inter.conn_type from interaction_groups i_g
  LEFT JOIN graph_nodes g_n on i_g.parent_node = g_n.email
  FULL JOIN interactions inter on inter.id = i_g.interaction_id
  ORDER BY g_n.email desc;
'''

contact_counts = '''
  SELECT
    g_n.name,
    g_n.email,
    inter.node_v,
    SUM(CASE WHEN conn_type = 'TO' THEN 1 ELSE 0 END) AS to_count,
    SUM(CASE WHEN conn_type = 'FROM' THEN 1 ELSE 0 END) AS from_count,
    SUM(CASE WHEN conn_type = 'CC' THEN 1 ELSE 0 END) AS cc_count,
    SUM(CASE WHEN conn_type = 'BCC' THEN 1 ELSE 0 END) AS bcc_count
  FROM interactions inter
  LEFT JOIN interaction_groups ig ON inter.id = ig.interaction_id
  FULL JOIN graph_nodes g_n on g_n.email = ig.parent_node
  WHERE ig.owner = :owner_id
  GROUP BY g_n.name, g_n.email, inter.node_u, inter.node_v
  ORDER BY g_n.name desc;
'''

all_edges = '''
  SELECT
    inter.node_u,
    inter.node_v
  FROM interactions inter
  RIGHT JOIN interaction_groups i_g ON inter.id = i_g.interaction_id
  WHERE i_g.owner = :owner_id
  GROUP BY inter.node_u, inter.node_v
  ORDER BY inter.node_u desc;
'''

all_nodes = '''
  SELECT parent_node
  FROM interaction_groups i_g
  WHERE i_g.owner = :owner_id
  GROUP BY parent_node;
'''
