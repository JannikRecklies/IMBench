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
        
    });

    client2.on("message", (data) => {
        console.log(`📩 Client 2 received from ${data.sender}: ${data.message}`);
        
    });


    await client1.regularKeyRequest("2")
    await client2.regularKeyRequest("1")

    // Start conversation AFTER ensuring connections are stable
    setTimeout(async () => {
        console.log("📤 Client 1 sending initial message...");
        let msg = await client1.createMessage("Hello from client 1!", "2")
        await client1.sendMessage(msg);
    }, 2000);

}

// ✅ No infinite loop needed! Just keep the process alive
run();