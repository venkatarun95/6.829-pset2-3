import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-n', type=int, default=None)
parser.add_argument('-d', type=int, default=1)
args = parser.parse_args()


def output_mahimahi(n, d):
  num_lines = n
  time = d * 12
  l = []
  for i in range(num_lines):
    l.append(int((1 + i) * time / float(num_lines)))

  return '\n'.join(map(str, l))


print(output_mahimahi(args.n, args.d))
