from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings  # useremo la configurazione da qui

client = AsyncIOMotorClient(settings.mongo_uri)  # es: "mongodb://assignments-db:27017"
db = client[settings.mongo_db_name]             # es: "assignmentsDB"

class AssignmentRepository:
    def __init__(self):
        self.collection = db["assignments"]

    async def create(self, assignment: dict):
        await self.collection.insert_one(assignment)

    async def find_for_teacher(self, teacher_id: str):
        cursor = self.collection.find({"teacherId": teacher_id})
        return [doc async for doc in cursor]

    async def find_for_student(self, student_id: str):
        cursor = self.collection.find({"students": {"$in": [student_id]}})
        return [doc async for doc in cursor]

    async def find_one(self, assignment_id: str):
        return await self.collection.find_one({"_id": assignment_id})

    async def delete(self, assignment_id: str):
        result = await self.collection.delete_one({"_id": assignment_id})
        return result.deleted_count > 0

# Istanza globale
assignment_repo = AssignmentRepository()
