from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from database import Base

class Task(Base):
    __tablename__ = "tasks"
    id = Column(
        Integer,
        primary_key=True, # Первичный ключ
        index=True, # Создать индекс для быстрого поиска
        autoincrement=True # Автоматическая генерация
    )

    title = Column(
        Text, # Text = текст неограниченной длины
        nullable=False # Не может быть NULL
    )

    description = Column(
        Text,
        nullable=True # Может быть NULL
    )

    is_important = Column(
        Boolean,
        nullable=False,
        default=False # По умолчанию False
    )

    deadline_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True
    )

    quadrant = Column(
        String(2), # Максимум 2 символа: "Q1", "Q2", "Q3", "Q4"
        nullable=False
    )

    completed = Column(
        Boolean,
        nullable=False,
        default=False
    )
 
    created_at = Column(
        DateTime(timezone=True), # С поддержкой часовых поясов
        server_default=func.now(), # Автоматически текущее время
        nullable=False
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True # NULL пока задача не завершена
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', quadrant='{self.quadrant}')>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "is_important": self.is_important,
            "deadline_at": self.deadline_at,
            "quadrant": self.quadrant,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }

    def calculate_quadrant(self) -> str:
        """Определяет квадрант матрицы Эйзенхауэра на основе важности и срочности"""
        from datetime import datetime, timedelta
        
        is_urgent = False
        if self.deadline_at:
            days_until_deadline = (self.deadline_at - datetime.now(self.deadline_at.tzinfo)).days
            is_urgent = days_until_deadline <= 3
            
        if self.is_important and is_urgent:
            return "Q1"
        elif self.is_important and not is_urgent:
            return "Q2"
        elif not self.is_important and is_urgent:
            return "Q3"
        else:
            return "Q4"