"use strict";

process.title = "Multithread BNB Bruteforce ";

// Importing required modules
const fs = require('fs');
const cluster = require('cluster');
const numCPUs = require('os').cpus().length;
const blessed = require('blessed');
const ethers = require('ethers');

// BSC provider (you can use any BSC node provider URL)
const provider = new ethers.providers.JsonRpcProvider('https://bsc-dataseed.binance.org/');

// Initializing a Set to store addresses
let addresses = new Set();

// Reading data from a file named 'data.txt'
const data = fs.readFileSync('./data.txt', 'utf8');
// Splitting the data by new line and adding each address to the Set
data.split("\n").forEach(address => {
    if (address.startsWith('0x')) {
        addresses.add(address);
    } else {
        console.error('Error: BNB addresses are not in correct format. Addresses must start with 0x');
        process.exit(1);
    }
});

// Initializing an object to store counts for each worker
let counts = {};

// Initializing an object to store start times for each worker
let startTimes = {};

// Function to generate a private key and check if the corresponding public address is in the Set of addresses
async function generate() {
    // Incrementing the count for the current worker
    counts[cluster.worker.id] = (counts[cluster.worker.id] || 0) + 1;

    // Sending the updated counts to the master process every loop
    process.send({ counts: counts });

    // Generating a new random BNB keypair
    const wallet = ethers.Wallet.createRandom();
    const privateKey = wallet.privateKey;
    const publicKey = wallet.address;

    // Checking if the public address corresponding to the private key is in the Set of addresses
    if (addresses.has(publicKey)) {
        console.log("");
        // Making a beep sound
        process.stdout.write('\x07');
        // Logging success message with the public address in green color
        console.log("\x1b[32m%s\x1b[0m", ">> Match Found: " + publicKey);
        const successString = `Wallet: ${publicKey}\n\nPrivate Key: ${privateKey}`;

        // Saving the wallet and its private key to a file named 'match.txt'
        fs.writeFileSync('./match.txt', successString);
        // Exiting the process
        process.exit();
    }

    // Check the balance of the generated address
    try {
        const balance = await provider.getBalance(publicKey);
        const balanceInEther = ethers.utils.formatEther(balance);

        if (parseFloat(balanceInEther) > 0) {
            console.log("\x1b[32m%s\x1b[0m", `>> Address with Balance Found: ${publicKey} - Balance: ${balanceInEther} BNB`);
            const successString = `Wallet: ${publicKey}\n\nPrivate Key: ${privateKey}\nBalance: ${balanceInEther} BNB`;

            // Saving the wallet, private key, and balance to a file named 'balance_match.txt'
            fs.writeFileSync('./balance_match.txt', successString);
            // Exiting the process
            process.exit();
        }
    } catch (err) {
        console.error(`Error checking balance for address ${publicKey}:`, err);
    }
}

// Checking if the current process is the master process
if (cluster.isMaster) {
    // Creating a blessed screen object
    let screen = blessed.screen({
        smartCSR: true
    });

    // Initializing an array to store boxes for each worker
    let boxes = [];

    // Looping through each CPU and creating a box for each worker
    for (let i = 0; i < numCPUs; i++) {
        let box = blessed.box({
            top: `${i * 100 / numCPUs}%`,
            left: '0%',
            width: '100%',
            height: `${100 / numCPUs}%`,
            content: `Worker ${i + 1} Loop count: 0 Keys/min: N/A (Updated every 60s)`,
            border: {
                type: 'line'
            },
            style: {
                fg: 'green',
                border: {
                    fg: 'green'
                }
            }
        });
        screen.append(box);
        boxes.push(box);
    }

    // Function to update the worker boxes with the average keys generated per minute
    function updateWorkerBoxes() {
        for (let workerId in counts) {
            let elapsedTime = (Date.now() - startTimes[workerId]) / 1000 / 60;
            let keysPerMin = (counts[workerId] / elapsedTime).toFixed(2);
            boxes[workerId - 1].setContent(`Worker ${workerId} Loop count: ${counts[workerId]} Keys/min: ${keysPerMin}`);
        }
        screen.render();
    }

    // Setting an interval to update the worker boxes every minute
    setInterval(updateWorkerBoxes, 60 * 1000);

    // Rendering the screen
    screen.render();

    // Listening for messages from worker processes
    cluster.on('message', (worker, message) => {
        if (message.counts) {
            for (let workerId in message.counts) {
                counts[workerId] = message.counts[workerId];
                if (!startTimes[workerId]) {
                    startTimes[workerId] = Date.now();
                }
            }
        }
    });

    // Forking worker processes for each CPU
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }

    // Listening for exit event of worker processes
    cluster.on('exit', (worker, code, signal) => {
        console.log(`worker ${worker.process.pid} died`);
    });
} else {
    // Setting an interval to run the generate function repeatedly with no delay
    setInterval(generate, 0);
}
