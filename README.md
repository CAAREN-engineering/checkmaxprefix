This script retrieves the configured max prefixes for a bgp peer on a juniper router and checks it against what is
in peeringDB.

It is intended to run via cron and generate a file of Junos 'set' commands to update peers with new information from peeringDB (if there is a mismatch).

It can also be run ad hoc which will generate a table of all peers and display configured max prefixes vs peeringDB

Requirements:
 1. Juniper PyEz module
 1. router with netconf over ssh enabled
 1. user needs read privileges to the configuration
 1. a file (creds.py) which contains
     1. rtrdict (a dictionary of routers to check)**
     1. username
     1. path to the private key used to authenticate

See creds.py-EXAMPLE for the format.

_currently, this script will check only one router_.  It is best that the rtrdict in creds.py be a dictionary of a single router
