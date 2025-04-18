import { DenimServer as DenimServer } from '../../core/DenimServer';
import Constants = require('../../helper/Constants');
const fs = require('fs')
const WebSocketServer = require('websocket').server;
const https = require('https');
import yargs from "yargs";

const logLevel = yargs.argv.debugserver ? 'debug' : 'info';
const logger = require('../../helper/Logger').getLogger("WebsocketServer",logLevel);

const q = yargs.argv.q != undefined ? yargs.argv.q : Constants.DEFAULT_Q;

let denimServer = new DenimServer(q);
let connectionToAddress = new Map<any, string>();
let addressToConnection = new Map<string, any>();

let server = https.createServer(
    { key:fs.readFileSync('ssl-cert/key.pem') 
    , cert:fs.readFileSync('ssl-cert/cert.pem')
    }
  , function(request, response) {
      logger.info((new Date()) + ' Received request for ' + request.url);
      response.writeHead(404);
      response.end();
  });

server.listen(8080, function() {
    logger.info((new Date()) + ' Server is listening on port 8080');
    logger.info("Statistics will be printed and saved upon ctrl-c before exiting");
    logger.info(`q is ${q}`);
});

let wsServer = new WebSocketServer({
    httpServer: server,
    // You should not use autoAcceptConnections for production
    // applications, as it defeats all standard cross-origin protection
    // facilities built into the protocol and the browser.  You should
    // *always* verify the connection's origin and decide whether or not
    // to accept it.
    autoAcceptConnections: false
});

function originIsAllowed(origin) {
  // put logic here to detect whether the specified origin is allowed.
  return true;
}

wsServer.on('request',(request) => {
    if (!originIsAllowed(request.origin)) {
        // Make sure we only accept requests from an allowed origin
        request.reject();
        logger.debug((new Date()) + ' Connection from origin ' + request.origin + ' rejected.');
        return;
    }
    
    let connection = request.accept(Constants.PROTOCOL, request.origin);
    logger.info((new Date()) + ' Connection accepted.');
    connection.on('message', (message) => {
        if (message.type === 'utf8') {
            let content = message.utf8Data;

            logger.info('New connection with: ' + content);
            connectionToAddress.set(connection, content);
            addressToConnection.set(content, connection);
        }
        else if (message.type === 'binary') {
            logger.debug('Received message of ' + message.binaryData.length + ' bytes');
            const sender = connectionToAddress.get(connection);
            const response = denimServer.process(sender, message.binaryData);
            // Reply/forward
            if(response.receiver!=null && response.msg.length > 0 ){                
                const respondTo = addressToConnection.get(response.receiver);
                respondTo.sendBytes(response.msg);
            } else {
                logger.debug(`DenimServer's process() returned null`);
            }

            // Process potentially deniable part *after* handling regular part
            denimServer._processChunks(sender, response.chunks);
        }
    });
    connection.on('close',(reasonCode, description) => {
        logger.info((new Date()) + ' Peer ' + connection.remoteAddress + ' disconnected.');
    });
});
