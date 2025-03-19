import Constants = require('../../helper/Constants');
import { DenimClient, newDenimClient } from "../../core/DenimClient";
import Util = require('../../helper/Util');
import SignalLib = require('@signalapp/libsignal-client');
import { denim_proto } from "../../proto-generated/compiled";
import { Message } from '../../core/Message';
import { client as WebSocketClient } from 'websocket';
import EventEmitter from 'events';
import { InfluxDB, Point } from "@influxdata/influxdb-client";

const logger = require('../../helper/Logger').getLogger("ClientWrapper", Constants.LOGLEVEL);

const INFLUX_URL = process.env.INFLUX_URL || "http://localhost:8086";
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || "your-default-token";
const INFLUX_ORG = process.env.INFLUX_ORG || "imbench";
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || "imbench";

const influx = new InfluxDB({ url: INFLUX_URL, token: INFLUX_TOKEN });
const writeApi = influx.getWriteApi(INFLUX_ORG, INFLUX_BUCKET);

export class ClientWrapper {
    private clientId: string;
    private deviceId: number;
    private denimClient: DenimClient;
    private clientSignalAddress: SignalLib.ProtocolAddress;
    private serverAddress: string;
    private sendFunction: ((x: Uint8Array) => void) | null = null;
    private eventEmitter: EventEmitter;
    private serverConnections = new Map<string, any>();
    private regularKeys = new Map<string, string>(); // Stores key statuses
    private queuedRegularMessages: Array<Message> = []; // Messages waiting for keys

    constructor(clientId: string, deviceId = Constants.DEFAULT_DEVICE_ID, serverAddress: string) {
        this.clientId = clientId;
        this.deviceId = deviceId;
        this.serverAddress = serverAddress;
        this.clientSignalAddress = SignalLib.ProtocolAddress.new(clientId, deviceId);
        this.eventEmitter = new EventEmitter();
    }

    /**
     * Initializes the Denim client and connects to the server.
     */
    async initialize() {
        logger.debug(`Initializing DenimClient ${this.clientSignalAddress.name()}`);
        this.denimClient = await newDenimClient(this.clientId, this.deviceId);
        this.sendFunction = await this.initConnection();

        // 🔹 Register the client with the server
        const registerBytes = await this.denimClient.createRegisterThreadUnsafe();
        this.sendFunction(registerBytes);
        
        logger.info(`Client ${this.clientSignalAddress.name()} is initialized and ready.`);
    }

    /**
     * Establishes a WebSocket connection to the Denim server.
     */
    private initConnection(): Promise<(x: Uint8Array) => void> {
        return new Promise((resolve, reject) => {
            let client = new WebSocketClient({ tlsOptions: { rejectUnauthorized: false } });

            client.on('connectFailed', (errorMessage) => {
                logger.error(`Failed to connect to ${this.serverAddress}: ${errorMessage.toString()}`);
                reject(errorMessage);
            });

            client.on('connect', (connection) => {
                logger.debug(`Connected to ${this.serverAddress}`);
                this.serverConnections.set(this.serverAddress, connection);
                connection.send(Util.signalAddressToString(this.clientSignalAddress));

                connection.on('error', (errorMessage) => {
                    logger.error(`Connection error: ${errorMessage.toString()}`);
                });

                connection.on('close', (reasonCode, description) => {
                    logger.debug(`Connection closed: ${reasonCode}, ${description}`);
                });

                connection.on('message', (data) => this.onMessage(data));

                resolve((x: Uint8Array) => {
                    if (connection.connected) {
                        connection.send(x);
                    } else {
                        logger.error("Attempting to send on a closed connection.");
                    }
                });
            });

            client.connect(this.serverAddress, Constants.PROTOCOL);
        });
    }

    /**
     * Handles incoming messages.
     */
    private async onMessage(data) {
        const denimMsg = denim_proto.DenimMessage.decode(data.binaryData);
        const processedMessages: Array<Message> = await this.denimClient.process(denimMsg);
        
        for (const processedMessage of processedMessages) {
            switch (processedMessage.messageType) {
                case Constants.MESSAGE_TYPE_TEXT:
                    this.handleTextMessage(processedMessage);
                    break;
                case Constants.MESSAGE_TYPE_KEY_RESPONSE:
                    this.handleKeyResponse(processedMessage);
                    break;
                case Constants.MESSAGE_TYPE_ERROR_KEY_REQUEST:
                    this.handleKeyRequestFailure(processedMessage);
                    break;
                default:
                    logger.debug(`Unknown message type received`);
            }
        }
    }

    /**
     * Handles a received text message.
     */
    private handleTextMessage(processedMessage: Message) {
        const parsedData = JSON.parse(processedMessage.message); // Extract structured message
        const msg_id = parsedData.msg_id; // Extract msg_id from metadata
        const sentTime = parseInt(msg_id.split("-")[0]); // Extract timestamp from msg_id
        const latency = Date.now() - Number(sentTime);
        const sender = processedMessage.sender.name();
        const messageSize = Buffer.byteLength(parsedData.message);
        
        // Store sent message metadata
        this.logMessageReceived(msg_id, sender, this.clientId, messageSize, latency);
        
        logger.info(`Received text message [${sender} → ${this.clientId}] (Latency: ${latency}ms)`);
        logger.debug(`Received text message [${sender} → ${this.clientId}]: "${processedMessage.message}" (Size: ${messageSize} bytes)`);
        
        this.eventEmitter.emit("message", {
            sender: processedMessage.sender.name(),
            message: processedMessage.message,
        });
    }

    /**
     * Handles key response messages.
     */
    private async handleKeyResponse(processedMessage: Message) {
        const receivedAddress = Util.signalAddressToString(processedMessage.sender);
        this.regularKeys.set(receivedAddress, Constants.KEY_STATE_RECEIVED);
        logger.info(`Received regular key [${receivedAddress} → ${this.clientId}]`);

        // Send queued messages
        this.sendQueuedMessages(receivedAddress);
    }

    /**
     * Handles key request failures and retries.
     */
    private handleKeyRequestFailure(processedMessage: Message) {
        const senderAddress = Util.signalAddressToString(processedMessage.sender);
        logger.warn(`Key request failed for ${senderAddress}. Retrying...`);

        const keyRequest = this.denimClient.createKeyRequest(processedMessage.sender);
        this.sendFunction(keyRequest);
    }

    /**
     * Sends a message to another client.
     */
    async sendMessage(message: string, recipientId: string) {
        const recipientSignalAddress = SignalLib.ProtocolAddress.new(recipientId, Constants.DEFAULT_DEVICE_ID);

        const timeSent = Date.now();
        const msg_id = this.generateMessageId();
        const messageSize = Buffer.byteLength(message);

        // Store sent message metadata
        this.logMessageSent(msg_id, this.clientId, recipientId, messageSize, timeSent);

        logger.debug(`Sending message [${this.clientId} → ${recipientId}]: "${message}" (Size: ${messageSize} bytes)`);

        // Instead of sending raw message, send a JSON object with metadata
        const messageObject = {
            msg_id: msg_id, // Attach msg_id to the message metadata
            message: message,
        };

        const msg = new Message(JSON.stringify(messageObject), this.denimClient.address, recipientSignalAddress, false, Constants.MESSAGE_TYPE_TEXT);
        
        const recipientKeyStatus = this.regularKeys.get(Util.signalAddressToString(recipientSignalAddress));

        if (!recipientKeyStatus) {
            // First-time messaging: request a key and queue the message
            logger.debug(`No key for ${recipientId}. Requesting...`);
            this.queueMessage(msg);
            const keyRequest = this.denimClient.createKeyRequest(msg.receiver);
            this.sendFunction(keyRequest);
        } else if (recipientKeyStatus === Constants.KEY_STATE_RECEIVED) {
            // Key is available, send message immediately
            logger.debug(`Sending message to ${recipientId}`);
            const denimMsg = await this.denimClient.createRegularMessage(msg.message, msg.receiver);
            this.sendFunction(denimMsg);
        } else {
            // Key is still in-flight, queue message
            logger.debug(`Waiting for key to be received for ${recipientId}`);
            this.queuedRegularMessages.push(msg);
        }
    }

    /**
     * Queues a message and sends a key request.
     */
    private queueMessage(msg: Message) {
        this.regularKeys.set(Util.signalAddressToString(msg.receiver), Constants.KEY_STATE_IN_FLIGHT);
        this.queuedRegularMessages.push(msg);
    }

    /**
     * Sends queued messages after a key is received.
     */
    private async sendQueuedMessages(recipientAddress: string) {
        const toSend = this.queuedRegularMessages.filter(msg => Util.signalAddressToString(msg.receiver) === recipientAddress);
        
        for (const msg of toSend) {
            logger.debug(`Sending queued message: ${msg.message}`);
            const denimMsg = await this.denimClient.createRegularMessage(msg.message, msg.receiver);
            this.sendFunction(denimMsg);
        }

        this.queuedRegularMessages = this.queuedRegularMessages.filter(msg => Util.signalAddressToString(msg.receiver) !== recipientAddress);
    }

    /**
     * Allows external code to listen for events.
     */
    on(event: string, listener: (...args: any[]) => void) {
        this.eventEmitter.on(event, listener);
    }

    /**
     * Generate a unique message ID (does not affect message content).
     */
    private generateMessageId(): string {
        return `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    }

    private logMessageSent(msg_id: string, sender: string, receiver: string, msg_size: number, time_sent: number) {
        const point = new Point("message_sent")
            .tag("msg_id", msg_id)
            .tag("sender", sender)
            .tag("receiver", receiver)
            .intField("msg_size", msg_size)
            .intField("time_sent", time_sent);
        writeApi.writePoint(point);
    }

    private logMessageReceived(msg_id: string, sender: string, receiver: string, msg_size: number, latency: number) {
        const point = new Point("message_revceived")
            .tag("msg_id", msg_id)
            .tag("sender", sender)
            .tag("receiver", receiver)
            .intField("msg_size", msg_size)
            .intField("latency_ms", latency);
        writeApi.writePoint(point);
    }

}