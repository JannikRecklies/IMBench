import Constants = require('../helper/Constants');
import { ClientWrapper } from './ClientWrapper';

const logger = require('../helper/Logger').getLogger("ClientManager", Constants.LOGLEVEL);
const WebSocketServer = require('websocket').server;
const http = require('http');

const server = http.createServer((req, res) => {
    res.writeHead(404);
    res.end();
});
server.listen(8081, () => logger.info("WebSocket server running on port 8081"));

const clientsManagerServer = new WebSocketServer({
    httpServer: server,
    autoAcceptConnections: false
});

const denimServerAddress: string = "wss://127.0.0.1:8080";
const clients: { [key: string]: ClientWrapper } = {};
const connections: any[] = [];

clientsManagerServer.on('request', (request) => {
    const connection = request.accept(null, request.origin);
    logger.info("Python connected to control simulation.");
    connections.push(connection);

    connection.on('message', async (message) => {
        const { command, clientId, recipientId, text, delay } = JSON.parse(message.utf8Data);

        if (command === "register") {
            clients[clientId] = new ClientWrapper(clientId, undefined, denimServerAddress);
            await clients[clientId].initialize();

            // Notify Python when this client receives a message
            clients[clientId].on("message", (data) => {
                logger.debug(`📩 Client ${clientId} received message: ${data.message}`);
                broadcastMessage({
                    event: "message_received",
                    clientId: clientId,
                    sender: data.sender,
                    message: data.message,
                    timestamp: Date.now()
                });
            });
        } 
        else if (command === "send") {
            setTimeout(() => {
                logger.debug(`Send message request [${clientId} → ${recipientId}]: ${text}`);
                clients[clientId]?.sendMessage(text, recipientId);
            }, delay);
        }
    });

    connection.on('close', () => {
        logger.info("Python WebSocket disconnected.");
        const index = connections.indexOf(connection);
        if (index > -1) connections.splice(index, 1);
    });
});

/**
 * Sends a message to all connected clients (Python scripts).
 */
function broadcastMessage(data: object) {
    const jsonData = JSON.stringify(data);
    connections.forEach(conn => conn.sendUTF(jsonData));
}