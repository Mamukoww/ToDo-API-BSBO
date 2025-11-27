from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from database import init_db, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from routers import tasks, stats
from scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При запуске приложения
    print("Запуск приложения")
    
    # Инициализируем БД
    await init_db()
    
    # Запускаем планировщик
    start_scheduler()
    
    yield  # Здесь приложение работает
    
    # При завершении работы приложения
    print("Завершение работы приложения")
    stop_scheduler()
    print("Приложение завершило работу")

app = FastAPI(
    title="ToDo лист API",
    description="API для управления задачами с использованием матрицы Эйзенхауэра",
    version="2.0.0",
    contact={
        "name": "Мамуков Лаврентий Михайлович",
    },
    lifespan=lifespan
)

# Подключаем роутеры
app.include_router(tasks.router, prefix="/api/v2")
app.include_router(stats.router, prefix="/api/v2")

@app.get("/")
async def read_root() -> dict:
    return {
        "message": "Task Manager API - Управление задачами по матрице Эйзенхауэра",
        "version": "2.0.0",
        "database": "PostgreSQL (Supabase)",
        "docs": "/docs",
        "redoc": "/redoc",
    }

@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_async_session)
) -> dict:
    """
    Проверка здоровья API и динамическая проверка подключения к БД.
    """
    try:
        # Пытаемся выполнить простейший запрос к БД
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {
        "status": "healthy",
        "database": db_status
    }