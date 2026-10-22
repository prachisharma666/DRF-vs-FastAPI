import os
from contextlib import asynccontextmanager
from typing import Literal
import httpx
from fastapi import FastAPI,HTTPException,Query,Path
from pydantic import BaseModel,Field,model_validator

UPSTREAM_URL=os.getenv("UPSTREAM_URL","https://openlibrary.org")
HEADERS={"User-Agent":"BookExplorer/0.1 (prachisharma062006@gmail.com)"}

@asynccontextmanager
async def lifespan(app):
    app.state.client=httpx.AsyncClient(base_url=UPSTREAM_URL,headers=HEADERS,timeout=5)
    yield
    await app.state.client.aclose()

app=FastAPI(title="Book Explorer-FastAPI",lifespan=lifespan)
READING_LIST:list[dict]=[]

class Book(BaseModel):
    work_id:str
    title:str
    authors:list[str]=[]
    first_publish_year:int|None=None
    cover_url:str|None=None

class ReadingListItem(BaseModel):
    work_id:str=Field(pattern=r"^OL\d+W$")
    status:Literal["want_to_read","reading","finished"]
    rating:int|None=Field(default=None,ge=1,le=5)
    notes:str|None=Field(default=None,max_length=500)

    @model_validator(mode="after")
    def rating_only_if_finished(self):
        if self.rating is not None and self.status!="finished":
            raise ValueError("rating is only allowed when status is 'finished'")
        return self

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.get("/api/books/{work_id}", response_model=Book)
async def get_book(work_id: str = Path(pattern=r"^OL\d+W$")):
    try:
        r = await app.state.client.get(f"/works/{work_id}.json")
    except httpx.HTTPError:
        raise HTTPException(502, "Upstream error")
    if r.status_code == 404:
        raise HTTPException(404, "Work not found")
    if r.status_code >= 400:
        raise HTTPException(502, "Upstream error")
    d = r.json()
    covers = d.get("covers") or []
    return Book(work_id=work_id, title=d["title"],
                cover_url=f"https://covers.openlibrary.org/b/id/{covers[0]}-M.jpg" if covers else None)

@app.get("/api/search", response_model=list[Book])
async def search(q:str=Query(min_length=1),limit:int=Query(10,ge=1,le=50)):
    try:
        r=await app.state.client.get("/search.json",params={"q":q,"limit":limit,
            "fields":"key,title,author_name,first_publish_year,cover_i"})
        r.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(502, "Upstream error")
    return [Book(work_id=d["key"].split("/")[-1],title=d["title"],
                 authors=d.get("author_name",[]),
                 first_publish_year=d.get("first_publish_year"),
                 cover_url=f"https://covers.openlibrary.org/b/id/{d['cover_i']}-M.jpg"
                           if d.get("cover_i") else None)
            for d in r.json()["docs"]]

@app.post("/api/reading-list", response_model=ReadingListItem, status_code=201)
async def add_to_list(item: ReadingListItem):
    READING_LIST.append(item.model_dump())
    return item

@app.get("/api/reading-list", response_model=list[ReadingListItem])
async def get_list():
    return READING_LIST