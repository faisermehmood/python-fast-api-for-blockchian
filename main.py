from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from datetime import datetime
from pymongo import MongoClient
from web3 import Web3

import requests

app = FastAPI()

# MongoDB Setup
client = MongoClient("mongodb://localhost:27017/")
db = client["markus-assignment"]
balances_collection = db["balances"]

# Connect with Etherium Node via Infura
w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/2504bf87548a4cafb59be32861e0f115"))

# CoinGecko Api get Etherium value in USD 
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
TOKEN_ID = "Ethereum"  # Name Id parameter for coingecko Api

#DataModel region
class WalletBalance(BaseModel):
    wallet: str

class BalanceHistory(BaseModel):
    timestamp: str
    value: float

class WalletBalanceResponse(BaseModel):
    wallet: str
    last_update_time: str
    current_balance: float
    current_balance_usd: float
    history: List[BalanceHistory]
#end datamodel region
def get_current_token_price():
    response = requests.get(f"{COINGECKO_API_URL}/simple/price", params={"ids": TOKEN_ID, "vs_currencies": "usd"})
    data = response.json()
    return data["ethereum"]["usd"]

def get_wallet_balance(wallet: str):
    # Fetch token balance from blockchain node
    checksum_address = w3.to_checksum_address(wallet)

    # Fetch token balance from ethereum node
    token_balance = w3.eth.get_balance(checksum_address)
    #token_balance = w3.eth.get_balance(wallet)
    token_balance_usd = token_balance * get_current_token_price()

    # Get current timestamp
    current_timestamp = datetime.utcnow().isoformat()

    # Save balance to MongoDB
    balances_collection.insert_one({
        "wallet": wallet,
        "timestamp": current_timestamp,
        "balance": token_balance,
        "balance_usd": token_balance_usd
    })

    return WalletBalanceResponse(
        wallet=wallet,
        last_update_time=current_timestamp,
        current_balance=token_balance,
        current_balance_usd=token_balance_usd,
        history=[]
    )
# Get the balance and token details
@app.post("/get_balance/")
async def get_balance(wallet_balance: WalletBalance):
    return get_wallet_balance(wallet_balance.wallet)
#retrive the history from mongo db
@app.get("/get_history/")
async def get_history(wallet: str):
    # Fetch balance history from MongoDB
    history = []
    cursor = balances_collection.find({"wallet": wallet})
    for document in cursor:
        history.append(BalanceHistory(timestamp=document["timestamp"], value=document["balance_usd"]))
    return history

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
