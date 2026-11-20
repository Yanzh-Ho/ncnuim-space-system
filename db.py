from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from db_config import DB_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
	app.state.pool = AsyncConnectionPool(
		conninfo=DB_URL,
		kwargs={"row_factory": dict_row, "autocommit": True},
		open=False,
	)
	await app.state.pool.open()
	print("✅ Connected to DB")
	yield
	await app.state.pool.close()
	print("🛑 Disconnected from DB")


async def getDB(request: Request):
	async with request.app.state.pool.connection() as conn:
		yield conn