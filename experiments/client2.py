from socketIO_client import SocketIO


def on_news(self, data):
    print(data)
    self.emit('my other event', {'my': 'data'})


s = SocketIO('localhost', 9000)
s.on('news', on_news)
