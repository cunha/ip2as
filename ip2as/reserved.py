import sys
from argparse import ArgumentParser

from bs4 import BeautifulSoup
import requests
from file2 import fopen


def get_reserved():
    r = requests.get('https://bgp.potaroo.net/cidr/autnums.html')
    b = BeautifulSoup(r.text, features='lxml')
    lines = [l.partition(' ') for l in b.pre.text.splitlines() if l.strip()]
    asns = {int(k[2:]): v.strip() for k, _, v in lines}
    reserved = {asn for asn, name in asns.items() if name == '-Reserved AS-, ZZ'}
    return reserved

def main():
    parser = ArgumentParser()
    parser.add_argument('-o', '--outfile', default='-')
    args = parser.parse_args()
    reserved = get_reserved()
    f = fopen(args.outfile, 'wt') if args.outfile != '-' else sys.stdout
    f.writelines('{}\n'.format(a) for a in sorted(reserved))