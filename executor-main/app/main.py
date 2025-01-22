import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    import helpers
    from PythonSafeEval.safe_eval import SafeEvalJavaScript, SafeEvalPython
except:
    from app import helpers
    from app.PythonSafeEval.safe_eval import SafeEvalJavaScript, SafeEvalPython

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
    try:
        # Parse the incoming JSON request
        body = await request.json()
        code = body.get("code")
        scope = body.get("scope", {})
        language = body.get("language")

        # Validate required fields
        if not code or not language:
            return JSONResponse(
                status_code=400,
                content={"error": "Both 'code' and 'language' fields are required."},
            )

        # Choose the appropriate evaluator
        if language == "python":
            evaluator = SafeEvalPython(
                version="3.8", modules=[]
            )  # TODO: add more modules here that could work.  need to figure out what you can do
        elif language == "javascript":
            evaluator = SafeEvalJavaScript(version="16", modules=[])
        else:
            return JSONResponse(
                status_code=400, content={"error": f"Unsupported language: {language}"}
            )

        # Evaluate the code
        result, hashed_s = evaluator.eval(code=code, scope=scope)

        out = result.get("stdout")
        err = result.get("stderr")
        returncode = result.get("returncode")
        if returncode != 0:
            return JSONResponse(
                status_code=400, content={"error": f"An error occurred: {err}"}
            )

        if returncode == 0:
            output = helpers.extract_value_after_return(out, hashed_s)
            return JSONResponse(
                status_code=200, content={"output": output, "stdout": out}
            )

    except Exception as e:
        # Handle unexpected errors
        return JSONResponse(
            status_code=500,
            content={
                "error": f"An error occurred: {str(e)}",
            },
        )


if __name__ == "__main__":
    evaluator = SafeEvalJavaScript(
        version="16", modules=[]
    )  # TODO: add more modules here that could work.  need to figure out what you can do
    result = evaluator.eval(code="return 1;", scope={"x": 2})
    print("asdfasdf", result)

    evaluator = SafeEvalPython(version="3.8", modules=["numpy"])
    result = evaluator.eval(code="print('asdf')", scope={})
    print("asdfasdf", result)
