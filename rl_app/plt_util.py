import numpy as np


def parse_mahimahi_out(fname, type='Ingress', ms_per_bin=50):
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
    raise Exception('Unknown argument')

  with open(fname) as f:
    for line in f.readlines():
      if not line.startswith('#'):
        if symbol in line:
          l = line.split()

          while int(l[0]) - cur_ms > ms_per_bin:
            byte_quantas.append(bytes_accum)
            cur_ms += ms_per_bin
            bytes_accum = 0

          bytes_accum += float(l[2])

  y = [b * 8. / ms_per_bin / 1e3 for b in byte_quantas]
  x = np.arange(0, len(y) * ms_per_bin, ms_per_bin) / 1e3
  return x, y


def get_q_size_mahimahi(fname, ms_per_bin=50):
  cur_ms = 0
  queue_size = []
  bytes_accum = 0

  with open(fname) as f:
    for line in f.readlines():
      if not line.startswith('#'):
        if '+' in line or '-' in line:
          l = line.split()

          while int(l[0]) - cur_ms > ms_per_bin:
            queue_size.append(bytes_accum)
            cur_ms += ms_per_bin

          if '+' in line:
            bytes_accum += float(l[2])
          else:
            bytes_accum -= float(l[2])

  y = [q / 1500.0 for q in queue_size]
  x = np.arange(0, len(y) * ms_per_bin, ms_per_bin) / 1e3
  return x, y


def parse_ping(fname):
  ret = []
  for line in open(fname).readlines():
    if 'bytes from' not in line:
      continue
    try:
      rtt = line.split(' ')[-2]
      rtt = rtt.split('=')[1]
      rtt = float(rtt)
      ret.append(rtt)
    except:
      break
  return ret
