sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv4.tcp_congestion_control=ccp
cd $HOME/ccp-kernel
sudo ./ccp_kernel_load ipc=0
export PYTHONPATH=$PYTHONPATH:$HOME/6.829-pset2-3
