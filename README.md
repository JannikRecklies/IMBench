# **IMBench Setup Guide**
IMBench is a benchmarking framework designed to evaluate instant messaging (IM) systems by simulating realistic user behavior, measuring message latency, and analyzing system performance. However, currently it is only doing so for DenIM.

## **Prerequisites**
- **Docker** (For InfluxDB, Grafana, and deployment)
- **Node.js 16 (NVM Recommended)**
- **Python 3.10+**
- **InfluxDB for performance metrics**
- **RabbitMQ for for reliable messaging between Behavior and IM Service**
- **Grafana for visualization**

---

## **Distributed setup with docker**

### **📊 Message broker (RabbitMQ)**
Acts as a reliable message broker to asynchronously exchange control and message data between the Python-based simulation and the TypeScript-based clients. Ensures that no messages are lost and supports scalable, decoupled communication.

#### **Install & Run RabbitMQ**
```sh
docker run -d --hostname rabbitmq \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management
```

### **📊 Database (InfluxDB)**
Stores benchmarking data (latency, message rates, CPU usage).

#### **Install & Run InfluxDB**
```sh
docker run -d --name=influxdb -p 8086:8086 influxdb
```
Then, access the running InfluxDB container:
```sh
docker exec -it <influxdb-container> /bin/sh
```
Setup InfluxDB:
```sh
influx setup
```
Configuration during setup:
- Username: imbench
- Password: password
- Organization: imbench
- Bucket: imbench

### **📈 Grafana (Visualization)**
Stores benchmarking data (latency, message rates, CPU usage).

#### **Install, Run and Access Grafana**
```sh
docker run -d -p 3000:3000 --name=grafana grafana/grafana
```

#### **Connect Grafana to InfluxDB**
1. Go to “Data Sources” → Add InfluxDB
2. URL: http://host.docker.internal:8086 (due to the use of docker-desctop for container management)
3. Database: imbench
4. Set token by looking it up inside the influxdb container:
    ```sh
    influx auth list
    ```

#### **Setup Dashboard for Performance Metrics Visualization**
1. Access grafana in the webbrowser: [http://localhost:3000](http://localhost:3000)
2. Go to "Dashboards" → New → Import
3. Copy dashboard_json_model.json from this project and paste it in (or simply import the file). 
4. Now a few refreshs for the single panels might be needed, if it says "No Data".

### **📦 Deployment**
Stores benchmarking data (latency, message rates, CPU usage).

#### **Build & Run Docker Containers**
```sh
cd denim-on-signal
docker build -t denim-clients-manager -f src/benchmarking/clients-manager/Dockerfile .
docker build -t denim-server -f src/benchmarking/server/Dockerfile .
```

#### **Run Containers**
```sh
docker run -p 8080:8080 --name denim-server --env-file denim-on-signal/src/benchmarking/server/.env -d denim-server
docker run -p 8081:8081 --name denim-clients-manager --env-file denim-on-signal/src/benchmarking/clients-manager/.env -d denim-clients-manager
```

#### **Check running containers**
```sh
docker ps
```

#### **Containers can be stopped and removed (if necessary)**
```sh
docker stop denim-server denim-clients-manager
docker rm denim-server denim-clients-manager
```


### **🤖 User Behavior Simulation (Python)**
Simulates user behavior in an **instant messaging** environment.

#### **Install Dependencies**
```sh
pip install -r requirements.txt
```

#### **Start User Behavior Simulation**
```sh
python3 user-simulation/client_manager.py
```
This will connect to the **DenIM Clients Manager** and control simulated users.



---

## **Running locally**

### **📡 DenIM (TypeScript)**
DenIM handles the **IM server** and **client connections**.

#### **Install & Build**
```sh
cd denim-on-signal
nvm install 16
nvm use 16
mkdir -p src/proto-generated
npm install
npm run proto
npm run build
npm install -g ts-node
```
If error occurs, try:
```sh
npm uninstall @types/markdown-it @types/linkify-it 
npm install @types/markdown-it @types/linkify-it
```

#### **Running DenIM**
##### **1️Start the DenIM Server**
```sh
ts-node ./src/experiments/WebsocketServer.ts
```
This starts a WebSocket server on **port 8080**.
##### **Start the Denim Clients Manager**
```sh
ts-node ./src/benchmarking/clients-manager/ClientsManager.ts
```
This manages multiple IM clients and connects them to the **DenIM server**. It also starts another websocket server on **port 8081**. This allows another service to control behavior of denim-users/clients.

### **🤖 User Behavior Simulation (Python)**
Simulates user behavior in an **instant messaging** environment.

#### **Install Dependencies**
```sh
pip install -r requirements.txt
```

#### **Start User Behavior Simulation**
```sh
python3 user-simulation/client_manager.py
```
This will connect to the **DenIM Clients Manager** and control simulated users.


