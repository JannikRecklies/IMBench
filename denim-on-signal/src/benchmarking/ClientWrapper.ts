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
        info(`Processed messages: ${processedMessages.length}`);
        
        for (const processedMessage of processedMessages) {
            let msg = processedMessage.message;
            info(`Message received with type: ${processedMessage.messageType}`);

            if (processedMessage.messageType === Constants.MESSAGE_TYPE_TEXT) {
                info(`Message received with content: ${processedMessage}`);
                // 🔹 Emit the event so external code can react
                this.eventEmitter.emit("message", {
                    sender: processedMessage.sender.name(),
                    message: msg,
                });
            } else if (processedMessage.messageType === Constants.MESSAGE_TYPE_KEY_RESPONSE) {
                const receivedAddress = Util.signalAddressToString(processedMessage.sender);
                this.regularKeys.set(receivedAddress, Constants.KEY_STATE_RECEIVED);
                info(`Key response received for user: ${receivedAddress}. RegularKeys Size: ${this.regularKeys.size}`);

                //Send queued messages
                const toSend = this.queuedRegularMessages.filter(msg => 
                    Util.signalAddressToString(msg.receiver) === receivedAddress);
                
                for(const msg of toSend){
                    info(`Sending queued regular message: ${msg}`);
                    //const sessionOngoing = (await this.denimClient.regularSessionStore.getSession(msg.receiver)).hasCurrentState();
                    // info(`Regular session started: ${sessionOngoing}`);
                    const denimMsg = await this.denimClient.createRegularMessage(msg.message, msg.receiver);
                    this.sendFunction(denimMsg)
                }

                this.queuedRegularMessages = []
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
    async sendMessage(message: string, recipientId: string) {
        const recipientSignalAddress = SignalLib.ProtocolAddress.new(recipientId, Constants.DEFAULT_DEVICE_ID);
        const msg = new Message(message, this.denimClient.address, recipientSignalAddress, false, Constants.MESSAGE_TYPE_KEY_RESPONSE)
        //const denimMsg = await this.denimClient.createRegularMessage(message, clientSignalAddress);
        
        let keyStatus = this.regularKeys.get(Util.signalAddressToString(recipientSignalAddress));
        // let denimMsg:Uint8Array;
        if(keyStatus==null) { // If there's no entry, we haven't requested keys for this user
            info(`Client ${this.denimClient.address.name()} has no key for ${recipientId}: ${this.regularKeys.size}`);
            this.regularKeys.set(Util.signalAddressToString(recipientSignalAddress), Constants.KEY_STATE_IN_FLIGHT);
            this.queuedRegularMessages.push(msg);
            
            let keyRequest = this.denimClient.createKeyRequest(recipientSignalAddress);
            this.sendFunction(keyRequest);
        } else if(keyStatus==Constants.KEY_STATE_RECEIVED) {
            info(`Client ${this.denimClient.address.name()} has key for ${recipientId}: ${this.regularKeys.size}`);
            const denimMsg = await this.denimClient.createRegularMessage(message, recipientSignalAddress);
            this.sendFunction(denimMsg);
        } else if(keyStatus==Constants.KEY_STATE_IN_FLIGHT) {
            info(`Client ${this.denimClient.address.name()} is waiting for key for ${recipientId}: ${this.regularKeys.size}`);
            this.queuedRegularMessages.push(msg);
        }
    }

    /**
     * Emits events when messages are received.
     */
    on(event: string, listener: (...args: any[]) => void) {
        this.eventEmitter.on(event, listener);
    }
}