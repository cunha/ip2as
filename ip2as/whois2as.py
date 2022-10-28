import re
import sys
from argparse import ArgumentParser
from collections import defaultdict, Counter
from multiprocessing import Pool

from file2 import fopen
from pb_amarder import Progress


def parse_whois(filename):
    elems = defaultdict(list)
    item = {}
    first = None
    with fopen(filename, encoding = "ISO-8859-1") as f:
        for line in f:
            if line.startswith('#') or line.startswith('%'):
                continue
            line = line.strip()
            if not line:
                if item:
                    elems[first].append(tuple(item.items()))
                    item = {}
                    first = None
                continue
            key, _, value = line.partition(':')
            if not value:
                continue
            value = value.strip()
            if key in item:
                item[key] += '\n' + value
            else:
                item[key] = value
            if first is None:
                first = key
    return elems['route']

def parse_whois_parallel(files, poolsize):
    elems = Counter()
    poolsize = min(poolsize, len(files))
    with Pool(poolsize) as pool:
        pb = Progress(len(files))
        for nelems in pb.iterator(pool.imap_unordered(parse_whois, files)):
            elems.update(nelems)
    return elems

def main():
    parser = ArgumentParser()
    parser.add_argument('-f', '--files')
    parser.add_argument('-F', '--files-list', nargs='*')
    parser.add_argument('-o', '--outfile')
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

    elems = parse_whois_parallel(files, args.poolsize)
    reg = re.compile(r'(\d+)')
    prefs = defaultdict(set)
    for item in elems:
        item = dict(item)
        origin = item['origin']
        m = reg.search(origin)
        if m:
            asn = m.group(1)
            prefs[item['route']].add(asn)
    f = fopen(args.outfile, 'wt') if args.outfile != '-' else sys.stdout
    try:
        for pref, asns in prefs.items():
            net, _, plen = pref.partition('/')
            f.write('{}\t{}\t{}\n'.format(net, plen, '_'.join(asns)))
    finally:
        f.close()
