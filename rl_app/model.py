from tensorpack import *
import tensorflow as tf

IMAGE_SIZE = (84, 84)
FRAME_HISTORY = 4
STATE_SHAPE = IMAGE_SIZE + (3, )


class Model(ModelDesc):

  def __init__(self, num_actions):
    super(Model, self).__init__()
    self.num_actions = num_actions

  def inputs(self):
    return [
        tf.TensorSpec((None, ) + STATE_SHAPE + (FRAME_HISTORY, ), tf.uint8,
                      'state'),
        tf.TensorSpec((None, ), tf.int64, 'action'),
        tf.TensorSpec((None, ), tf.float32, 'futurereward'),
        tf.TensorSpec((None, ), tf.float32, 'action_prob'),
    ]

  def _get_NN_prediction(self, state):
    assert len(state.shape)  # Batch, H, W, Channel, History
    state = tf.transpose(
        # swap channel & history, to be compatible with old models
        state,
        [0, 1, 2, 4, 3])
    image = tf.reshape(state, [-1] + list(STATE_SHAPE[:2]) +
                       [STATE_SHAPE[2] * FRAME_HISTORY])

    image = tf.cast(image, tf.float32) / 255.0
    with argscope(Conv2D, activation=tf.nn.relu):
      l = Conv2D('conv0', image, 32, 5)
      l = MaxPooling('pool0', l, 2)
      l = Conv2D('conv1', l, 32, 5)
      l = MaxPooling('pool1', l, 2)
      l = Conv2D('conv2', l, 64, 4)
      l = MaxPooling('pool2', l, 2)
      l = Conv2D('conv3', l, 64, 3)

    l = FullyConnected('fc0', l, 512)
    l = PReLU('prelu', l)
    logits = FullyConnected('fc-pi', l,
                            self.num_actions)  # unnormalized policy
    value = FullyConnected('fc-v', l, 1)
    return logits, value

  def build_graph(self, state, action, futurereward, action_prob):
    logits, value = self._get_NN_prediction(state)
    value = tf.squeeze(value, [1], name='pred_value')  # (B,)
    policy = tf.nn.softmax(logits, name='policy')
    return
