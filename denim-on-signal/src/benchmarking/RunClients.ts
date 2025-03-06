import { ClientWrapper } from "./ClientWrapper";

const serverAddress = "wss://127.0.0.1:8080";

async function run() {
    let client1 = new ClientWrapper("1", undefined, serverAddress);
    let client2 = new ClientWrapper("2", undefined, serverAddress);

    await client1.initialize();
    await client2.initialize();

    console.log("✅ Clients initialized and connected!");

    // 🔹 React when a message is received
    client1.on("message", (data) => {
        console.log(`📩 Client 1 received from ${data.sender}: ${data.message}`);
        setTimeout(() => {
            console.log("📤 Client 1 responding...");
            client1.sendMessage("Hello from client 1!", data.sender);
        }, 5000);
    });

    client2.on("message", (data) => {
        console.log(`📩 Client 2 received from ${data.sender}: ${data.message}`);
        setTimeout(() => {
            console.log("📤 Client 2 responding...");
            client2.sendMessage("Hello from client 2!", data.sender);
        }, 5000);
    });

    // Start conversation AFTER ensuring connections are stable
    setTimeout(async () => {
        console.log("📤 Client 1 sending initial message...");
        await client1.sendMessage("Hello from client 1!", "2")
    }, 2000);

}

// ✅ No infinite loop needed! Just keep the process alive
run();