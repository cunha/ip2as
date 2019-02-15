#!/usr/bin/env python
from argparse import ArgumentParser, FileType
from typing import List, Tuple

from traceutils.as2org.as2org import AS2Org
from traceutils.bgp.bgp import BGP
from traceutils.file2.file2 import File2
from traceutils.ixps.ixps import PeeringDB
from traceutils.radix.ip2as import IP2AS
from traceutils.utils.utils import max_num


def valid(asn):
    return asn != 23456 and 0 < asn < 64496 or 131071 < asn < 4200000000


def create_table(prefixes: List[Tuple[str, str]], peeringdb: PeeringDB, rir: List[Tuple[str, str]], bgp: BGP, as2org: AS2Org):
    table = IP2AS()
    table.add_private()
    ixp_prefixes = [(prefix, asn) for prefix, asn in peeringdb.prefixes.items() if not table.search_best_prefix(prefix)]
    for prefix, ixp_id in ixp_prefixes:
        table.add(prefix, asn=(-100 - ixp_id))
    prefixes = [(prefix, asn_s) for prefix, asn_s in prefixes if not table.search_best_prefix(prefix)]
    for prefix, asn_s in prefixes:
        asn = determine_bgp(asn_s, as2org, bgp)
        table.add(prefix, asn=asn)
    rir = [(prefix, asn_s) for prefix, asn_s in rir if not table.search_best_prefix(prefix)]
    for prefix, asn_s in rir:
        asns = list(map(int, asn_s.split('_')))
        asn = max(asns, key=lambda x: (bgp.conesize[x], -x))
        table.add(prefix, asn=asn)
    return table


def determine_bgp(asn_s, as2org: AS2Org, bgp: BGP):
    asns = []
    for asn in asn_s.split('_'):
        if asn[0] == '{':
            for asn in asn[1:-1].split(','):
                asns.append(int(asn))
        else:
            asns.append(int(asn))
    if len(asns) == 1:
        return asns[0]
    orgs = {as2org[asn] for asn in asns}
    if len(orgs) == 1:
        return asns[0]
    for asn in asns:
        if all(asn in bgp.cone[other] for other in asns if other != asn):
            return asn
    mins = max_num(asns, key=lambda x: -bgp.conesize[x])
    if mins:
        return mins[0]
    return asns[0]


def read_prefixes(filename: str):
    prefixes = []
    try:
        with File2(filename) as f:
            for line in f:
                prefix, asn_s = line.split()
                prefixes.append((prefix, asn_s))
    except ValueError:
        with File2(filename, 'rt') as f:
            for line in f:
                if line[0] == '#':
                    continue
                addr, prefixlen, asn_s = line.split()
                asns = [asn for asn in map(int, asn_s.split('_')) if valid(asn)]
                if not asns:
                    continue
                asn_s = '_'.join(str(asn) for asn in asns)
                prefixlen = int(prefixlen)
                if ':' in addr:
                    if prefixlen > 48:
                        continue
                else:
                    if prefixlen > 24:
                        continue
                prefix = '{}/{}'.format(addr, prefixlen)
                prefixes.append((prefix, asn_s))
    return prefixes


def main():
    parser = ArgumentParser()
    parser.add_argument('-p', '--prefixes', required=True, help='RIB prefix-to-AS file in the standard CAIDA format.')
    parser.add_argument('-P', '--peeringdb', required=True, help='PeeringDB json file.')
    parser.add_argument('-r', '--rir', required=True, help='RIR prefix-to-AS file.')
    parser.add_argument('-R', '--rels', required=True, help='AS relationship file in the standard CAIDA format.')
    parser.add_argument('-c', '--cone', required=True, help='AS customer cone file in the standard CAIDA format.')
    parser.add_argument('-o', '--output', type=FileType('w'), default='-', help='Output file.')
    parser.add_argument('-a', '--as2org', required=True, help='AS-to-Org mappings in the standard CAIDA format.')
    args = parser.parse_args()

    ixp = PeeringDB(args.peeringdb)
    bgp = BGP(args.rels, args.cone)
    as2org = AS2Org(args.as2org)
    prefixes = read_prefixes(args.prefixes)
    rir = read_prefixes(args.rir)
    table = create_table(prefixes, ixp, rir, bgp, as2org)
    for node in table.nodes():
        args.output.write('{} {}\n'.format(node.network, node.asn))


if __name__ == '__main__':
    main()
