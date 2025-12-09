from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any

from database import get_async_session
from models import User, Task, UserRole
from dependencies import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.get("/users", response_model=List[Dict[str, Any]])
async def get_all_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """
    Получение списка всех пользователей с количеством их задач.
    Доступно только для администраторов.
    """
    # Проверяем, является ли пользователь администратором
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения этого действия"
        )
    
    # Получаем всех пользователей с количеством их задач
    result = await db.execute(
        select(
            User.id,
            User.email,
            User.role,
            func.count(Task.id).label('task_count')
        ).outerjoin(
            Task, User.id == Task.user_id
        ).group_by(User.id)
    )
    
    users = result.all()
    
    # Форматируем результат
    return [
        {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "task_count": user.task_count or 0
        }
        for user in users
    ]
