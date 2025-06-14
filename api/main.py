from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

@app.get("/")
async def health_check():
    return "The health check is successful"

