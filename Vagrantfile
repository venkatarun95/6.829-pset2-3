$setup = <<-SCRIPT
sudo DEBIAN_FRONTEND=noninteractive apt-get --yes update
sudo DEBIAN_FRONTEND=noninteractive apt-get --yes install build-essential \
  git python3 python3-pip bridge-utils mahimahi python-opengl cmake \
  libopenmpi-dev ffmpeg python3-dev zlib1g-dev iperf
sudo DEBIAN_FRONTEND=noninteractive apt-get --yes install libelf-dev
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

# Use CCP as our default kernel module
sudo sysctl -w net.ipv4.tcp_congestion_control=ccp

# Download module
cd /pset2-3/
mkdir model_cache_dir
cd /pset2-3/model_cache_dir
wget http://models.tensorpack.com/OpenAIGym/Breakout-v0.npz
cd ..

SCRIPT

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/bionic64"
  config.vm.synced_folder ".", "/pset2-3"
  config.vm.network :forwarded_port, guest:7000, host:7000 # http server
  config.ssh.forward_x11 = true

  config.vm.provider "virtualbox" do |v|
    v.gui = false
    v.cpus = 4
    v.memory = 8192
  end
  config.vm.provision "shell", inline: $setup
end
