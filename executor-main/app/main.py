from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio
# from app import pythonExecutor

app = FastAPI()

# Define the data structure for the request body
class Item(BaseModel):
    name: str
    price: str
    is_offer: bool
    item_name: Optional[str] = None

# In-memory data store
items_store = {}

@app.put("/items/{item_id}")
async def update_item(item: Item, item_id: int):
    """
    Stores an item in the in-memory data store.
    """
    item.item_name = item.name
    items_store[item_id] = item
    return item

@app.get("/items/{item_id}")
async def get_item(item_id: int, q: str = None):
    """
    Retrieves an item from the in-memory data store.
    """
    if item_id not in items_store:
        raise HTTPException(status_code=404, detail="Item not found")
    item = items_store[item_id]
    response = {"item_id": item_id, "data": item}
    if q:
        response["query"] = q
    return response

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.post("/evaluate")
async def evaluate(request: Request):
    await asyncio.sleep(10)
    return {"output": 2}

    evaluator = SafeEval()
    safe_globals = {"__builtins__": {}}

    try:
        result = evaluator.eval(code, globals=safe_globals)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    
    
    
    
    # TODO: Your evaluation code here
    return {"output": 1}