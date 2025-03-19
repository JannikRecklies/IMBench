# IMBench
Benchmarking Instant Messaging Systems under Realistic User Behavior

## Setup

### DenIM (TypeScript)
##### Denim Server
##### Denim Clients Manager

#### Denim Clients Manager

### User Behavior Simulation (Python)

### Database (InfluxDB)
- Install docker
- Install & Set Up InfluxDB (docker run -d --name=influxdb -p 8086:8086 influxdb)
- docker exec -it ... /bin/sh into the created docker container
- influx setup (username: imbench, password: password, org: imbench, bucket: imbench)
- Create a database (inlfux )