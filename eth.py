import os
import asyncio
import aiohttp
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from eth_account import Account
from eth_utils import to_checksum_address

ALCHEMY_URL = "https://eth-mainnet.g.alchemy.com/v2/eVSWYz-Y7WaD05gKy3v7sgm2oHpCCwG1"
CONCURRENT_TASKS = 100  # Number of concurrent tasks

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
    async with session.post(ALCHEMY_URL, json=payload) as response:
        if response.status == 200:
            result = await response.json()
            balance = int(result['result'], 16)
            return balance / 1e18  # Convert from wei to ether
        else:
            return 0

async def process_address():
    mnemonic = generate_mnemonic()
    address = derive_eth_address(mnemonic)
    
    async with aiohttp.ClientSession() as session:
        balance = await check_balance(session, address)
    
    if balance > 0:
        with open('gg.txt', 'a') as f:
            f.write(f"Mnemonic: {mnemonic}\nAddress: {address}\nBalance: {balance} ETH\n\n")
        print(f"Found address with balance: {address} - {balance} ETH")
    else:
        print(f"Checked address: {address} - No balance")

async def main():
    while True:
        tasks = [asyncio.create_task(process_address()) for _ in range(CONCURRENT_TASKS)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
