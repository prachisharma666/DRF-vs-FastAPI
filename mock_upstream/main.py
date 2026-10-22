import asyncio
from fastapi import FastAPI,HTTPException
app=FastAPI()

@app.get("/search.json")
async def search(q:str="",limit:int=10):
    await asyncio.sleep(0.2)
    return {"docs": [{"key": f"/works/OL{i}W", "title": f"Book {i}",
            "author_name": ["Author"], "first_publish_year": 1950 + i,
            "cover_i": i} for i in range(limit)]}

@app.get("/works/{work_id}.json")
async def work(work_id: str):
    await asyncio.sleep(0.2)
    if work_id == "OL404W":          # magic ID to test 404 handling
        raise HTTPException(404)
    return {"key": f"/works/{work_id}", "title": f"Book {work_id}", "covers": [1]}