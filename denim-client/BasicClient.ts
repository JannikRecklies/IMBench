import Constants = require('../helper/Constants');
import {DenimClient, newDenimClient} from "../core/DenimClient";
import { ProtoFactory } from "../helper/ProtoFactory";
import Util = require('../helper/Util');
import SignalLib = require('@signalapp/libsignal-client');
import { denim_proto } from "../proto-generated/compiled";
import { Message } from '../core/Message';
import yargs from "yargs";

const EventEmitter = require('events');
class MessageEmitter extends EventEmitter {}
let messageEmitter = new MessageEmitter();

const denimServerAddress = "wss://192.168.2.240:8080/"

const fs = require('fs');

const logger = require('../helper/Logger').getLogger("NewBasicClient", Constants.LOGLEVEL);
const info = x => logger.info(x)
const debug = x => logger.debug(x)
const error = x => logger.error(x);

const WebSocketClient = require('websocket').client;

const printMessageReceived = "messageReceived";

type t = (x:Uint8Array) => void;

let denimSend:t; // Connection to DenimServer
let denimClient:DenimClient; // DenimClient object to delegate to

let serverConnections = new Map<string, any>();
let clientSignalAddress:SignalLib.ProtocolAddress;

function getPrintName() {
    return `CLIENT_ID_${clientSignalAddress?.name()}`;
}

process.on('uncaughtException', function(e) {
    error(`Uncaught Exception in ${getPrintName()}: ${e}`);
    error(`Stack trace: ${e.stack?e.stack:new Error("Uncaught error").stack}`);
    process.exit(99);
});

process.on('exit', function (exitcode) {
    info(`${getPrintName()} exiting with code ${exitcode}; ongoing connections: ${serverConnections.values?.length}`);
});


function initExperimentClient(onMessage, initialMessage, serverAddress, protocol): Promise<t> {
    return new Promise ((resolve, reject) => {
        let client = new WebSocketClient({tlsOptions:{rejectUnauthorized: false}})

        client.on('connectFailed', (errorMessage) => {
            error(`Failed to connect to ${serverAddress}, protocol: ${protocol}. Connect error: ${errorMessage.toString()}`)
        });
        
        client.on('connect',(connection) => {
            info('Connected to '+serverAddress);
            serverConnections.set(serverAddress, connection);
            connection.send(initialMessage);
            connection.on('error',(errorMessage) => {
                error(`${getPrintName()}; Connection Error: ${errorMessage.toString()}`);
            });
            connection.on('close', (reasonCode, description) => {
                info(`Connection to ${connection.remoteAddress} closed`);

                if(connection.protocol===Constants.PROTOCOL) {
                    // Report back to dispatcher
                    info(`${getPrintName()} Socket closed`);
                } else if(connection.protocol===Constants.EXPERIMENT_PROTOCOL) {
                    error(`${getPrintName()} Connection with Dispatcher (${connection.remoteAddress}) closed, reason: ${reasonCode}, description: ${description}`);
                    process.exit(255);
                }
            });
            connection.on('message', onMessage);
            
            function sendMessage (x:string|Uint8Array) { // Strings to Dispatcher, bytes to DenimServer
                if (connection.connected) {
                    connection.send(x);
                } else {
                    // some error reporting
                    throw `Attempting to send on a closed connection, protocol is ${connection.protocol}`;
                }
            }
            resolve(sendMessage)
        });
    
        client.connect(serverAddress, protocol);
   });
}



const onMessage = async (data) => {
    info(`msg received`);
    if(data.utf8Data) { // Dispatcher messages
        info(data.utf8Data);
        //Process dispatcher commands
        let content = data.utf8Data;
        info(data.binaryData)
    }
}

async function main() {
    info(`test`);
    // denimSend = await initExperimentClient(onMessage, Constants.CLIENT_CONNECT, 'wss://192.168.2.240:8080', Constants.PROTOCOL);
    // Initialize denim client
    let denimClient1 = await newDenimClient("1", Constants.DEFAULT_DEVICE_ID); 
    let clientSignalAddress1 = SignalLib.ProtocolAddress.new("1", Constants.DEFAULT_DEVICE_ID);
    info(`DenimClient ${clientSignalAddress1.name()} has been initialized`); 
    let denimSend1 = await initExperimentClient(onMessage, Util.signalAddressToString(clientSignalAddress1), denimServerAddress, Constants.PROTOCOL);


    let denimClient2 = await newDenimClient("2", Constants.DEFAULT_DEVICE_ID); 
    let clientSignalAddress2 = SignalLib.ProtocolAddress.new("2", Constants.DEFAULT_DEVICE_ID);
    info(`DenimClient ${clientSignalAddress2.name()} has been initialized`); 
    let denimSend2 = await initExperimentClient(onMessage, Util.signalAddressToString(clientSignalAddress2), denimServerAddress, Constants.PROTOCOL);

    

    const denimMsg = denimClient1.createKeyRequest(clientSignalAddress2);
    // const denimMsg = await denimClient1.createRegularMessage("initialMessage", clientSignalAddress2);
    denimSend1(denimMsg);
    info(`over`);
}


main();