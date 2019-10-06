sudo apt-get --yes update
sudo add-apt-repository ppa:keithw/mahimahi -y
sudo apt-get --yes update
sudo apt-get --yes install build-essential \
  git python3 python3-pip python3-dev bridge-utils mahimahi python-opengl \
  ffmpeg xfce4 zlib1g-dev iperf iperf3

sudo python3 -m pip install gym termcolor tensorflow opencv-python atari-py pyarrow numpy absl-py zmq matplotlib
sudo python3 -m pip install --upgrade git+https://github.com/tensorpack/tensorpack.git

# for mahimahi
sudo sysctl -w net.ipv4.ip_forward=1

cd /home/vagrant

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
