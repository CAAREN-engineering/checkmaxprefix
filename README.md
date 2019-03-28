This script retrieves the configured max prefixes for a bgp peer on a juniper router and checks it against what is
in peeringDB.

It is intended to run via cron and generate a file of Junos 'set' commands to update peers with new information from peeringDB (if there is a mismatch).

It can also be run ad hoc which will generate a table of all peers and display configured max prefixes vs peeringDB

Requirements:
 1. Juniper PyEz module
 1. router with netconf over ssh enabled
 1. user needs read privileges to the configuration

_You will need to edit the script to enter the router IP and credentials in function `GetConfig`:_

```
# ***************************************
# update this section with router info***
targetrouter = 'NOTSET'
username = 'NOTSET'
path2keyfile = 'NOTSET'
# ***************************************

