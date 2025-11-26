from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from schemas import TaskCreate, TaskUpdate, TaskResponse
from database import init_db, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import Task

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Tasks not found"}},
)

@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    # Сессия базы данных (автоматически через Depends
    db: AsyncSession = Depends(get_async_session)) -> List[TaskResponse]: 
    result = await db.execute(select(Task)) # Выполняем SELECT запрос
    tasks = result.scalars().all() # Получаем все объекты
    # FastAPI автоматически преобразует Task → TaskResponse
    return tasks

@router.get("/quadrant/{quadrant}",
            response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session)
) -> List[TaskResponse]:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4" # текст, который будет выведен пользователю
        )
    # SELECT * FROM tasks WHERE quadrant = 'Q1'
    result = await db.execute(
        select(Task).where(Task.quadrant == quadrant)
    )
    tasks = result.scalars().all()
    return tasks

@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session)
) -> List[TaskResponse]:
    keyword = f"%{q.lower()}%" # %keyword% для LIKE
    # SELECT * FROM tasks
    # WHERE LOWER(title) LIKE '%keyword%'
    # OR LOWER(description) LIKE '%keyword%'
    result = await db.execute(
        select(Task).where(
            (Task.title.ilike(keyword)) |
            (Task.description.ilike(keyword))
        )
    )
    tasks = result.scalars().all()
    if not tasks:
        raise HTTPException(status_code=404, detail="По данному запросу ничего не найдено")
    return tasks

    
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
) -> TaskResponse:
    # SELECT * FROM tasks WHERE id = task_id
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    # Получаем одну задачу или None
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task

# Мы указываем, что эндпоинт будет возвращать данные,
# соответствующие схеме TaskResponse
@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session)
) -> TaskResponse:
    # Создаем экземпляр Task из данных запроса
    db_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        deadline_at=task.deadline_at,
        completed=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # Устанавливаем квадрант на основе важности и срочности
    db_task.quadrant = db_task.calculate_quadrant()
    
    # Добавляем задачу в сессию
    db.add(db_task)
    await db.commit()  # Сохраняем изменения в БД
    await db.refresh(db_task)  # Обновляем объект данными из БД
    
    return db_task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session)
) -> TaskResponse:
    # Получаем задачу по ID
    result = await db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    
    if db_task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Флаг для отслеживания изменения полей, влияющих на квадрант
    quadrant_needs_update = False
    
    # Обновляем поля, если они были переданы
    if task_update.title is not None:
        db_task.title = task_update.title
    if task_update.description is not None:
        db_task.description = task_update.description
    if task_update.is_important is not None:
        db_task.is_important = task_update.is_important
        quadrant_needs_update = True
    if task_update.deadline_at is not None:
        db_task.deadline_at = task_update.deadline_at
        quadrant_needs_update = True
    if task_update.completed is not None:
        db_task.completed = task_update.completed
        if task_update.completed:
            db_task.completed_at = datetime.now(timezone.utc)
        else:
            db_task.completed_at = None
    await db.refresh(task) # Обновить объект из БД

    return task
    
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    task.completed = True
    task.completed_at = datetime.now()

    await db.commit()
    await db.refresh(task)

    return task

@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
) -> dict:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    # Сохраняем информацию для ответа
    deleted_task_info = {
        "id": task.id,
        "title": task.title
    }
    await db.delete(task) # Помечаем для удаления
    await db.commit() # DELETE FROM tasks WHERE id = task_id
    return {
        "message": "Задача успешно удалена",
        "id": deleted_task_info["id"],
        "title": deleted_task_info["title"]
    }