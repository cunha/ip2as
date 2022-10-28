from argparse import ArgumentParser
from collections import Counter, defaultdict
from multiprocessing import Pool
from subprocess import Popen, PIPE
from typing import Optional, Set

from file2 import fopen
from pb_amarder import Progress

import ip2as.reserved as rv

_reserved: Optional[Set[int]] = None

def valid(asn):
    if asn != 23456 and 0 < asn < 64496 or 131071 < asn < 400000:
        if _reserved is not None:
            return asn not in _reserved
        return True
    return False

def parse_set(asns):
    newasns = []
    for asn in asns[1:-1].split(','):
        asn = int(asn)
        if valid(asn):
            newasns.append(str(asn))
    return newasns

def read(filename):
    counter = Counter()
    cmd = 'bgpreader -d singlefile -o rib-file={} -w 0,2147483648'.format(filename)
    reader = Popen(cmd, shell=True, stdout=PIPE, universal_newlines=True)
    for line in reader.stdout:
        splits = line.split('|')
        if splits[1] == 'R':
            dumptype, elemtype, _, _, _, _, _, _, _, prefix, _, aspath, _, _, _, _ = splits
            if elemtype == 'R':
                aspath = aspath.split()
                for asn in reversed(aspath):
                    if '{' in asn:
                        asns = parse_set(asn)
                        if asns:
                            for asn in asns:
                                counter[prefix, asn] += 1
                            break
                    else:
                        asn = int(asn)
                        if valid(asn):
                            counter[prefix, asn] += 1
                            break
    return counter

def read_parallel(files, poolsize, reserved):
    global _reserved
    _reserved = reserved
    c = Counter()
    pb = Progress(len(files), callback=lambda: '{:,d}'.format(len(c)))
    with Pool(poolsize) as pool:
        for nc in pb.iterator(pool.imap_unordered(read, files)):
            c.update(nc)
    return c

def group_pref(prefcounter):
    d = defaultdict(list)
    for (pref, asn), _ in prefcounter.most_common():
        d[pref].append(asn)
    return d

def write(prefs, outfile):
    with fopen(outfile, 'wt') as f:
        for pref, asns in prefs.items():
            if asns:
                net, _, plen = pref.rpartition('/')
                asns = '_'.join(map(str, asns))
                f.write('{}\t{}\t{}\n'.format(net, plen, asns))

def main():
    parser = ArgumentParser()
    parser.add_argument('-f', '--files')
    parser.add_argument('-F', '--files-list', nargs='*')
    parser.add_argument('-o', '--outfile')
    parser.add_argument('-r', '--reserved')
    parser.add_argument('-p', '--poolsize', type=int, default=25)
    args = parser.parse_args()

    files = []
    if args.files:
        with fopen(args.files) as f:
            for line in f:
                line = line.strip()
                if line:
                    files.append(line)
    if args.files_list:
        files.extend(args.files_list)

    if args.reserved:
        reserved = set()
        with fopen(args.reserved) as f:
            for line in f:
                line = line.strip()
                asn = int(line)
                reserved.add(asn)
    else:
        reserved = rv.get_reserved()

    poolsize = min(args.poolsize, len(files))
    prefcounter = read_parallel(files, poolsize, reserved)
    prefs = group_pref(prefcounter)
    write(prefs, args.outfile)
