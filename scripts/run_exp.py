"""
  Example invokation:
  python3 scripts/run_exp.py --model_cache_dir=/home/arc/model_cache_dir/ -n test --results_dir=/tmp/base --rtt=10 --time=10 --thr=4 --action_port=10000 --frames_port=10001 --dump_video
"""
import argparse
import numpy as np
import os
import subprocess
import sys
import threading

from rl_app.plt_util import parse_mahimahi_out, parse_ping, get_q_size_mahimahi
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.use('Agg')

INF_TRACE = 'mm_traces/100mbps.log'
MAHIMAHI_BASE = '100.64.0.4'
MTU_BYTES = 1500

parser = argparse.ArgumentParser()
parser.add_argument('--render', dest='render', action='store_true')
parser.add_argument('--dump_video', dest='dump_video', action='store_true')
parser.add_argument('--name',
                    '-n',
                    type=str,
                    required=True,
                    help='Assign a name to this experiment.')
parser.add_argument('--results_dir', default='results/', type=str)
# parser.add_argument('--cc', default='cubic', type=str)
parser.add_argument('-r', '--rtt', type=int, help='min rtt in milliseconds.')
parser.add_argument('--sps', type=int, default=90)
parser.add_argument('--time',
                    type=int,
                    default=120,
                    help='experiment time in seconds')
parser.add_argument('-t',
                    '--thr',
                    type=str,
                    help='Bottleneck Throughput in Mbps.')
parser.add_argument('--queue_size_factor',
                    type=float,
                    default=None,
                    help='queue size = this factor * BDP_min')
parser.add_argument('--queue_size', type=int, default=10)
parser.add_argument('--env_name', type=str, default='Breakout-v0')
parser.add_argument('--model_cache_dir',
                    type=str,
                    default='./model_cache_dir/')
parser.add_argument('--disable_mahimahi',
                    dest='disable_mahimahi',
                    action='store_true')
parser.add_argument('--dry_run', dest='dry_run', action='store_true')
parser.add_argument('--action_port', type=int, default=10000)
parser.add_argument('--frames_port', type=int, default=10001)
parser.add_argument('--use_iperf', dest='use_iperf', action='store_true')
parser.add_argument('remaining_args', nargs='*')
args = parser.parse_args()


def run_cmd(cmd, blocking=True, dry_run=False):

  def _run_cmd():
    if dry_run:
      print(cmd)
      return 0
    else:
      return os.system(cmd)

  if blocking:
    return _run_cmd()
  else:
    t = threading.Thread(target=_run_cmd)
    t.daemon = True
    t.start()
    return t


def subprocess_cmd(command, dry_run=False):
  if dry_run:
    print(command)
    return None
  else:
    process = subprocess.Popen(command,
                               stdout=sys.stdout,
                               stderr=sys.stderr,
                               shell=True)
    return process


def get_mahimahi_stub(args):
  if args.rtt % 2 != 0:
    raise Exception('Specify even number for rtt value')
  if args.queue_size_factor is not None:
    raise Exception('queue_size-factor has been removed')

  thr_file = './mm_traces/%smbps.log' % args.thr
  if not os.path.isfile(thr_file):
    raise Exception(
        'Throughput file not found at %s. Check mm_traces/generate_const_mahimahi_traces.sh'
        % thr_file)

  uplink_log = os.path.join(args.results_dir, args.name, 'mm_uplink.log')
  downlink_log = os.path.join(args.results_dir, args.name, 'mm_downlink.log')

  cmd = 'mm-delay {delay} mm-link --uplink-queue=droptail --uplink-queue-args="packets={queue_size}" \
  {uplink_thr} {downlink_thr} --uplink-log={uplink_log} --downlink-log={downlink_log}'.format(
      delay=int(args.rtt / 2),
      uplink_thr=thr_file,
      downlink_thr=INF_TRACE,
      uplink_log=uplink_log,
      downlink_log=downlink_log,
      queue_size=args.queue_size)
  cmd += ' <<EOF\n{cmd}\nEOF'
  return cmd


def get_server_cmd(args):
  cmd = 'export PYTHONPATH="$PYTHONPATH:%s";' % os.getcwd()
  cmd += 'exec python3 rl_app/agent_server.py -- --env_name=%s' % args.env_name
  cmd += ' --frames_port=%d --action_port=%d --model_fname=%s/%s.npz' % (
      args.frames_port, args.action_port, args.model_cache_dir, args.env_name)
  cmd += ' --time=%d' % (args.time + 20)
  return cmd


def get_client_cmd(args, disable_mahimahi):
  dump_dir = os.path.join(args.results_dir, args.name, 'game_results')
  cmd = 'export PYTHONPATH="$PYTHONPATH:%s";' % os.getcwd()
  cmd += 'python3 rl_app/gameplay.py -- --frameskip=3 --sps=%d --env_name=%s' % (
      args.sps, args.env_name)
  if disable_mahimahi:
    cmd += ' --server_ip=127.0.0.1'
  else:
    cmd += " --server_ip=`echo '$MAHIMAHI_BASE'`"
  cmd += ' --frames_port=%d --action_port=%d --results_dir=%s ' % (
      args.frames_port, args.action_port, dump_dir)
  cmd += ' --time=%d' % args.time
  if args.render:
    cmd += ' --render'
  if args.dump_video:
    cmd += ' --dump_video'
  if args.use_iperf:
    cmd += ' --use_iperf'

  if args.remaining_args:
    cmd += ' '
    cmd += (' '.join(args.remaining_args))

  return cmd


def plot_mahimahi(args):
  plt.figure()
  x_cap, y_cap = parse_mahimahi_out(os.path.join(args.results_dir, args.name,
                                                 'mm_uplink.log'),
                                    'Capacity',
                                    ms_per_bin=200)
  plt.plot(x_cap, y_cap, label='Capacity-%.3f' % np.mean(y_cap[20:]))
  x_ing, y_ing = parse_mahimahi_out(os.path.join(args.results_dir, args.name,
                                                 'mm_uplink.log'),
                                    'Ingress',
                                    ms_per_bin=200)
  plt.plot(x_ing, y_ing, label='Ingress-%.3f' % np.mean(y_ing[20:]))
  x_eng, y_eng = parse_mahimahi_out(os.path.join(args.results_dir, args.name,
                                                 'mm_uplink.log'),
                                    'Egress',
                                    ms_per_bin=200)
  plt.plot(x_eng, y_eng, label='Egress-%.3f' % np.mean(y_eng[20:]))
  plt.xlabel('sec')
  plt.ylabel('Mbps')
  plt.legend()
  plt.savefig(
      fname=os.path.join(args.results_dir, args.name, 'throughput.png'))


def plot_qsize(args):
  x, y = get_q_size_mahimahi(os.path.join(args.results_dir, args.name,
                                          'mm_uplink.log'),
                             ms_per_bin=200)
  plt.figure()
  plt.plot(x, y, label='Qsize-%.3f' % np.mean(y[20:]))
  plt.xlabel('sec')
  plt.xlabel('sec')
  plt.ylabel('# packets')
  plt.legend()
  plt.savefig(fname=os.path.join(args.results_dir, args.name, 'qsize.png'))


def main():
  if args.disable_mahimahi:
    print('****************')
    print('WARNING: Disabling mahimahi')
    print('****************')

  if not args.dry_run:
    # setup results dir
    # enable this for safer checks
    # if os.path.exists(os.path.join(args.results_dir, args.name)):
    #   raise Exception('results dir %s already exists' %
    #                   os.path.join(args.results_dir, args.name))
    os.system('mkdir -p %s' % os.path.join(args.results_dir, args.name))

  stub = get_mahimahi_stub(args)
  cli_cmd = get_client_cmd(args, args.disable_mahimahi)
  if not args.disable_mahimahi:
    cli_cmd = stub.format(cmd=cli_cmd)
  server_cmd = get_server_cmd(args)
  process = subprocess_cmd(server_cmd, dry_run=args.dry_run)
  ret = run_cmd(cli_cmd, blocking=True, dry_run=args.dry_run)
  if ret == 0 and not args.dry_run:
    plot_mahimahi(args)
    plot_qsize(args)

  ret2 = 0
  if not args.dry_run:
    ret2 = process.poll()
    if ret2 is None:
      process.kill()
      ret2 = 0

  if ret != 0:
    raise Exception('Failure executing command %s' % cli_cmd)

  if ret2 != 0:
    raise Exception('Failure executing command %s' % server_cmd)


if __name__ == '__main__':
  main()
