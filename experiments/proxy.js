var proxy = require('http-proxy').createProxyServer({
  target: {host: 'localhost', port: 9000}
});
var server = require('http').createServer(function(req, res) {
  console.log('[REQUEST.%s] %s', req.method, req.url);
  console.log(req['headers']);
  if (req.method == 'POST') {
    var body = '';
    req.on('data', function (data) {
      body += data;
    });
    req.on('end', function () {
      print_body('[REQUEST.BODY] ', body);
    });
  }
  var _write = res.write;
  res.write = function(data) {
    print_body('[RESPONSE.BODY] ', data);
    _write.call(res, data);
  }
  proxy.web(req, res);
});
function print_body(header, body) {
  var text = String(body);
  console.log(header + text);
  for (var i = 0; i < text.length; i++) {
    console.log('body[%s] = %s = %s', i, text[i], text.charCodeAt(i));
  }
}
server.listen(8000);
