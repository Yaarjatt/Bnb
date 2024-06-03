import os
import hashlib
import ecdsa
import base58
from mnemonic import Mnemonic
import asyncio
import aiohttp
import random

class BalanceChecker:
    def __init__(self, api_keys):
        self.base_url = "https://api.blockcypher.com/v1/btc/main/addrs/"
        self.api_keys = api_keys

    async def check_balance(self, address):
        try:
            random.shuffle(self.api_keys)  # Shuffle API keys before each balance check
            for api_key in self.api_keys:
                print(f"Checking balance for address: {address.decode('utf-8')} (API key: {api_key})")
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.base_url + address.decode('utf-8') + "?token=" + api_key) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data['balance'], api_key  # Return balance and API key
                        elif response.status != 429:  # Only rotate if not rate limited
                            print(f"Error: {response.status}, {await response.text()}")
                            return 0, api_key
            print("All API keys are rate limited.")
            return 0, "No API key available"
        except Exception as e:
            print(f"Error checking balance for address {address}: {e}")
            return 0, "Error"

async def generate_and_check_address(balance_checker):
    while True:
        # Generate 12-word mnemonic phrase
        mnemonic = generate_12_word_mnemonic()
        # Derive Bitcoin address from mnemonic
        btc_address = mnemonic_to_address(mnemonic)

        # Check balance of the address
        balance, api_key = await balance_checker.check_balance(btc_address)

        if balance > 0:
            print(f"Found funded address: {btc_address.decode('utf-8')} (Checked with API key: {api_key})")
            save_address(btc_address)

def generate_12_word_mnemonic():
    # Generate a BIP39 12-word mnemonic phrase
    mnemo = Mnemonic("english")
    return mnemo.generate(128)  # 128 bits for 12 words

def mnemonic_to_address(mnemonic):
    # Derive Bitcoin address from mnemonic
    seed = Mnemonic("english").to_seed(mnemonic)
    private_key = hashlib.sha256(seed).digest()
    public_key = private_key_to_public_key(private_key)
    btc_address = public_key_to_address(public_key)
    return btc_address

def private_key_to_public_key(private_key):
    # Generate public key from private key using elliptic curve cryptography (secp256k1)
    signing_key = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
    verifying_key = signing_key.get_verifying_key()
    public_key = b"\04" + verifying_key.to_string()
    return public_key

def public_key_to_address(public_key):
    # Perform SHA-256 hash on the public key
    sha256_hash = hashlib.sha256(public_key).digest()
    # Perform RIPEMD-160 hash on the result of SHA-256
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    # Add network byte (0x00 for Bitcoin mainnet)
    network_byte = b"\x00"
    # Concatenate network byte and RIPEMD-160 hash
    extended_hash = network_byte + ripemd160_hash
    # Perform SHA-256 hash on the extended RIPEMD-160 hash
    hash_hash = hashlib.sha256(extended_hash).digest()
    # Perform SHA-256 hash on the result of the previous SHA-256 hash
    hash_hash = hashlib.sha256(hash_hash).digest()
    # Take the first 4 bytes of the second SHA-256 hash (checksum)
    checksum = hash_hash[:4]
    # Concatenate the extended RIPEMD-160 hash and the checksum
    binary_address = extended_hash + checksum
    # Convert the binary address to Base58 encoding (Bitcoin address format)
    btc_address = base58.b58encode(binary_address)
    return btc_address

def save_address(address):
    with open('gg.txt', 'a') as file:
        file.write(address.decode('utf-8') + '\n')

async def main():
    # Replace 'YOUR_API_KEYS' with your actual list of API keys
    api_keys = ['f54f502d4ba04ce0867d84e6e81165c8', '72e47637d6ed4b6c87c78418f1c0a1ed', '0d310828cd5e444e99a0d1358057d4ea','79e1d3cd4c424fba9467905213792723','56422303468b43928d6a210c15004223','a6c3ffc1e962453b9d1a0032763d9d01']
    # Initialize the balance checker
    balance_checker = BalanceChecker(api_keys)

    # Create tasks for key generation and balance checking
    tasks = []
    for _ in range(10):  # You can adjust the number of tasks
        task = asyncio.create_task(generate_and_check_address(balance_checker))
        tasks.append(task)

    # Wait for all tasks to finish
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
