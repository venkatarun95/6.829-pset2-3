import json

port = 8887

class NetObjects:
    def __init__(self, connection):
        self.connection = connection
        self.recv_buf = ''

    def recv_obj(self):
        # Get the next chunk of data
        chunk = ''
        while True:
            data = self.connection.recv(256).decode()
            pos = data.find('\0')
            if pos != -1:
                chunk = self.recv_buf + data[:pos]
                self.recv_buf = data[pos+1:]
                break
            self.recv_buf += data
        return json.loads(chunk)

    def send_obj(self, obj):
        str = json.dumps(obj) + '\0'
        self.connection.sendall(str.encode())
