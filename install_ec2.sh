sudo DEBIAN_FRONTEND=noninteractive apt-get --yes update
sudo DEBIAN_FRONTEND=noninteractive apt-get --yes install build-essential \
    git python3 python3-pip bridge-utils mahimahi python-opengl cmake \
      libopenmpi-dev ffmpeg python3-dev zlib1g-dev iperf
sudo DEBIAN_FRONTEND=noninteractive apt-get --yes install libelf-dev
sudo python3 -m pip install gym termcolor tensorflow opencv-python atari-py pyarrow numpy absl-py zmq matplotlib requests
sudo python3 -m pip install --upgrade git+https://github.com/tensorpack/tensorpack.git

# for mahimahi
sudo sysctl -w net.ipv4.ip_forward=1

cd $HOME

# Install Rust
curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
rustup default nightly

# Setup CCP kernel module
git clone https://github.com/ccp-project/ccp-kernel.git
cd ccp-kernel
git submodule update --init --recursive
make
sudo ./ccp_kernel_load ipc=0

# Download module
mkdir model_cache_dir
cd model_cache_dir
wget http://models.tensorpack.com/OpenAIGym/Breakout-v0.npz
cd ..
