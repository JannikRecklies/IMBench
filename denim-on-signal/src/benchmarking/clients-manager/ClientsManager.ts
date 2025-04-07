import amqp from 'amqplib';
import { ClientWrapper } from './ClientWrapper';
import Constants = require('../../helper/Constants');

const logger = require('../../helper/Logger').getLogger("ClientManager", Constants.LOGLEVEL);

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://host.docker.internal';
const EXCHANGE_NAME = 'imbench_exchange';
const DENIM_SERVER_URL = process.env.DENIM_SERVER_URL || "wss://host.docker.internal:8080";

const clients: { [key: string]: ClientWrapper } = {};

async function main() {
  const conn = await amqp.connect(RABBITMQ_URL);
  const channel = await conn.createChannel();

  // Declare a topic exchange
  await channel.assertExchange(EXCHANGE_NAME, 'topic', { durable: false });

  // Create an exclusive queue for registration messages from Python
  const { queue: registrationQueue } = await channel.assertQueue('', { exclusive: true });
  await channel.bindQueue(registrationQueue, EXCHANGE_NAME, 'py.register');

  // Listen for registration messages
  channel.consume(registrationQueue, async (msg) => {
    if (!msg) return;

    const { command, clientId } = JSON.parse(msg.content.toString());
    if (command === "register" && !(clientId in clients)) {
      logger.info(`📥 Registering client ${clientId}`);
      clients[clientId] = new ClientWrapper(clientId, undefined, DENIM_SERVER_URL);
      await clients[clientId].initialize();

      // Create an exclusive queue for this client’s messages from Python
      const { queue: clientQueue } = await channel.assertQueue('', { exclusive: true });
      await channel.bindQueue(clientQueue, EXCHANGE_NAME, `py.client.${clientId}`);

      // Listen for Python → TS messages for this client
      channel.consume(clientQueue, async (msg) => {
        if (!msg) return;

        const { command, recipientId, message_content } = JSON.parse(msg.content.toString());
        if (command === "send") {
          logger.info(`📤 Send message request [${clientId} → ${recipientId}]: ${message_content}`);
          clients[clientId]?.sendMessage(message_content, recipientId);
        }

        channel.ack(msg);
      });

      // Handle TS → Python messages from Denim client
      clients[clientId].on("message", async (data) => {
        const payload = {
          event: "message_received",
          clientId,
          sender: data.sender,
          message_content: data.message,
          timestamp: Date.now()
        };

        channel.publish(EXCHANGE_NAME, `ts.client.${clientId}`, Buffer.from(JSON.stringify(payload)));
      });
    }

    channel.ack(msg);
  });

  logger.info("✅ RabbitMQ Client Manager is ready.");
}

main().catch((err) => {
  console.error("❌ Failed to start client manager:", err);
});