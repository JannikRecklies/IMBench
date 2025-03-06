import Constants = require('../helper/Constants');
import { DenimClient, newDenimClient } from "../core/DenimClient";
import { ProtoFactory } from "../helper/ProtoFactory";
import Util = require('../helper/Util');
import SignalLib = require('@signalapp/libsignal-client');
import { denim_proto } from "../proto-generated/compiled";
import { Message } from '../core/Message';
import { client as WebSocketClient } from 'websocket';
import EventEmitter from 'events';

const logger = require('../helper/Logger').getLogger("DenimClientWrapper", Constants.LOGLEVEL);
const info = (x: string) => logger.info(x);
const debug = (x: string) => logger.debug(x);
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
    private deniableKeys = new Map<string, string>();
    private regularKeys = new Map<string, string>();
    private queuedRegularMessages: Array<Message> = [];
    private queuedDeniableMessages: Array<Message> = [];

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
        info(`Initializing DenimClient ${this.clientSignalAddress.name()}`);
        this.denimClient = await newDenimClient(this.clientId, this.deviceId);
        this.sendFunction = await this.initConnection();
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
                error(`Failed to connect to ${this.serverAddress}. Connect error: ${errorMessage.toString()}`);
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
                    info(`Connection closed: ${reasonCode}, description: ${description}`);
                });

                connection.on('message', (data) => this.onMessage(data));

                function sendMessage(x: Uint8Array) {
                    if (connection.connected) {
                        connection.send(x);
                    } else {
                        throw `Attempting to send on a closed connection.`;
                    }
                }

                resolve(sendMessage);
            });

            client.connect(this.serverAddress, Constants.PROTOCOL);
            
        });
    }

    /**
     * Handles incoming messages.
     */
    private async onMessage(data) {
        info(`Message received`);
        const denimMsg = denim_proto.DenimMessage.decode(data.binaryData);
        const processedMessages: Array<Message> = await this.denimClient.process(denimMsg);
        
        for (const processedMessage of processedMessages) {
            let msg = processedMessage.message;
            info(`Message received: ${processedMessage.messageType}`);

            if (processedMessage.messageType === Constants.MESSAGE_TYPE_TEXT) {
                info(`Message received: ${processedMessage}`);
                // 🔹 Emit the event so external code can react
                this.eventEmitter.emit("message", {
                    sender: processedMessage.sender.name(),
                    message: msg,
                });
            } else if (processedMessage.messageType === Constants.MESSAGE_TYPE_KEY_RESPONSE) {
                const receivedAddress = Util.signalAddressToString(processedMessage.sender);
                info(`Key response received for user: ${receivedAddress}`);

                if (!processedMessage.deniable) {
                    this.regularKeys.set(receivedAddress, Constants.KEY_STATE_RECEIVED);
                } else {
                    this.deniableKeys.set(receivedAddress, Constants.KEY_STATE_RECEIVED);
                }
            } else if(processedMessage.messageType==Constants.MESSAGE_TYPE_ERROR_KEY_REQUEST){ 
                            
                info(`Key request for ${processedMessage.sender.name()} failed, resending (deniable=${processedMessage.deniable})`);

                if(processedMessage.deniable==false) {
                    const denimMsg = this.denimClient.createKeyRequest(processedMessage.sender);
                    // Defensive check to make sure experiment is running...
                    this.sendFunction(denimMsg)
                } else {
                    this.denimClient.queueDeniableKeyRequest(processedMessage.sender);
                }

            }
        }
    }

    async regularKeyRequest(recipientId: string) {
        let keyStatus = this.regularKeys.get(recipientId);
        let denimMsg:Uint8Array;
        if(keyStatus==null) { // If there's no entry, we haven't requested keys for this user
            let recipientAddress = SignalLib.ProtocolAddress.new(recipientId, this.deviceId);
            denimMsg = this.denimClient.createKeyRequest(recipientAddress);
            info(`${this.denimClient.address.name()} requesting regular key for ${recipientAddress}`);
            this.sendFunction(denimMsg);
        } else if(keyStatus==Constants.KEY_STATE_RECEIVED) {
            return
        }
    }

    /**
     * Sends a message to another client.
     */
    async sendMessage(denimMsg: Uint8Array) {
        if (!this.sendFunction) {
            error("Client is not connected.");
            return;
        }

        //let recipientAddress = SignalLib.ProtocolAddress.new(recipientId, this.deviceId);
        // const denimMsg = this.denimClient.createKeyRequest(recipientAddress);
        this.sendFunction(denimMsg);

        info(`Sent message`);
    }

    async createMessage(message: string, recipientId: string) {
        const clientSignalAddress = SignalLib.ProtocolAddress.new(recipientId, Constants.DEFAULT_DEVICE_ID);
        const denimMsg = await this.denimClient.createRegularMessage(message, clientSignalAddress);
        return denimMsg
    }

    /**
     * Emits events when messages are received.
     */
    on(event: string, listener: (...args: any[]) => void) {
        this.eventEmitter.on(event, listener);
    }
}