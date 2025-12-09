from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Optional
from datetime import datetime, timezone, date, timedelta
from schemas import TaskCreate, TaskUpdate, TaskResponse
from database import init_db, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import Task
from dependencies import get_current_user
from models import User, UserRole


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Tasks not found"}},
)

"""@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    # Сессия базы данных (автоматически через Depends
    db: AsyncSession = Depends(get_async_session)) -> List[TaskResponse]: 
    result = await db.execute(select(Task)) # Выполняем SELECT запрос
    tasks = result.scalars().all() # Получаем все объекты
    # FastAPI автоматически преобразует Task → TaskResponse
    return tasks"""

@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    # Сессия базы данных (автоматически через Depends
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user) 
) -> List[TaskResponse]:
    if current_user.role.value == "admin":
        result = await db.execute(select(Task))
    else:
        result = await db.execute(
            select(Task).where(Task.user_id == current_user.id)
        )

    tasks = result.scalars().all()

    tasks_with_days = []
    for task in tasks:
        days_until_deadline = None
        if task.deadline_at:
            delta = task.deadline_at - datetime.now(task.deadline_at.tzinfo)
            days_until_deadline = delta.days
            
        task_data = task.to_dict()
        task_data['days_until_deadline'] = days_until_deadline
        tasks_with_days.append(TaskResponse(**task_data))
    
    return tasks_with_days


@router.get("/quadrant/{quadrant}",
            response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends (get_current_user)
) -> List[TaskResponse]:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4" # текст, который будет выведен пользователю
        )

    if current_user.role.value == "admin":
        result = await db.execute(
            select (Task).where(Task.quadrant == quadrant)
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.quadrant == quadrant,
                Task.user_id == current_user.id
            )
        )

    tasks = result.scalars().all()
    return tasks

@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user) 
) -> List[TaskResponse]:
    keyword = f"%{q.lower()}%" # %keyword% для LIKE
    if current_user.role.value == "admin":
        result = await db.execute(
        select (Task).where(
            (Task.title.ilike(keyword)) |
            (Task.description.ilike(keyword))
        )
    )
    else:
        result = await db.execute(
            select (Task).where(
                Task.user_id == current_user.id,
                (Task.title.ilike(keyword)) |
                (Task.description.ilike (keyword))
        )
    )        
    tasks = result.scalars().all()
    if not tasks:
        raise HTTPException(status_code=404, detail="По данному запросу ничего не найдено")
    return tasks

@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status (
    status: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends (get_current_user)
) -> List[TaskResponse]:
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=404, detail="Недопустимый статус. Используйте: completed или pending")
    is_completed = (status == "completed")
    if current_user.role.value == "admin":
        result = await db.execute(
            select(Task).where(Task.completed == is_completed)
        )
    else:
        result = await db. execute(
            select(Task).where(
                Task. completed == is_completed, 
                Task.user_id == current_user.id
        )
    )    
    tasks = result.scalars().all()
    return tasks

@router.get("/today", response_model=List[TaskResponse])
async def get_tasks_due_today(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time()).astimezone()
    end_of_day = datetime.combine(today, datetime.max.time()).astimezone()
    
    if current_user.role.value == "admin":
        result = await db.execute(
            select(Task).where(
                Task.deadline_at >= start_of_day,
                Task.deadline_at <= end_of_day
            )
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                Task.deadline_at >= start_of_day,
                Task.deadline_at <= end_of_day
            )
        )
        
    tasks = result.scalars().all()
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )

    days_until_deadline = None
    if task.deadline_at:
        delta = task.deadline_at - datetime.now(task.deadline_at.tzinfo)
        days_until_deadline = delta.days

    task_data = task.to_dict()
    task_data['days_until_deadline'] = days_until_deadline

    if task.deadline_at is not None and days_until_deadline is not None and days_until_deadline < 0:
        task_data['status_message'] = "Задача просрочена"
    else:
        task_data['status_message'] = "Все идет по плану!"
    
    return TaskResponse(**task_data)

# Мы указываем, что эндпоинт будет возвращать данные,
# соответствующие схеме TaskResponse
@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    # Создаем экземпляр Task из данных запроса
    db_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        deadline_at=task.deadline_at,
        completed=False,
        created_at=datetime.now(timezone.utc),
        user_id=current_user.id
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
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    # Получаем задачу по ID
    result = await db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    
    if db_task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Проверяем права доступа
    if current_user.role.value != "admin" and db_task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для обновления этой задачи"
        )
    
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

    
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    # Получаем задачу по ID
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Проверяем права доступа
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )
    
    # Помечаем задачу как выполненную
    task.completed = True
    task.completed_at = datetime.now(timezone.utc)
    
    # Сохраняем изменения в базе данных
    await db.commit()
    await db.refresh(task)
    
    # Добавляем days_until_deadline и status_message в ответ
    task_data = task.to_dict()
    days_until_deadline = None
    if task.deadline_at:
        delta = task.deadline_at - datetime.now(task.deadline_at.tzinfo)
        days_until_deadline = delta.days
    
    task_data['days_until_deadline'] = days_until_deadline
    if task.deadline_at is not None and days_until_deadline is not None and days_until_deadline < 0:
        task_data['status_message'] = "Задача просрочена"
    else:
        task_data['status_message'] = "Все идет по плану!"
    
    return TaskResponse(**task_data)

@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Проверяем права доступа
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления этой задачи"
        )
    
    # Сохраняем информацию для ответа
    deleted_task_info = {
        "id": task.id,
        "title": task.title,
        "message": "Задача успешно удалена"
    }
    
    # Удаляем задачу из базы данных
    await db.delete(task)
    await db.commit()
    
    return deleted_task_info