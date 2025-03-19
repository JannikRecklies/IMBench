# Use official Node.js 16 base image
FROM node:16

# Set working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json before installing dependencies
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY . .

# Ensure the proto-generated directory exists
RUN mkdir -p src/proto-generated

# Generate protobufs and build the app
RUN npm run proto
RUN npm run build

# Install ts-node globally (needed for running TypeScript server)
RUN npm install -g ts-node

# Expose WebSocket server port
EXPOSE 8080

# Start the WebSocket server
CMD ["ts-node", "./src/benchmarking/server/WebsocketServer.ts", "--q=1"]