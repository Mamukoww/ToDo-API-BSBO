from fastapi import APIRouter, HTTPException, Query, Response, status
from typing import List, Dict, Any
from datetime import datetime
from schemas import TaskBase, TaskCreate, TaskUpdate, TaskResponse
from database import tasks_db

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
    responses={404: {"description": "Stats not found"}},
)

@router.get("")
async def get_tasks_stats() -> dict:
    total_tasks = len(tasks_db)

    by_quadrant = {
        "Q1": len([t for t in tasks_db if t["quadrant"] == "Q1"]),
        "Q2": len([t for t in tasks_db if t["quadrant"] == "Q2"]),
        "Q3": len([t for t in tasks_db if t["quadrant"] == "Q3"]),
        "Q4": len([t for t in tasks_db if t["quadrant"] == "Q4"]),
    }

    by_status = {
        "completed": len([t for t in tasks_db if t["completed"]]),
        "pending": len([t for t in tasks_db if not t["completed"]]),
    }

    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": by_status
    }