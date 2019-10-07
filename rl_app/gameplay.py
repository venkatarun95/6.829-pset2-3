import argparse
import json
import subprocess
import sys
import os
import threading
import time

import cv2
import gym
import numpy as np
import queue
from absl import app
from rl_app.atari_wrapper import (FireResetEnv, FrameStack, LimitLength,
                                  MapState, Monitor)
from rl_app.network.network import Receiver, Sender
from rl_app.util import Clock, put_overwrite
from rl_app.plt_util import parse_mahimahi_out, parse_ping
from tensorpack import *
from collections import namedtuple
from rl_app.network.serializer import pa_serialize
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.use('Agg')

parser = argparse.ArgumentParser()
parser.add_argument('--env_name', type=str, required=True)
parser.add_argument('--server_ip', type=str, required=True)
parser.add_argument('--frames_port', type=int, required=True)
parser.add_argument('--action_port', type=int, required=True)
parser.add_argument('--sps', type=int, default=20)
parser.add_argument('--frameskip', type=int, default=3)
parser.add_argument('--render', dest='render', action='store_true')
parser.add_argument('--dump_video', dest='dump_video', action='store_true')
parser.add_argument('--results_dir',
                    type=str,
                    required=True,
                    help='Dump the video results here (optionally video)')
parser.add_argument('--time', type=int, default=60)
parser.add_argument('--use_latest_act_as_default',
                    dest='use_latest_act_as_default',
                    action='store_true')
parser.add_argument('--use_iperf', dest='use_iperf', action='store_true')
parser.add_argument('--use_', dest='use_iperf', action='store_true')
parser.add_argument('--verbose', dest='verbose', action='store_true')

NEW_GAME_PENALTY = 10
IMAGE_SIZE = (84, 84)
FRAME_HISTORY = 4
GameStat = namedtuple(
    'GameStat', ['is_skip_action', 'lag_n_frames', 'lag_time', 'frame_size'])


class GamePlay:

  def __init__(self,
               env_name,
               sps,
               agent_server_ip,
               frames_port,
               action_port,
               time_limit,
               render=False,
               results_dir=None,
               dump_video=None,
               frameskip=1,
               use_latest_act_as_default=False,
               use_iperf=False,
               verbose=False):

    self.max_steps = sps * time_limit
    self.sps = sps
    self.time_limit = time_limit
    self.results_dir = results_dir
    os.system('mkdir -p %s' % self.results_dir)
    self._step_sleep_time = 1.0 / sps
    self.server_ip = agent_server_ip
    self.frames_port = frames_port
    self.action_port = action_port
    self.frameskip = frameskip
    self.env_name = env_name
    self.dump_video = dump_video
    self.render = render
    self.use_latest_act_as_default = use_latest_act_as_default
    if use_latest_act_as_default:
      raise Exception('Not supported for now..')
    self.lock = threading.Lock()
    self._latest_action = None
    self._frames_q = queue.Queue(1)
    self._game_stats = []
    self.game_id = None
    self.skip_count = None
    self.verbose = verbose
    self.use_iperf = use_iperf

  def start(self):
    self._frames_socket = Sender(host=self.server_ip,
                                 port=self.frames_port,
                                 bind=False,
                                 verbose=self.verbose)
    self._actions_socket = Receiver(host=self.server_ip,
                                    port=self.action_port,
                                    bind=False,
                                    verbose=self.verbose)
    self._frames_socket.start_loop(self.push_frames, blocking=False)
    self._actions_socket.start_loop(self._receive_actions, blocking=False)
    proc = self._start_ping()
    self._start_cwnd_monitor()
    if self.use_iperf:
      proc2 = self._start_iperf_client()

    self._process()

    if proc.poll() is None:
      proc.kill()

    if self.use_iperf:
      if proc2.poll() is None:
        proc2.kill()

    self._plot_results()

  def _make_env(self, env_number=0):
    env = gym.make(self.env_name, frameskip=1, repeat_action_probability=0.)
    if self.dump_video:
      env = Monitor(env,
                    os.path.join(self.results_dir, 'video_%d' % env_number),
                    video_callable=lambda _: True,
                    force=True)
    env = FireResetEnv(env)
    env = MapState(env, lambda im: cv2.resize(im, IMAGE_SIZE))
    env = FrameStack(env, FRAME_HISTORY)
    return env

  def _start_iperf_client(self):
    proc = subprocess.Popen('exec iperf3 -c %s -t %s' %
                            (self.server_ip, self.time_limit),
                            stderr=sys.stderr,
                            stdout=sys.stdout,
                            shell=True)
    return proc

  def _start_ping(self):
    proc = subprocess.Popen('exec ping %s -w %s -i 0.2 > %s' %
                            (self.server_ip, self.time_limit + 4,
                             os.path.join(self.results_dir, 'ping.txt')),
                            stderr=sys.stderr,
                            stdout=sys.stdout,
                            shell=True)
    return proc

  def _start_cwnd_monitor(self):

    def _collect_cwnd():
      while True:
        cwnd = self._frames_socket.get_cwnd()
        with self.lock:
          self.cwnds.append([time.time(), cwnd])
        time.sleep(.250)

    self.cwnds = []
    self._cwnd_thread = threading.Thread(target=_collect_cwnd)
    self._cwnd_thread.daemon = True
    self._cwnd_thread.start()

  def _receive_actions(self, act):
    with self.lock:
      self._latest_action = [time.time(), act]

  def push_frames(self):
    try:
      return self._frames_q.get_nowait()
    except queue.Empty:
      # print('App limited!...')
      pass
    return self._frames_q.get()

  def _encode_obs(self, obs):
    encoded = []
    for i in range(FRAME_HISTORY):
      success, enc = cv2.imencode('.png', obs[:, :, :, i])
      if not success:
        raise Exception('Error encountered on encoding function')
      encoded.append(enc)
    return encoded

  @staticmethod
  def decode_obs(data):
    assert len(data) == FRAME_HISTORY
    frames = []
    for enc_frame in data:
      frames.append(cv2.imdecode(enc_frame, cv2.IMREAD_UNCHANGED))
    return np.stack(frames, axis=-1)

  def _get_noop_action(self):
    return 1

  def _get_default_action(self):
    if self.skip_count < self.frameskip:
      act = self._prev_action
    else:
      act = self._get_noop_action()
    return act

  def _unwrap_action(self, act, step_number):
    game_stat = GameStat(is_skip_action=False,
                         lag_n_frames=None,
                         lag_time=None,
                         frame_size=None)

    # drop actions destined for the previous game.
    if act:
      if act[1]['game_id'] < self.game_id:
        act = None

    if act is None:
      game_stat = game_stat._replace(is_skip_action=True)
      act = self._get_default_action()
      self.skip_count += 1
    else:
      self.skip_count = 0
      t, act = act
      game_stat = game_stat._replace(lag_time=t - act['frame_timestamp'],
                                     lag_n_frames=step_number -
                                     act['frame_id'],
                                     frame_size=act['frame_size'])
      act = act['action']

    self._prev_action = act
    self._game_stats.append(game_stat)
    return act

  def _new_game(self):
    if self.game_id is None:
      self.game_id = 0
    else:
      self.game_id += 1
    self.skip_count = 0
    self._prev_action = self._get_noop_action()
    env = self._make_env(self.game_id)
    obs = env.reset()
    return env, obs

  def _wrap_frame(self, step_number, obs):
    encoded_obs = self._encode_obs(obs)
    frame = dict(frame_id=step_number,
                 frame_timestamp=time.time(),
                 frame_size=sum([sys.getsizeof(img) for img in encoded_obs]),
                 encoded_obs=encoded_obs,
                 game_id=self.game_id)
    return frame

  def _process(self):
    env, obs = self._new_game()
    sum_r = 0
    n_steps = 0
    isOver = False
    clock = Clock()
    clock.reset()
    new_game_last_step = False

    # while not isOver:
    while n_steps < self.max_steps:
      put_overwrite(self._frames_q, self._wrap_frame(n_steps, obs))

      t = self._step_sleep_time - clock.time_elapsed()
      if -t > 1e-3:
        if not new_game_last_step:
          print('sps too high for the current gameserver.... %.3f' % t)
      else:
        time.sleep(max(0, t))
      clock.reset()

      with self.lock:
        act = self._latest_action
        self._latest_action = None

      act = self._unwrap_action(act, n_steps)
      obs, r, isOver, info = env.step(act)
      if self.render:
        env.render()

      if isOver:
        env, obs = self._new_game()
        new_game_last_step = True
      else:
        new_game_last_step = False

      print('.', end='', flush=True)
      sum_r += r
      n_steps += 1

    n_skipped_actions = sum(map(lambda k: k.is_skip_action, self._game_stats))
    put_overwrite(self._frames_q, None)
    print('')
    print('# of steps elapsed: ', n_steps)
    print('# of skipped actions: ', n_skipped_actions)

    print('# of games played: ', self.game_id + 1)
    if info['ale.lives']:
      print('# of lives left: ', info['ale.lives'])
    else:
      print('Gameover - No lives left!!')
    score = sum_r - (self.game_id * NEW_GAME_PENALTY)
    print('Score: ', score)
    self._log_results(
        **dict(n_steps=n_steps,
               sum_reward=sum_r,
               score=score,
               lives_remaining=info['ale.lives'],
               n_skipped_actions=n_skipped_actions,
               total_games=self.game_id + 1))

  def _log_results(self, **kwargs):
    with open(os.path.join(self.results_dir, 'cwnd.json'), 'w') as f:
      with self.lock:
        l = list(self.cwnds)
      if l:
        json.dump(l, f, indent=2, sort_keys=True)

    with open(os.path.join(self.results_dir, 'results.json'), 'w') as f:
      json.dump(kwargs, f, indent=4, sort_keys=True)

    with open(os.path.join(self.results_dir, 'game_stats.json'), 'w') as f:
      game_stats = list(
          map(lambda game_stat: game_stat._asdict(), self._game_stats))
      json.dump(game_stats, f, indent=2, sort_keys=True)

  def _plot_results(self):
    ping_data = parse_ping(os.path.join(self.results_dir, 'ping.txt'))
    plt.figure()
    plt.plot(ping_data)
    plt.ylabel('milli seconds')
    plt.savefig(fname=os.path.join(self.results_dir, 'ping.png'))

    with open(os.path.join(self.results_dir, 'cwnd.json'), 'r') as f:
      l = json.load(f)

    if l:
      times = [i[0] for i in l]
      y = [i[1] for i in l]
      times = [t - times[0] for t in times]
      plt.figure()
      plt.plot(times, y)
      plt.xlabel('seconds')
      plt.ylabel('cwnd')
      plt.savefig(fname=os.path.join(self.results_dir, 'cwnd.png'))


def main(argv):
  args = parser.parse_args(argv[1:])
  game_play = GamePlay(
      env_name=args.env_name,
      sps=args.sps,
      agent_server_ip=args.server_ip,
      frames_port=args.frames_port,
      action_port=args.action_port,
      results_dir=args.results_dir,
      dump_video=args.dump_video,
      time_limit=args.time,
      render=args.render,
      frameskip=args.frameskip,
      use_latest_act_as_default=args.use_latest_act_as_default,
      use_iperf=args.use_iperf,
      verbose=args.verbose)
  game_play.start()


if __name__ == '__main__':
  app.run(main)
