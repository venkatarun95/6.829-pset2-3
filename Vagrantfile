$setup = <<-SCRIPT
sudo apt-get update
sudo apt-get --yes install build-essential \
  git python3 python3-pip bridge-utils mahimahi python-opengl
sudo python3 -m pip install gym atari-py #roboschool
cd /home/vagrant
sudo pip install termcolor

SCRIPT

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"
  config.vm.synced_folder ".", "/pset2-3"
  config.vm.network :forwarded_port, guest:8000, host:8000 # http server
  config.ssh.forward_x11 = true

  config.vm.provider "virtualbox" do |v|
    v.gui = false
    v.cpus = 4
    v.memory = 8192
  end
  config.vm.provision "shell", inline: $setup
end
