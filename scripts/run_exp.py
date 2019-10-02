"""
  Example invokation:
  python scripts/run_exp.py -- --model_cache_dir=/home/arc/model_cache_dir/ -n test --results_dir=/tmp/base --rtt=10 --time=10 --thr=4
"""
import threading
import argparse
import os
import sys
from absl import app

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
                    default=2.,
                    help='queue size = this factor * BDP_min')
parser.add_argument('--env_name', type=str, default='Breakout-v0')
parser.add_argument('--model_cache_dir',
                    type=str,
                    default='./model_cache_dir/')
parser.add_argument('--disable_mahimahi',
                    dest='disable_mahimahi',
                    action='store_true')
parser.add_argument('--dry_run', dest='dry_run', action='store_true')


def run_cmd(cmd, blocking=True, dry_run=False):

  def _run_cmd():
    if dry_run:
      print(cmd)
      ret = 0
    else:
      ret = os.system(cmd)

    if ret > 0:
      raise Exception('Failure executing command %s' % cmd)
    return ret

  if blocking:
    return _run_cmd()
  else:
    t = threading.Thread(target=_run_cmd)
    t.start()
    return t


# def set_cc_algorithm(cc, dry_run):
#   run_cmd(
#       'sudo bash -c "echo %s > /proc/sys/net/ipc4/tcp_congestion_control"' %
#       cc,
#       dry_run=dry_run)


def get_mahimahi_stub(args):
  if args.rtt % 2 != 0:
    raise Exception('Specify even number for rtt value')

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
      queue_size=int(args.queue_size_factor * float(args.thr) * args.rtt *
                     1e3 / MTU_BYTES))
  cmd += ' <<EOF\n{cmd}\nEOF'
  return cmd


def get_server_cmd(args):
  cmd = 'export PYTHONPATH="$PYTHONPATH:%s";' % os.getcwd()
  cmd += 'python3 rl_app/agent_server.py -- --env_name=%s' % args.env_name
  cmd += ' --frames_port=10000 --action_port=10001 --gameover_port=10002 --model_fname=%s/%s.npz' % (
      args.model_cache_dir, args.env_name)
  return cmd


def get_client_cmd(args, disable_mahimahi):
  dump_dir = os.path.join(args.results_dir, args.name, 'game_results')
  cmd = 'export PYTHONPATH="$PYTHONPATH:%s";' % os.getcwd()
  cmd += 'python3 rl_app/gameplay.py -- --frameskip=3 --sps=30 --env_name=%s' % args.env_name
  if disable_mahimahi:
    cmd += ' --server_ip=127.0.0.1'
  else:
    cmd += " --server_ip=`echo '$MAHIMAHI_BASE'`"
  cmd += ' --frames_port=10000 --action_port=10001 --gameover_port=10002 --results_dir=%s ' % dump_dir
  cmd += ' --time=%d' % args.time
  if args.render:
    cmd += ' --render'
  if args.dump_video:
    cmd += ' --dump_video'
  return cmd


def main(argv):
  args = parser.parse_args(argv[1:])
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

  # set_cc_algorithm(args.cc, args.dry_run)
  stub = get_mahimahi_stub(args)
  cli_cmd = get_client_cmd(args, args.disable_mahimahi)
  if not args.disable_mahimahi:
    cli_cmd = stub.format(cmd=cli_cmd)
  t1 = run_cmd(cli_cmd, blocking=False, dry_run=args.dry_run)
  t2 = run_cmd(get_server_cmd(args), blocking=False, dry_run=args.dry_run)
  t1.join()
  t2.join()


if __name__ == '__main__':
  app.run(main)
