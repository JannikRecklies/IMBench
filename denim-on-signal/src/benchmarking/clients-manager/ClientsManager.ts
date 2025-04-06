import { createClient } from 'redis';
import Constants = require('../../helper/Constants');
import { ClientWrapper } from './ClientWrapper';

const logger = require('../../helper/Logger').getLogger("ClientManager", Constants.LOGLEVEL);

const redisHost = process.env.REDIS_HOST || 'localhost';
const redisPort = Number(process.env.REDIS_PORT || 6379);

const redisGlobalPub = createClient({ socket: { host: redisHost, port: redisPort } });

async function main() {
    await redisGlobalPub.connect();

    const clients: { [key: string]: ClientWrapper } = {};
    const DENIM_SERVER_URL: string = process.env.DENIM_SERVER_URL || "wss://host.docker.internal:8080";

    // Subscribe to global control channel to register clients
    const redisControlSub = createClient({ socket: { host: redisHost, port: redisPort } });
    await redisControlSub.connect();

    await redisControlSub.subscribe("register-client", async (message) => {
        const { command, clientId } = JSON.parse(message);

        if (command === "register" && !(clientId in clients)) {
            logger.info(`📥 Registering client ${clientId}`);

            clients[clientId] = new ClientWrapper(clientId, undefined, DENIM_SERVER_URL);
            await clients[clientId].initialize();

            // Subscribe to messages for this specific client
            const redisClientSub = createClient({ socket: { host: redisHost, port: redisPort } });
            await redisClientSub.connect();
            await redisClientSub.subscribe(`py:client:${clientId}`, async (msg) => {
                const { command, recipientId, message_content } = JSON.parse(msg);

                if (command === "send") {
                    logger.info(`📤 Send message request [${clientId} → ${recipientId}]: ${message_content}`);
                    clients[clientId]?.sendMessage(String(message_content), String(recipientId));
                }
            });

            // Handle incoming Denim messages
            clients[clientId].on("message", (data) => {
                logger.info(`📩 Client ${clientId} received message: ${data.message}`);
                const payload = {
                    event: "message_received",
                    clientId,
                    sender: data.sender,
                    message_content: data.message,
                    timestamp: Date.now()
                };
                redisGlobalPub.publish(`ts:client:${clientId}`, JSON.stringify(payload));
            });
        }
    });
}

main().catch((err) => {
    console.error("❌ Failed to start client manager:", err);
});
