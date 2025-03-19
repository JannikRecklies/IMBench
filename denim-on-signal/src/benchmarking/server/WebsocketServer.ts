import { DenimServer as DenimServer } from '../../core/DenimServer';
import Constants = require('../../helper/Constants');
const fs = require('fs')
const WebSocketServer = require('websocket').server;
const https = require('https');
import yargs from "yargs";
import os from 'os';
import { InfluxDB, Point } from '@influxdata/influxdb-client';

const logLevel = yargs.argv.debugserver ? 'debug' : 'info';
const logger = require('../../helper/Logger').getLogger("WebsocketServer",logLevel);

const INFLUX_URL = process.env.INFLUX_URL || "http://localhost:8086";
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || "your-default-token";
const INFLUX_ORG = process.env.INFLUX_ORG || "imbench";
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || "imbench";

const influx = new InfluxDB({ url: INFLUX_URL, token: INFLUX_TOKEN });
const writeApi = influx.getWriteApi(INFLUX_ORG, INFLUX_BUCKET);

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

function getCpuUsage(): Promise<number> {
    return new Promise<number>((resolve) => {
        const startTime = process.hrtime();
        const startUsage = process.cpuUsage();

        setTimeout(() => {
            const elapsedTime = process.hrtime(startTime);
            const elapsedUsage = process.cpuUsage(startUsage);

            const elapsedTimeMs = (elapsedTime[0] * 1000) + (elapsedTime[1] / 1e6);
            const userCpuMs = elapsedUsage.user / 1000;
            const systemCpuMs = elapsedUsage.system / 1000;

            const cpuUsage = ((userCpuMs + systemCpuMs) / elapsedTimeMs) * 100;
            resolve(cpuUsage);
        }, 1000); // Measure over 1 second
    });
}

function getSystemCpuUsage(): number {
    const cpus = os.cpus();
    let totalIdle = 0, totalTick = 0;

    cpus.forEach(cpu => {
        for (const type in cpu.times) {
            totalTick += cpu.times[type]; // Total CPU time
        }
        totalIdle += cpu.times.idle; // Idle CPU time
    });

    return 100 - (100 * totalIdle / totalTick); // Convert to percentage
}


async function logCpuUsage() {
    const cpuUsage = await getCpuUsage(); // Measuring Node.js Process CPU Usage
    // const cpuUsage = getSystemCpuUsage() // Measuring System-Wide CPU Usage (macOS/Linux)
    console.log(`💻 CPU Usage: ${cpuUsage.toFixed(2)}%`);

    const point = new Point("server_cpu_usage")
        .floatField("cpu_percentage", cpuUsage)
        .timestamp(new Date());

    writeApi.writePoint(point);
}

// Log CPU usage every 10 seconds
setInterval(logCpuUsage, 10000);