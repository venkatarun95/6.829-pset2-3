from rl_app.network.network import Receiver, Sender
import time
from absl.testing import absltest


class NetworkTest(absltest.TestCase):

  def _setup(self):
    recv_server = Receiver(host='0.0.0.0', port=7000, bind=True)

    self._msg_recvd = False

    def f(msg):
      assert msg == 0
      if self._msg_recvd:
        return None
      print('Server received message', msg)
      self._msg_recvd = True

    def f_send():
      return 0

    recv_server.start_loop(f)
    sender_client = Sender(host='127.0.0.1', port=7000, bind=False)
    sender_client.start_loop(f_send)
    return recv_server, sender_client

  def testSenderReceiver(self):
    recv_server, sender_client = self._setup()
    time.sleep(.5)
    self.assertEqual(self._msg_recvd, True)
    print('Done')


if __name__ == '__main__':
  absltest.main()
