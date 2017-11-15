# -*- coding: utf-8 -*-
__author__ = 'IPPM RAS: https://github.com/IDMIPPM/'


import random
import sys
from eco_core import ic


if __name__ == '__main__':
    seeds = [125034, 417269]
    seed = random.choice(seeds)
    random.seed(seed)

    if len(sys.argv) == 6:
        log = None
        F = sys.argv[1]
        G = sys.argv[2]
        weights = sys.argv[3]
        patch_file = sys.argv[4]
        out_file = sys.argv[5]
    else:
        print('Wrong number of parameters: {}'.format(len(sys.argv)))
        print('Usage: python eco_flow.py <F.v> <G.v> <weight.txt> <patch.v> <out.v>')
        exit()

    print('PATHS INFO')
    print('F file:', F)
    print('G file:', G)
    print('weight file:', weights)
    print('patch.v file:', patch_file)
    print('out.v file:', out_file)
    ic(F, G, weights, patch_file, out_file, 1800)
