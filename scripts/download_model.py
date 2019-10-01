import shutil
import os

MODEL_CACHE_DIR = 'model_cache_dir/'
ENV_TO_URL = {
    'Breakout-v0': 'http://models.tensorpack.com/OpenAIGym/Breakout-v0.npz'
}
ENV_TO_FNAME = {'Breakout-v0': 'Breakout-v0.npz'}


def download_pretrained_weights(env_name):
  """
    Downloads the pretrained weights to the directory.
    Makes it if not available.
  """
  print('Downloading model weights to ')
  os.system('mkdir -p %s' % MODEL_CACHE_DIR)
  os.system('cd "%s" && curl -s -S "%s" > %s' %
            (MODEL_CACHE_DIR, ENV_TO_URL[env_name], ENV_TO_FNAME[env_name]))
