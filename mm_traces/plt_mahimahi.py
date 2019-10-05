import sys
import os
import json
import numpy as np
import matplotlib as mpl
from itertools import cycle
import argparse
# Need this to plot bandwidth without an X server
mpl.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--ms-per-bin', type=int, default=500)
parser.add_argument(
    '--mm-log-files',
    type=str,
    nargs='+',
    required=True,
    help='The first file would be used to infer bottleneck capacity')
parser.add_argument(
    '--names',
    type=str,
    nargs='+',
    default=None,
    help='Labels to use for plot corresponding to each of the above log file')
parser.add_argument('--out-dir',
                    type=str,
                    required=True,
                    help='Outputs figures to this dir')
args = parser.parse_args()

if args.names is None:
  args.names = args.mm_log_files
else:
  assert len(args.names) == len(args.mm_log_files)


def parse_mahimahi_out(fname, type):
  cur_ms = 0
  byte_quantas = []
  bytes_accum = 0

  if type == 'Egress':
    symbol = '-'
  elif type == 'Ingress':
    symbol = '+'
  elif type == 'Capacity':
    symbol = '#'
  else:
    print 'Unknown argument'
    sys.exit(1)

  with open(fname) as f:
    for line in f.readlines():
      if not line.startswith('#'):
        if symbol in line:
          l = line.split()

          while int(l[0]) - cur_ms > args.ms_per_bin:
            byte_quantas.append(bytes_accum)
            cur_ms += args.ms_per_bin
            bytes_accum = 0

          bytes_accum += float(l[2])

  y = [b * 8. / args.ms_per_bin / 1e3 for b in byte_quantas]
  x = np.arange(0, len(y) * args.ms_per_bin, args.ms_per_bin) / 1e3
  return x, y


def get_q_size_mahimahi(fname):
  cur_ms = 0
  queue_size = []
  bytes_accum = 0

  with open(fname) as f:
    for line in f.readlines():
      if not line.startswith('#'):
        if '+' in line or '-' in line:
          l = line.split()

          while int(l[0]) - cur_ms > args.ms_per_bin:
            queue_size.append(bytes_accum)
            cur_ms += args.ms_per_bin

          if '+' in line:
            bytes_accum += float(l[2])
          else:
            bytes_accum -= float(l[2])

  y = [q / 1500.0 for q in queue_size]
  x = np.arange(0, len(y) * args.ms_per_bin, args.ms_per_bin) / 1e3
  return x, y


# Visualizing Egress doesn't make much sense for our situation
for t in ['Ingress']:
  plt.figure()

  f = args.mm_log_files[0]
  x, y = parse_mahimahi_out(f, 'Capacity')
  plt.plot(x, y, label='Capacity')

  for name, f in zip(args.names, args.mm_log_files):
    x, y = parse_mahimahi_out(f, t)
    plt.plot(x, y, label=name)

  plt.ylabel('%s Throughput (Mbps)' % t)
  plt.xlabel('Time (seconds)')
  plt.legend()

  plt.savefig('%s/%s.png' % (args.out_dir, t))
