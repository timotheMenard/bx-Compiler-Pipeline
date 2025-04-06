from bx2tac import bx2tac
from tac2x64 import tac2x64
from tac_cfopt import tac_cfopt

import subprocess
import getopt
import sys

"""
.
Manages all the scripts
"""
if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], '', [])
    file = args[0]

    if file.endswith('.bx'):
        filename = file[:-3]
    else:
        print(f'{file} does not end in .bx')
        sys.exit(1)

    with open(file, 'r') as f:
        code = f.read()

    tac_file = bx2tac(code, file)
    tac_fn = filename + '.tac.json'

    with open(tac_fn, 'w') as f:
        f.write(tac_file)

    tac_optimize_file = tac_cfopt(tac_fn)

    x64_file = tac2x64(filename + ".tac_opt.json")
    x64_name = filename + '.s'

    f_out = open(x64_name, 'w')
    for i in x64_file:
        f_out.write(i + '\n')
    f_out.close()











