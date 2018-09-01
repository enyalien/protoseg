#!/usr/bin/env python

import os
import sys

from protoseg import Config
from protoseg import backends

datapath = 'data/'
resultspath = 'results/'

def help():
    return "Config file parameter missing. Run like: python train.py /path/to/config.yml"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(help())
        sys.exit(1)
    configs = Config(sys.argv[1])    
    for run in configs:
        print("Run: ", run)
        resultpath = os.path.join(resultspath, run)
        if not os.path.exists(resultpath):
            os.makedirs(resultpath)
        configs.save(resultpath + '/config.yml')
        backend = backends.get_backend(configs.get()['backend'])()
        backend.train()
    sys.exit(0)