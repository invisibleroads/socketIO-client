// DEBUG=* node app.js
var app = require('express')();
var server = require('http').Server(app);
var io = require('socket.io')(server);

server.listen(9000);

app.get('/', function (req, res) {
  res.sendFile(__dirname + '/index.html');
});

io.on('connection', function (socket) {
  socket.emit('news', { hello: 'world' });
  socket.on('my other event', function (data) {
    console.log(data);
  });
});
