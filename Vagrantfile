$setup = <<-SCRIPT
sudo apt-get update
sudo apt-get --yes install build-essential \
  git python3 python3-pip bridge-utils mahimahi python-opengl
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
