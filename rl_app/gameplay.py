import argparse
import threading
import time

import cv2
import gym
import numpy as np
import queue
from absl import app
from rl_app.atari_wrapper import (FireResetEnv, FrameStack, LimitLength,
                                  MapState)
from rl_app.network.network import Receiver, Sender
from rl_app.util import Timer, put_overwrite
from tensorpack import *

parser = argparse.ArgumentParser()
parser.add_argument('--env_name', type=str, required=True)
parser.add_argument('--server_ip', type=str, required=True)
parser.add_argument('--frames_port', type=int, required=True)
parser.add_argument('--action_port', type=int, required=True)
parser.add_argument('--sps', type=int, default=20)
parser.add_argument('--frameskip', type=int, default=1)
parser.add_argument('--render', dest='render', action='store_true')
parser.add_argument('--dump_dir',
                    type=str,
                    default=None,
                    help='Dump the video here')
parser.add_argument('--time_limit', type=int, default=60)

IMAGE_SIZE = (84, 84)
FRAME_HISTORY = 4


class GamePlay:

  def __init__(
      self,
      env_name,
      sps,
      agent_server_ip,
      frames_port,
      action_port,
      time_limit,
      render=False,
      dump_dir=None,
      frameskip=1,
  ):
    env = gym.make(env_name, frameskip=frameskip, repeat_action_probability=0.)
    if dump_dir:
      env = gym.wrappers.Monitor(env, dump_dir, video_callable=lambda _: True)
    env = FireResetEnv(env)
    env = MapState(env, lambda im: cv2.resize(im, IMAGE_SIZE))
    env = FrameStack(env, FRAME_HISTORY)
    env = LimitLength(env, sps * time_limit)

    self.sps = sps
    self._step_sleep_time = 1.0 / sps
    self.server_ip = agent_server_ip
    self.frames_port = frames_port
    self.action_port = action_port
    self.render = render
    self.env = env
    self.lock = threading.Lock()
    self._latest_action = None
    self._frames_q = queue.Queue(1)

  def start(self):
    self._frames_socket = Sender(host=self.server_ip,
                                 port=self.frames_port,
                                 bind=False)
    self._actions_socket = Receiver(host=self.server_ip,
                                    port=self.action_port,
                                    bind=False)
    self._frames_socket.start_loop(self.push_frames, blocking=False)
    self._actions_socket.start_loop(self._receive_actions, blocking=False)
    self._process()

  def _receive_actions(self, act):
    with self.lock:
      self._latest_action = act

  def push_frames(self):
    return self._frames_q.get()

  def _get_default_action(self):
    return 0

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

  def _process(self):
    env = self.env
    obs = env.reset()
    sum_r = 0
    n_steps = 0
    isOver = False
    put_overwrite(self._frames_q, self._encode_obs(obs))

    while not isOver:
      with Timer() as step_time:
        print('.', end='', flush=True)
        with self.lock:
          act = self._latest_action
          self._latest_action = None

        if act is None:
          act = self._get_default_action()

        obs, r, isOver, info = env.step(act)
        put_overwrite(self._frames_q, self._encode_obs(obs))

        if self.render:
          env.render()

      if not isOver:
        time.sleep(max(0, self._step_sleep_time - step_time.time()))

      sum_r += r
      n_steps += 1

    print('# of steps elapsed: ', n_steps)
    print('Score: ', sum_r)


def main(argv):
  args = parser.parse_args(argv[1:])
  game_play = GamePlay(
      env_name=args.env_name,
      sps=args.sps,
      agent_server_ip=args.server_ip,
      frames_port=args.frames_port,
      action_port=args.action_port,
      dump_dir=args.dump_dir,
      time_limit=args.time_limit,
      render=args.render,
      frameskip=args.frameskip,
  )
  game_play.start()


if __name__ == '__main__':
  app.run(main)
