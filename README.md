This script checks the configured max prefixes for a bgp peer on a juniper router and checks it against what is
in peeringDB.

It is intended to run via cron and generate some output (email or something else) to indicate when a peer updates max
perfixes in peeringDB and therefore the router ocnfig needs to be updated.

It can also be run 'adhoc' which will generate a table of all peers and display configured max prefixes vs peeringDB

Requirements:
 1. Juniper PyEz module
 1. netconf private key


