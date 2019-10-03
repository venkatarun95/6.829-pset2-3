sudo apt-get --yes update
sudo add-apt-repository ppa:keithw/mahimahi
sudo apt-get --yes update
sudo apt-get --yes install build-essential \
  git python3 python3-pip python3-dev bridge-utils mahimahi python-opengl \
  ffmpeg libav-tools xfce4 virtualbox-guest-dkms \
  virtualbox-guest-utils virtualbox-guest-x11

sudo sed -i 's/allowed_users=.*$/allowed_users=anybody/' /etc/X11/Xwrapper.config
sudo python3 -m pip install gym #atari-py roboschool
cd /home/vagrant
sudo pip install termcolor
# Install Rust
curl https://sh.rustup.rs -sSf | sh -- -y
source $HOME/.cargo/env
rustup default nightly
# Setup CCP kernel module
git clone https://github.com/ccp-project/ccp-kernel.git
cd ccp-kernel
git submodule update --init --recursive
make
sudo ./ccp_kernel_load ipc=0
# Use CCP as our default kernel module
sudo sysctl -w net.ipv4.tcp_congestion_control=ccp




sudo DEBIAN_FRONTEND=noninteractive apt-get --yes update
sudo DEBIAN_FRONTEND=noninteractive apt-get --yes install build-essential \
  git python3 python3-pip python3-dev bridge-utils mahimahi python-opengl cmake \
  libopenmpi-dev zlib1g-dev ffmpeg # libav-tools

sudo python3 -m pip install gym tensorflow opencv-python atari-py pyarrow numpy absl-py
sudo python3 -m pip install --upgrade git+https://github.com/tensorpack/tensorpack.git


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

# Use CCP as our default kernel module
sudo sysctl -w net.ipv4.tcp_congestion_control=ccp
# for mahimahi
sudo sysctl -w net.ipv4.ip_forward=1
