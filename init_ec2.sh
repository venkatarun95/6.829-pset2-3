sudo sysctl -w net.ipv4.ip_forward=1
cd $HOME/ccp-kernel
sudo ./ccp_kernel_load ipc=0
export PYTHONPATH=$PYTHONPATH:$HOME/6.829-pset2-3
