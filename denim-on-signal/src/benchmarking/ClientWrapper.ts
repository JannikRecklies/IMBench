import Constants = require('../helper/Constants');
import { DenimClient, newDenimClient } from "../core/DenimClient";
import { ProtoFactory } from "../helper/ProtoFactory";
import Util = require('../helper/Util');
import SignalLib = require('@signalapp/libsignal-client');
import { denim_proto } from "../proto-generated/compiled";
import { Message } from '../core/Message';
import { client as WebSocketClient } from 'websocket';
import EventEmitter from 'events';
import fs from 'fs';

const logger = require('../helper/Logger').getLogger("ClientWrapper", Constants.LOGLEVEL);
const info = (x: string) => logger.info(x);
const error = (x: string) => logger.error(x);

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
    private messageLog = [];
    private logFilePath: string;

    constructor(clientId: string, deviceId = Constants.DEFAULT_DEVICE_ID, serverAddress: string) {
        this.clientId = clientId;
        this.deviceId = deviceId;
        this.serverAddress = serverAddress;
        this.clientSignalAddress = SignalLib.ProtocolAddress.new(clientId, deviceId);
        this.eventEmitter = new EventEmitter();
        this.logFilePath = `./logs/client_${clientId}_messages.json`;

        // Ensure log directory exists
        if (!fs.existsSync('./logs')) {
            fs.mkdirSync('./logs');
        }

        // Periodically save logs every 10 seconds
        setInterval(() => this.saveMessageLog(), 10000);
    }

    /**
     * Initializes the Denim client and connects to the server.
     */
    async initialize() {
        info(`Initializing DenimClient ${this.clientSignalAddress.name()}`);
        this.denimClient = await newDenimClient(this.clientId, this.deviceId);
        this.sendFunction = await this.initConnection();

        // 🔹 Register the client with the server
        const registerBytes = await this.denimClient.createRegisterThreadUnsafe();
        this.sendFunction(registerBytes);
        
        info(`Client ${this.clientSignalAddress.name()} is ready.`);
    }

    /**
     * Establishes a WebSocket connection to the Denim server.
     */
    private initConnection(): Promise<(x: Uint8Array) => void> {
        return new Promise((resolve, reject) => {
            let client = new WebSocketClient({ tlsOptions: { rejectUnauthorized: false } });

            client.on('connectFailed', (errorMessage) => {
                error(`Failed to connect to ${this.serverAddress}: ${errorMessage.toString()}`);
                reject(errorMessage);
            });

            client.on('connect', (connection) => {
                info(`Connected to ${this.serverAddress}`);
                this.serverConnections.set(this.serverAddress, connection);
                connection.send(Util.signalAddressToString(this.clientSignalAddress));

                connection.on('error', (errorMessage) => {
                    error(`Connection error: ${errorMessage.toString()}`);
                });

                connection.on('close', (reasonCode, description) => {
                    info(`Connection closed: ${reasonCode}, ${description}`);
                });

                connection.on('message', (data) => this.onMessage(data));

                resolve((x: Uint8Array) => {
                    if (connection.connected) {
                        connection.send(x);
                    } else {
                        error("Attempting to send on a closed connection.");
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
        info(`📩 Message received`);
        const denimMsg = denim_proto.DenimMessage.decode(data.binaryData);
        const processedMessages: Array<Message> = await this.denimClient.process(denimMsg);
        
        info(`🔄 Processed ${processedMessages.length} messages`);
        
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
                    info(`⚠️ Unknown message type received`);
            }
        }
    }

    /**
     * Handles a received text message.
     */
    private handleTextMessage(processedMessage: Message) {
        info(`📨 Message content: ${processedMessage.message}`);
        this.eventEmitter.emit("message", {
            sender: processedMessage.sender.name(),
            message: processedMessage.message,
        });
        //////////////
        const parsedData = JSON.parse(processedMessage.message); // Extract structured message
        const msg_id = parsedData.msg_id; // Extract msg_id from metadata
        const sentTime = parseInt(msg_id.split("-")[0]); // Extract timestamp from msg_id
        const receivedTime = Date.now();
        const sender = processedMessage.sender.name();
        const messageSize = Buffer.byteLength(parsedData.message);

        console.log(`📩 [${msg_id}] ${sender} → ${this.clientId} (Size: ${messageSize} bytes)`);

        this.messageLog.push({
            msg_id: msg_id,
            sender_id: sender,
            receiver_id: this.clientId,
            time_sent: sentTime,
            time_received: receivedTime,
            size_bytes: messageSize,
        });
    }

    /**
     * Handles key response messages.
     */
    private async handleKeyResponse(processedMessage: Message) {
        const receivedAddress = Util.signalAddressToString(processedMessage.sender);
        this.regularKeys.set(receivedAddress, Constants.KEY_STATE_RECEIVED);
        info(`🔑 Key received for user: ${receivedAddress}`);

        // 🔹 Send queued messages
        this.sendQueuedMessages(receivedAddress);
    }

    /**
     * Handles key request failures and retries.
     */
    private handleKeyRequestFailure(processedMessage: Message) {
        const senderAddress = Util.signalAddressToString(processedMessage.sender);
        info(`❌ Key request failed for ${senderAddress}. Retrying...`);

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
        this.messageLog.push({
            msg_id: msg_id,
            sender_id: this.clientId,
            receiver_id: recipientId,
            time_sent: timeSent,
            time_received: null,
            size_bytes: messageSize,
        });

        console.log(`📤 [${msg_id}] ${this.clientId} → ${recipientId} (Size: ${messageSize} bytes)`);

        // Instead of sending raw message, send a JSON object with metadata
        const messageObject = {
            msg_id: msg_id, // Attach msg_id to the message metadata
            message: message,
        };

        const msg = new Message(JSON.stringify(messageObject), this.denimClient.address, recipientSignalAddress, false, Constants.MESSAGE_TYPE_TEXT);
        
        const recipientKeyStatus = this.regularKeys.get(Util.signalAddressToString(recipientSignalAddress));

        if (!recipientKeyStatus) {
            // First-time messaging: request a key and queue the message
            info(`🕒 No key for ${recipientId}. Requesting...`);
            this.queueMessage(msg);
            const keyRequest = this.denimClient.createKeyRequest(msg.receiver);
            this.sendFunction(keyRequest);
        } else if (recipientKeyStatus === Constants.KEY_STATE_RECEIVED) {
            // Key is available, send message immediately
            info(`📤 Sending message to ${recipientId}`);
            const denimMsg = await this.denimClient.createRegularMessage(msg.message, msg.receiver);
            this.sendFunction(denimMsg);
        } else {
            // Key is still in-flight, queue message
            info(`🕒 Waiting for key to be received for ${recipientId}`);
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
            info(`📤 Sending queued message: ${msg.message}`);
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

    /**
     * Retrieve stored messages for analysis.
     */
    getMessageLog() {
        return this.messageLog;
    }

    private saveMessageLog() {
        fs.writeFileSync(this.logFilePath, JSON.stringify(this.messageLog, null, 2));
        console.log(`💾 Saved message log for client ${this.clientId}`);
    }
}