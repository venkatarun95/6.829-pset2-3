"""
python3 scripts/sweep.py --dry_run --model_cache_dir=/users/arc/model_cache_dir --n_trials=3
 --results_dir=/users/arc/vol/results/ --cc cubic --rtt 10 20 50 100 --thr 1 2 4 8 100 --queue 1 2 10 --time=120 --name=2min_16_par | parallel -k -j1  --halt now,fail=1 --ungroup
"""
import os
import math
import argparse
import subprocess
import threading
import sys
import queue
import time
import _thread

parser = argparse.ArgumentParser()
parser.add_argument('--name',
                    required=True,
                    type=str,
                    help='Give name to the sweep')
parser.add_argument('--n_trials', default=1, type=int)
parser.add_argument('--results_dir', default='/home/arc/results/', type=str)
parser.add_argument('--rtt', type=int, nargs='+', default=None)
parser.add_argument('--queue', type=str, nargs='+', default=None)
parser.add_argument('--thr', type=str, nargs='+', default=None)
parser.add_argument('--cc', type=str, nargs='+', default=None)
parser.add_argument('--time', type=int, default=60)
parser.add_argument('--sps', type=int, nargs='+', default=90)
parser.add_argument('--model_cache_dir',
                    type=str,
                    default='./model_cache_dir/')
parser.add_argument('--dry_run', dest='dry_run', action='store_true')
parser.add_argument('remaining_args', nargs='*')
args = parser.parse_args()


def get_cmd(trial_id, name, thr, rtt, time, action_port, frames_port,
            queue_size, sps):

  cmd = 'python3 scripts/run_exp.py -n={name} --model_cache_dir={model_cache_dir}\
  --results_dir={results_dir} --rtt={rtt} --time={time} --thr={thr} --dump_video\
  --action_port={action_port} --frames_port={frames_port} --queue_size={queue_size}\
  --sps={sps} \
  -- {remain_args} '.format(name=name,
                            model_cache_dir=args.model_cache_dir,
                            results_dir=os.path.join(args.results_dir,
                                                     args.name, str(trial_id)),
                            rtt=rtt,
                            time=time,
                            thr=thr,
                            action_port=action_port,
                            frames_port=frames_port,
                            queue_size=queue_size,
                            sps=sps,
                            remain_args=' '.join(args.remaining_args))
  return cmd


ERROR = False


def kill_ccp():
  cmd = 'sudo pkill -f cc.py;'
  if args.dry_run:
    print(cmd)
  else:
    os.system(cmd)


def start_ccp(cwnd):
  kill_ccp()
  cmd = 'sudo python3 cc.py --cwnd=%d' % cwnd
  if args.dry_run:
    cmd += '& '
    print(cmd)
    return 0
  else:
    print('Starting cmd ', cmd)
    proc = subprocess.Popen(cmd,
                            stderr=sys.stderr,
                            stdout=sys.stdout,
                            shell=True)
    time.sleep(2)
    return proc


def run_cmd_to_success(cmd):
  if args.dry_run:
    print(cmd)
    ret = 0
  else:
    ret = os.system(cmd)
    assert ret == 0
  return ret


def main():
  action_port = 10000
  frames_port = 10001
  for cc in args.cc:
    if cc != 'ccp':
      kill_ccp()
    if args.dry_run:
      print(
          'sudo -S bash -c "echo %s > /proc/sys/net/ipv4/tcp_congestion_control"'
          % cc)
    else:
      assert os.system(
          'sudo -S bash -c "echo %s > /proc/sys/net/ipv4/tcp_congestion_control"'
          % cc) == 0

    for trial_id in range(args.n_trials):
      for sps in args.sps:
        for rtt in args.rtt:
          for thr in args.thr:
            if cc == 'ccp':
              delay = rtt + (1500.0 * 8.0 / float(thr) / 1e3)
              cwnd = 1500 * math.ceil(float(thr) * delay * 1e3 / 8.0 / 1500.0)
              cwnd = int(cwnd)
              ccp_proc = start_ccp(cwnd)
            for queue in args.queue:
              name = "{cc}_rtt_{rtt}_thr_{thr}_queue_{queue}_sps_{sps}".format(
                  cc=cc, rtt=rtt, thr=thr, queue=queue, sps=sps)
              cmd = get_cmd(trial_id, name, thr, rtt, args.time, action_port,
                            frames_port, queue, sps)
              run_cmd_to_success(cmd)
              action_port += 2
              frames_port += 2


if __name__ == '__main__':
  main()
