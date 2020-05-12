from collections import namedtuple

# Lookup set for POCs
poc_set = set([
    'From',
    'To',
    'Cc',
    'Bcc'
])

# Lookup set for headers we're tracking
target_set = set([
    'From',
    'To',
    'Cc',
    'Bcc',
    'Received-SPF',
    'Subject'
])

# Routine definition for plaintext cleaning generator
Routine = namedtuple('Operation', 'pattern repl op_name')
