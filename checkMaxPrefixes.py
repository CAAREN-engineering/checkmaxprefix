#!/usr/bin/python3

"""
This script checks the configured max prefixes for a bgp peer on a juniper router and checks it against what is
in peeringDB.

It is intended to run via cron and generate some output (email or something else) to indicate when a peer updates max
perfixes in peeringDB and therefore the router ocnfig needs to be updated.

It can also be run 'adhoc' which will generate a table of all peers and display configured max prefixes vs peeringDB
"""

from argparse import ArgumentParser
import json
import urllib.request
from jnpr.junos import Device


targetrouter = '161.253.191.250'
username = 'netconf'
path2keyfile = '/home/agallo/.ssh/netconf'


def GetConfig(router):
    '''
    retrieve config from router.
    filter to retrieve only BGP stanza
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
    peer name, max v4 prefixes, max v6 prefixes
    :param bgpconfig:
    :return: two lists of dictionaries (one for each protocol); key=ASN, value=configured max prefixes
    '''
    peerList = bgpconfig['configuration'][0]['protocols'][0]['bgp'][0]['group']
    extractedList4 = []
    extractedList6 = []
    for peer in peerList:
        peerAS = int(peer['peer-as'][0]['data'])
        # check to see if family options are configured and if so, which family we're dealing with
        if 'family' in peer:
            familytype = list(peer['family'][0].keys())[0]
            if familytype == 'inet':
                maxv4 = peer['family'][0]['inet'][0]['unicast'][0]['prefix-limit'][0]['maximum'][0]['data']
                peerentry = {peerAS: maxv4}
                extractedList4.append(peerentry)
            if familytype == 'inet6':
                maxv6 = peer['family'][0]['inet6'][0]['unicast'][0]['prefix-limit'][0]['maximum'][0]['data']
                peerentry = {peerAS: maxv6}
                extractedList6.append(peerentry)
    return extractedList4, extractedList6


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
        ASNs.append(str(list(item.keys())[0]))
    for item in v6:
        if str(list(item.keys())[0]) not in ASNs:
            ASNs.append(str(list(item.keys())[0]))
    ASNs.sort(key=int)
    return ASNs


def GetPeeringDBData(ASNs):
    '''
    Query peeringDB for max prefixes for each configured peer
    this will retrieve both v4 and v6 for each ASN, even if we have only one protocol configured
    :param ASNs: list of ASNs
    :return: two lists of dictionaries (one for each protocol); key=ASN, value=announced max prefixes
    '''
    baseurl = "https://www.peeringdb.com/api/net?asn="
    announcedv4 = []
    announcedv6 = []
    for item in ASNs:
        with urllib.request.urlopen(baseurl + item) as raw:
            jresponse = json.loads(raw.read().decode())
            max4 = jresponse['data'][0]['info_prefixes4']
            max6 = jresponse['data'][0]['info_prefixes6']
            tempdict4 = {item: max4}
            tempdict6 = {item: max6}
            announcedv4.append(tempdict4)
            announcedv6.append(tempdict6)
    return announcedv4, announcedv6


def main():
    bgpstanza = GetConfig(targetrouter)
    configMax4, configMax6 = ConfiguredPeers(bgpstanza)
    ASNlist = GenerateASN(configMax4, configMax6)
    announced4, announced6 = GetPeeringDBData(ASNlist)


main()
