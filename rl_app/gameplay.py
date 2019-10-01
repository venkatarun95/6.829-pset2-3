import threading
import time

import cv2
import gym
from atari_wrapper import FireResetEnv, FrameStack, LimitLength, MapState
from rl_app.network.network import Receiver, Sender
from rl_app.util import put_overwrite, Timer
from tensorpack import *

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
      render=False,
      dumpdir=None,
  ):
    env = gym.make(env_name)
    if dumpdir:
      env = gym.wrappers.Monitor(env, dumpdir, video_callable=lambda _: True)
    env = FireResetEnv(env)
    env = MapState(env, lambda im: cv2.resize(im, IMAGE_SIZE))
    env = FrameStack(env, FRAME_HISTORY)

    self.sps = sps
    self._step_sleep_time = 1.0 / sps
    self.server_ip = agent_server_ip
    self.frames_port = frames_port
    self.action_port = action_port
    self.render = render
    self.env = env
    self.lock = Threading.lock()
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

  def _process(self):
    obs = env.reset()
    sum_r = 0
    n_steps = 0
    isOver = False

    while not isOver:
      with Timer() as step_time:
        with self.lock:
          act = self._latest_action
          self._latest_action = None

        if act is None:
          act = self._get_default_action()

        ob, r, isOver, info = env.step(act)

        if self.render:
          env.render()

      if not isOver:
        time.sleep(max(0, self._step_sleep_time - step_time.time()))

      sum_r += r
      n_steps += 1

    print('# of steps elapsed: ', n_steps)
    print('Score: ', sum_r)
