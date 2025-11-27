from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from models import Task
from database import get_async_session
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
router = APIRouter(
    prefix="/stats",
    tags=["statistics"]
)

@router.get("/", response_model=dict)
async def get_tasks_stats(db: AsyncSession = Depends(get_async_session)) -> dict:
    result = await db.execute(select(Task))
    tasks = result.scalars().all()
    total_tasks = len(tasks)
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    by_status = {"completed": 0, "pending": 0}
    
    for task in tasks:
        if task.quadrant in by_quadrant:
            by_quadrant[task.quadrant] += 1
        if task.completed:
            by_status["completed"] += 1
        else:
            by_status["pending"] += 1

    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": by_status
    }

@router.get("/deadlines", response_model=List[Dict[str, Any]])
async def get_pending_tasks_deadlines(
    db: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """
    Возвращает список невыполненных задач с информацией о дедлайнах.
    
    Для каждой задачи возвращается:
    - id: идентификатор задачи
    - title: название задачи
    - description: описание задачи
    - deadline_at: крайний срок выполнения
    - days_remaining: количество дней до дедлайна (None если дедлайн не установлен)
    - is_overdue: просрочена ли задача
    """
    # Получаем все невыполненные задачи с установленным дедлайном
    result = await db.execute(
        select(Task).where(
            and_(
                Task.completed == False,
                Task.deadline_at.isnot(None)
            )
        ).order_by(Task.deadline_at.asc())
    )
    tasks = result.scalars().all()
    
    now = datetime.now(timezone.utc)
    
    # Формируем список задач с информацией о дедлайнах
    tasks_with_deadlines = []
    for task in tasks:
        if not task.deadline_at:
            continue
            
        delta = task.deadline_at - now
        days_remaining = delta.days + 1  # +1 чтобы считать полные дни
        
        tasks_with_deadlines.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "deadline_at": task.deadline_at,
            "days_remaining": max(0, days_remaining) if days_remaining > 0 else 0,
            "is_overdue": days_remaining < 0,
            "quadrant": task.quadrant,
            "is_important": task.is_important
        })
    
    return tasks_with_deadlines
