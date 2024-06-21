import os
import asyncio
import aiohttp
import time
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from eth_account import Account
from eth_utils import to_checksum_address

ALCHEMY_URL = "https://eth-mainnet.g.alchemy.com/v2/eVSWYz-Y7WaD05gKy3v7sgm2oHpCCwG1"
CONCURRENT_TASKS = 200  # Increased concurrent tasks
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def generate_mnemonic():
    return Bip39MnemonicGenerator().FromEntropy(os.urandom(32)).ToStr()

def derive_eth_address(mnemonic):
    seed = Bip39SeedGenerator(mnemonic).Generate()
    bip44_mst_ctx = Bip44.FromSeed(seed, Bip44Coins.ETHEREUM)
    bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
    bip44_chain_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
    bip44_addr_ctx = bip44_chain_ctx.AddressIndex(0)
    private_key = bip44_addr_ctx.PrivateKey().Raw().ToHex()
    address = Account.from_key(private_key).address
    return to_checksum_address(address)

async def check_balance(session, address):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1
    }
    try:
        async with session.post(ALCHEMY_URL, json=payload, timeout=5) as response:
            if response.status == 200:
                result = await response.json()
                balance = int(result['result'], 16)
                return balance / 1e18  # Convert from wei to ether
            else:
                print(f"Error response: {response.status}")
                return 0
    except asyncio.TimeoutError:
        print("Request timed out")
        return 0
    except Exception as e:
        print(f"Error checking balance: {str(e)}")
        return 0

async def send_telegram_message(session, message):
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        async with session.post(TELEGRAM_API_URL, json=payload, timeout=5) as response:
            if response.status != 200:
                print(f"Failed to send Telegram message. Status: {response.status}")
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")

async def process_address(session):
    mnemonic = generate_mnemonic()
    address = derive_eth_address(mnemonic)
    
    balance = await check_balance(session, address)
    
    if balance > 0:
        message = f"Found address with balance!\nMnemonic: {mnemonic}\nAddress: {address}\nBalance: {balance} ETH"
        print(message)
        with open('gg.txt', 'a') as f:
            f.write(message + "\n\n")
        await send_telegram_message(session, message)
    return 1  # Return 1 to count processed addresses

async def main():
    processed = 0
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        while True:
            tasks = [asyncio.create_task(process_address(session)) for _ in range(CONCURRENT_TASKS)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processed += sum(r for r in results if isinstance(r, int))

            elapsed_time = time.time() - start_time
            speed = processed / elapsed_time

            print(f"Processed: {processed}, Speed: {speed:.2f} addresses/second")

if __name__ == "__main__":
    asyncio.run(main())
