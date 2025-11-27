from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from models.task import Task
from datetime import datetime, timezone


# Глобальная переменная для хранения экземпляра планировщика
scheduler = AsyncIOScheduler()

async def update_task_urgency():
    """
    Асинхронная функция для обновления срочности (квадранта) всех незавершенных задач.
    Пересчитывает квадрант на основе текущей даты и дедлайна задачи.
    """
    print("Запуск автоматического обновления срочности задач.")
    
    # Получаем сессию БД
    db = await get_async_session().__anext__()
    
    try:
        # Получаем все незавершенные задачи
        result = await db.execute(
            select(Task).where(Task.completed == False)
        )
        tasks = result.scalars().all()
        
        updated_count = 0
        
        for task in tasks:
            # Сохраняем старый квадрант для сравнения
            old_quadrant = task.quadrant
            
            # Вычисляем новый квадрант
            new_quadrant = task.calculate_quadrant()
            
            # Если квадрант изменился, обновляем задачу
            if old_quadrant != new_quadrant:
                task.quadrant = new_quadrant
                updated_count += 1
        
        # Сохраняем изменения в БД
        if updated_count > 0:
            await db.commit()
            print(f"Обновлено {updated_count} задач.")
        else:
            print("Обновлений по задачам нет")
            
    except Exception as e:
        await db.rollback()
        print(f"Ошибка при обновлении: {str(e)}")
        raise
    finally:
        await db.close()

def start_scheduler():
    """
    Запускает планировщик с настройками по умолчанию:
    - Ежедневно в 9:00 утра
    - Каждые 5 минут
    """
    if not scheduler.running:
        # Добавляем задачу на ежедневное выполнение в 9:00
        scheduler.add_job(
            update_task_urgency,
            trigger=CronTrigger(hour=9, minute=0),
            id='daily_urgency_update',
            name='Обновление срочности задач',
            replace_existing=True
        )
        
        """# Добавляем задачу на выполнение каждые 5 минут
        scheduler.add_job(
            update_task_urgency,
            trigger='interval',
            minutes=5,
            id='frequent_urgency_update',
            name='Тестовое обновление срочности',
            replace_existing=True
        )"""
        
        # Запускаем планировщик
        scheduler.start()


def stop_scheduler():
    """Останавливает планировщик"""
    if scheduler.running:
        scheduler.shutdown()
