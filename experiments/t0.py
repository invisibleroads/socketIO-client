from socketIO_client import SocketIO

s = SocketIO('localhost', 8000)
del s
from time import sleep
sleep(3)
