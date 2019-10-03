"""
python3 scripts/sweep.py --dry_run --model_cache_dir=/users/arc/model_cache_dir --n_trials=3 --n_parallel_runs=32
 --results_dir=/users/arc/vol/results/ --cc cubic --rtt 10 20 50 100 --thr 1 2 4 8 100 --frac 1 2 10 --time=120 --name=2min_16_par | parallel -k -j1  --halt now,fail=1 --ungroup
"""
import os
import argparse
import subprocess
import threading
import queue
import time
import _thread

parser = argparse.ArgumentParser()
parser.add_argument('--name',
                    required=True,
                    type=str,
                    help='Give name to the sweep')
parser.add_argument('--n_trials', default=1, type=int)
parser.add_argument('--n_parallel_runs', default=1, type=int)
parser.add_argument('--results_dir', default='/home/arc/results/', type=str)
parser.add_argument('--rtt', type=int, nargs='+', default=None)
parser.add_argument('--frac', type=str, nargs='+', default=None)
parser.add_argument('--thr', type=int, nargs='+', default=None)
parser.add_argument('--cc', type=str, nargs='+', default=None)
parser.add_argument('--time', type=int, default=60)
parser.add_argument('--model_cache_dir',
                    type=str,
                    default='./model_cache_dir/')
parser.add_argument('--dry_run', dest='dry_run', action='store_true')
parser.add_argument('remaining_args', nargs='*')
args = parser.parse_args()


def get_cmd(trial_id, name, thr, rtt, time, action_port, frames_port,
            queue_size_factor):

  cmd = 'python3 scripts/run_exp.py -n={name} --model_cache_dir={model_cache_dir}\
  --results_dir={results_dir} --rtt={rtt} --time={time} --thr={thr} --dump_video\
  --action_port={action_port} --frames_port={frames_port} --queue_size_factor={queue_size_factor} \
  -- {remain_args} '.format(name=name,
                            model_cache_dir=args.model_cache_dir,
                            results_dir=os.path.join(args.results_dir,
                                                     args.name, str(trial_id)),
                            rtt=rtt,
                            time=time,
                            thr=thr,
                            action_port=action_port,
                            frames_port=frames_port,
                            queue_size_factor=queue_size_factor,
                            remain_args=' '.join(args.remaining_args))

  return cmd


ERROR = False


def run_cmds_from_q(
    q,
    lock=threading.Lock(),
):
  global ERROR
  while True:
    cmd = q.get()
    if cmd is None:
      return
    with lock:
      print(cmd)

    if args.dry_run:
      ret = 0
    else:
      # ret = os.system(cmd)
      process = subprocess.Popen(cmd,
                                 stderr=sys.stderr,
                                 stdout=sys.stdout,
                                 shell=True)
      while True:
        with lock:
          if ERROR:
            process.kill()
            return
        ret = process.poll()
        if ret is None:
          time.sleep(.1)
        else:
          break

    if ret != 0:
      ERROR = True
      print('************** Exception **************')
      print('non-zero Return code received when running %s' % cmd)
      time.sleep(1)
      _thread.interrupt_main()
      return


def main():
  q = queue.Queue(args.n_parallel_runs)
  threads = [
      threading.Thread(target=run_cmds_from_q, args=(q, ))
      for _ in range(args.n_parallel_runs)
  ]
  for t in threads:
    t.daemon = True
    t.start()

  action_port = 10000
  frames_port = 10001
  for cc in args.cc:
    if args.dry_run:
      print(
          'echo arc | sudo -S bash -c "echo %s > /proc/sys/net/ipv4/tcp_congestion_control"'
          % cc)
    else:
      assert os.system(
          'echo arc | sudo -S bash -c "echo %s > /proc/sys/net/ipv4/tcp_congestion_control"'
          % cc) == 0
    for trial_id in range(args.n_trials):
      for rtt in args.rtt:
        for thr in args.thr:
          for frac in args.frac:
            name = "{cc}_rtt_{rtt}_thr_{thr}_frac_{frac}".format(cc=cc,
                                                                 rtt=rtt,
                                                                 thr=thr,
                                                                 frac=frac)
            q.put(
                get_cmd(trial_id, name, thr, rtt, args.time, action_port,
                        frames_port, frac))
            action_port += 2
            frames_port += 2

    # wait for all commands to exit
    while not q.empty():
      time.sleep(1)


if __name__ == '__main__':
  main()
