#!/usr/bin/python3

"""
This script checks the configured max prefixes for a bgp peer on a juniper router and checks it against what is
in peeringDB.

It is intended to run via cron and generate some output (email or something else) to indicate when a peer updates max
perfixes in peeringDB and therefore the router ocnfig needs to be updated.

It can also be run 'adhoc' which will generate a table of all peers and display configured max prefixes vs peeringDB
"""

# TODO: command line options to run ad hoc (eg. print table to STDOUT)
# TODO: when running ad hoc, have option to print full output or just mismatches (right now, print full table)
# TODO: generate junos set commands to fix mismatch
#       this will require a change in data structure.  the module that parses the BGP config (ConfiguredPeers)
#       returns two dictionaries (one for each protocol).  in order to have the group name (needed for set commands),
#       we need a list of dictionaries, which complicates downstream processing.  maybe save this for when the script
#       is rewritten with classes?


from argparse import ArgumentParser
import json
import urllib.request
from jnpr.junos import Device
from prettytable import PrettyTable


targetrouter = '161.253.191.250'
username = 'netconf'
path2keyfile = '/home/agallo/.ssh/netconf'


def GetConfig(router):
    '''
    retrieve config from router.
    filter to retrieve only BGP stanza (though that doesn't appear to work since ConfiguredPeers requires the full
    config path to the group (peerList = bgpconfig['configuration'][0]['protocols'][0]['bgp'][0]['group'])
    retrieve in json, because it's much easier than XML
    :param router:
    :return: bgpstanza
    '''
    with Device(router, user=username, ssh_private_key_file=path2keyfile) as dev:
        a = dev.rpc.get_config(filter_xml='protocols/bgp', options={'format': 'json'})
    return a


def ConfiguredPeers(bgpconfig):
    '''
    take the BGP config in JSON format and extract
    peer AS, max v4 prefixes, max v6 prefixes
    AS is both authoritative an unique and is used as a key to search peeringDB
    :param bgpconfig:
    :return: two  dictionaries (one for each protocol); key=ASN, value=configured max prefixes
    '''
    peerList = bgpconfig['configuration'][0]['protocols'][0]['bgp'][0]['group']
    extracted4 = {}
    extracted6 = {}
    for peer in peerList:
        peerAS = int(peer['peer-as'][0]['data'])
        # check to see if family options are configured and if so, which family we're dealing with
        if 'family' in peer:
            familytype = list(peer['family'][0].keys())[0]
            if familytype == 'inet':
                maxv4 = int(peer['family'][0]['inet'][0]['unicast'][0]['prefix-limit'][0]['maximum'][0]['data'])
                extracted4.update({peerAS: maxv4})
            if familytype == 'inet6':
                maxv6 = int(peer['family'][0]['inet6'][0]['unicast'][0]['prefix-limit'][0]['maximum'][0]['data'])
                extracted6.update({peerAS: maxv6})
    return extracted4, extracted6


def GenerateASN(v4, v6):
    '''
    generate a simple master list of all ASNs configured on that router.  This single list will have both
    v4 and v6 peers.  It will be used to query peeringDB
    :param v4: the list of dictionaries of configured v4 prefix limits
    :param v6: the list of dictionaries of configured v4 prefix limits
    :return: ASNs
    '''
    ASNs = []
    for item in v4:
        ASNs.append(item)
    for item in v6:
        if item not in ASNs:
            ASNs.append(item)
    ASNs.sort()
    return ASNs


def GetPeeringDBData(ASNs):
    '''
    Query peeringDB for max prefixes for each configured peer
    this will retrieve both v4 and v6 for each ASN, even if we have only one protocol configured
    :param ASNs: list of ASNs
    :return: two dictionaries (one for each protocol); key=ASN, value=announced max prefixes
    '''
    baseurl = "https://www.peeringdb.com/api/net?asn="
    announcedv4 = {}
    announcedv6 = {}
    for item in ASNs:
        with urllib.request.urlopen(baseurl + str(item)) as raw:
            jresponse = json.loads(raw.read().decode())
            max4 = jresponse['data'][0]['info_prefixes4']
            max6 = jresponse['data'][0]['info_prefixes6']
            announcedv4.update({item: max4})
            announcedv6.update({item: max6})
    return announcedv4, announcedv6


def findMismatch(cfgMax4, cfgMax6, annc4, annc6):
    '''
    compare data from peeringDB & what is configured; note mismatches
    :param cfgMax4: dictionary of v4 ASN: max prefix configured
    :param cfgMax6: dictionary of v6 ASN: max prefix configured
    :param annc4: dictionary of v4 ASN: max prefix from peeringDB
    :param annc6: dictionary of v6 ASN: max prefix from peeringDB
    :return: v4table, v6table (lists of dictionaries)
    '''
    v4table = []
    v6table = []
    #  Because the peeringDB list should be a superset of what is configured, use that as the iterator
    for ASN, prefixes in announced4.items():
        if int(ASN) in configMax4:
            if prefixes == 0:               # some networks don't list anything on pDB
                v4table.append({'ASN': ASN, 'configMax4': configMax4[int(ASN)], 'prefixes': prefixes, 'mismatch': 'n/a'})
            elif prefixes != configMax4[int(ASN)]:
                v4table.append(
                    {'ASN': ASN, 'configMax4': configMax4[int(ASN)], 'prefixes': prefixes, 'mismatch': 'YES'})
            else:
                v4table.append(
                    {'ASN': ASN, 'configMax4': configMax4[int(ASN)], 'prefixes': prefixes, 'mismatch': ''})
    for ASN, prefixes in announced6.items():
        if int(ASN) in configMax6:
            if prefixes == 0:               # some networks don't list anything on pDB
                v6table.append(
                    {'ASN': ASN, 'configMax6': configMax6[int(ASN)], 'prefixes': prefixes, 'mismatch': 'n/a'})
            elif prefixes != configMax6[int(ASN)]:
                v6table.append(
                    {'ASN': ASN, 'configMax6': configMax6[int(ASN)], 'prefixes': prefixes, 'mismatch': 'YES'})
            else:
                v6table.append(
                    {'ASN': ASN, 'configMax6': configMax6[int(ASN)], 'prefixes': prefixes, 'mismatch': ''})

    return v4table, v6table


def createTable(v4results, v6results, suppress):
    """
    Create a pretty table
    :param v4results (list of dictionaries)
    :param v6results (list of dictionaries)
    :param supress (supress entires with no mismatch?  BOOL, True set default in argparse config()
    :return: nothing!  print to STDOUT
    """
    Tablev4 = PrettyTable(['ASN', 'v4config', 'v4pDB', 'Mismatch?'])
    Tablev6 = PrettyTable(['ASN', 'v6config', 'v6pDB', 'Mismatch?'])
    for entry in v4results:
        if not suppress:
            Tablev4.add_row([entry['ASN'], entry['configMax4'], entry['prefixes'], entry['mismatch']])
        elif entry['mismatch'] == "YES":
            Tablev4.add_row([entry['ASN'], entry['configMax4'], entry['prefixes'], entry['mismatch']])
    for entry in v6results:
        if not suppress:
            Tablev6.add_row([entry['ASN'], entry['configMax6'], entry['prefixes'], entry['mismatch']])
        elif entry['mismatch'] == "YES":
            Tablev6.add_row([entry['ASN'], entry['configMax6'], entry['prefixes'], entry['mismatch']])
    print("v4 results")
    print(Tablev4)
    print("\n\n\n")
    print("v6 results")
    print(Tablev6)
    return


def generateSetCommands(v4results, v6results, bgpstanza):
    """
    generate the Junos set commands necessary to update config to match what is in peeringDB
    :param v4results:
    :param v6results:
    :param bgpstanza:
    :return: a list of commands
    """
    v4commands = []
    v6commands = []
    for item in v4results:
        if item['mismatch'] == 'YES':
            for group in bgpstanza['configuration'][0]['protocols'][0]['bgp'][0]['group']:
                if 'family' in group:
                    if 'inet' in group['family'][0]:
                        if item['ASN'] == int(group['peer-as'][0]['data']) and list(group['family'][0].keys())[0] == 'inet':
                            groupname = group['name']['data']
                            newpfxlimit = item['prefixes']
                            command = "set protocols bgp group {} family inet unicast prefix-limit maximum {}".format(
                                groupname, newpfxlimit)
                            v4commands.append(command)
    for item in v6results:
        if item['mismatch'] == 'YES':
            for group in bgpstanza['configuration'][0]['protocols'][0]['bgp'][0]['group']:
                if 'family' in group:
                    if 'inet6' in group['family'][0]:
                        if item['ASN'] == int(group['peer-as'][0]['data']) and list(group['family'][0].keys())[0] == 'inet6':
                            groupname = group['name']['data']
                            newpfxlimit = item['prefixes']
                            command = "set protocols bgp group {} family inet6 unicast prefix-limit maximum {}".format(
                                groupname, newpfxlimit)
                            v6commands.append(command)
    return v4commands, v6commands


def main():
    bgpstanza = GetConfig(targetrouter)
    configMax4, configMax6 = ConfiguredPeers(bgpstanza)
    ASNlist = GenerateASN(configMax4, configMax6)
    announced4, announced6 = GetPeeringDBData(ASNlist)
    v4results, v6results = findMismatch(configMax4, configMax6, announced4, announced6)
    createTable(v4results, v6results, suppress)
    commands4, commands6 = generateSetCommands(v4results, v6results, bgpstanza)

main()
