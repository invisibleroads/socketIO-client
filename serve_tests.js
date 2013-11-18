var io = require('socket.io').listen(8000);

var main = io.of('').on('connection', function(socket) {
  socket.on('message', function(data, fn) {
    if (fn) {  // Client expects a callback
      if (data) {
        fn(data);
      } else {
        fn();
      }
    } else if (typeof data === 'object') {
      socket.json.send(data ? data : 'message_response');  // object or null
    } else {
      socket.send(data ? data : 'message_response');  // string or ''
    }
  });
  socket.on('emit', function() {
    socket.emit('emit_response');
  });
  socket.on('emit_with_payload', function(payload) {
    socket.emit('emit_with_payload_response', payload);
  });
  socket.on('emit_with_multiple_payloads', function(payload, payload) {
    socket.emit('emit_with_multiple_payloads_response', payload, payload);
  });
  socket.on('emit_with_callback', function(fn) {
    fn();
  });
  socket.on('emit_with_callback_with_payload', function(fn) {
    fn(PAYLOAD);
  });
  socket.on('emit_with_callback_with_multiple_payloads', function(fn) {
    fn(PAYLOAD, PAYLOAD);
  });
  socket.on('emit_with_event', function(payload) {
    socket.emit('emit_with_event_response', payload);
  });
  socket.on('ack', function(payload) {
    socket.emit('ack_response', payload, function(payload) {
      socket.emit('ack_callback_response', payload);
    });
  });
  socket.on('aaa', function() {
    socket.emit('aaa_response', PAYLOAD);
  });
  socket.on('bbb', function(payload, fn) {
    if (fn) {
      fn(payload);
    }
  });
  socket.on('wait_with_disconnect', function() {
    socket.emit('wait_with_disconnect_response');
  });
});

var chat = io.of('/chat').on('connection', function (socket) {
  socket.on('emit_with_payload', function(payload) {
    socket.emit('emit_with_payload_response', payload);
  });
  socket.on('aaa', function() {
    socket.emit('aaa_response', 'in chat');
  });
  socket.on('ack', function(payload) {
    socket.emit('ack_response', payload, function(payload) {
      socket.emit('ack_callback_response', payload);
    });
  });
});

var news = io.of('/news').on('connection', function (socket) {
  socket.on('emit_with_payload', function(payload) {
    socket.emit('emit_with_payload_response', payload);
  });
  socket.on('aaa', function() {
    socket.emit('aaa_response', 'in news');
  });
});

var PAYLOAD = {'xxx': 'yyy'};
