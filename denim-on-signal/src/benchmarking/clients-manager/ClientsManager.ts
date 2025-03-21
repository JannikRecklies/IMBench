import Constants = require('../../helper/Constants');
import { ClientWrapper } from './ClientWrapper';

const logger = require('../../helper/Logger').getLogger("ClientManager", Constants.LOGLEVEL);
import WebSocket, { WebSocketServer } from 'ws';
import http from 'http';

const server = http.createServer((req, res) => {
    res.writeHead(404);
    res.end();
});
server.listen(8081, () => logger.info("WebSocket server running on port 8081"));

const clientsManagerServer = new WebSocketServer({ server });

const DENIM_SERVER_URL: string = process.env.DENIM_SERVER_URL || "wss://host.docker.internal:8080";

const clients: { [key: string]: ClientWrapper } = {};
const connections: Set<WebSocket> = new Set();

// Handle WebSocket connections
clientsManagerServer.on('connection', (ws) => {
    logger.info("✅ Python connected to control simulation.");
    connections.add(ws);

    // Handle incoming messages
    ws.on('message', async (message) => {
        const { command, clientId, recipientId, message_content } = JSON.parse(message.toString());

        if (command === "register") {
            clients[clientId] = new ClientWrapper(String(clientId), undefined, DENIM_SERVER_URL);
            await clients[clientId].initialize();

            clients[clientId].on("message", (data) => {
                logger.info(`📩 Client ${clientId} received message: ${data.message}`);
                broadcastMessage({
                    event: "message_received",
                    clientId: clientId,
                    sender: data.sender,
                    message_content: data.message,
                    timestamp: Date.now()
                });
            });
        } else if (command === "send") {
            logger.debug(`Send message request [${clientId} → ${recipientId}]: ${message_content}`);
            clients[clientId]?.sendMessage(String(message_content), String(recipientId));
        }
    });

    ws.on("close", () => {
        logger.info("❌ Python WebSocket disconnected.");
        connections.delete(ws);
    });
});
    
/**
 * Sends a message to all connected Python clients.
 */
function broadcastMessage(data: object) {
    const jsonData = JSON.stringify(data);
    connections.forEach((ws) => ws.send(jsonData));
}