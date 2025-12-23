const http = require('http');

const server = http.createServer((req, res) => {
  res.end('ok');
});

server.listen(5174, '127.0.0.1', () => {
  console.log('LISTEN OK http://127.0.0.1:5174');
});
