#python3 server.py &

mm-delay 20 mm-link --uplink-queue=droptail --uplink-queue-args=packets=100 --downlink-queue=droptail --downlink-queue-args=packets=100 Verizon-LTE-short.up Verizon-LTE-short.down python3 client.py

#pkill server.py
