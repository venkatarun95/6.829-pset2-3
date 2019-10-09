sudo sysctl -w net.ipv4.ip_forward=1
cd /root/ccp-kernel
sudo ./ccp_kernel_load ipc=0
sudo sysctl -w net.ipv4.tcp_congestion_control=ccp

cd /pset2-3
export PYTHONPATH=$PYTHONPATH:/pset2-3
