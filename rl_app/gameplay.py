import threading

import cv2
import gym
from atari_wrapper import FireResetEnv, FrameStack, LimitLength, MapState

IMAGE_SIZE = (84, 84)
FRAME_HISTORY = 4


class GamePlay:

  def __init__(
      self,
      env_name,
      agent_server_ip,
      agent_server_port,
      agent_receiver_port,
      render=False,
      dumpdir=None,
      frame_buffer_max_size=10,
  ):
    env = gym.make(env_name)
    if dumpdir:
      env = gym.wrappers.Monitor(env, dumpdir, video_callable=lambda _: True)
    env = FireResetEnv(env)
    env = MapState(env, lambda im: cv2.resize(im, IMAGE_SIZE))
    env = FrameStack(env, FRAME_HISTORY)

    self.render = render
    self.dumpdir = dumpdir
    self.env = env
    self.lock = Threading.lock()
    self.frame_sender = get_remote_client(Agent,
                                          host=agent_server_ip,
                                          port=agent_server_port)
    self.action_receiver = ZmqReceiver(host='*',
                                       port=agent_receiver_port,
                                       bind=True)

    self._frames_q = threading.Queue(maxsize=frame_buffer_max_size)
    self._latest_action = None

  def serve_forever(self):
    self.action_receiver.start_loop(self._receive_actions, blocking=False)
    # register
    self.frame_sender.register(env_name, env.action_space.n,
                               agent_receiver_port)
    # loops foreveer.
    self._push_frames(self._frames_q)

  def _receive_actions(self, act):
    with self.lock.acquire():
      self._latest_action = act

  def _push_frames(self, frames_q):
    while True:
      s = frames_q.read()
      if s is None:
        return
      self.frame_sender.record_frame(s)
