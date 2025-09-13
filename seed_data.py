import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def seed_database():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.assessment_db
    collection = db.employees

    sample_employees = [
        {
            "employee_id": "E001",
            "name": "John Doe",
            "department": "Engineering",
            "salary": 75000,
            "joining_date": datetime(2023, 1, 15),
            "skills": ["Python", "MongoDB", "APIs"]
        },
        {
            "employee_id": "E002",
            "name": "Jane Smith",
            "department": "Engineering",
            "salary": 85000,
            "joining_date": datetime(2022, 8, 20),
            "skills": ["Python", "React", "Node.js", "MongoDB"]
        },
        {
            "employee_id": "E003",
            "name": "Mike Johnson",
            "department": "HR",
            "salary": 60000,
            "joining_date": datetime(2023, 3, 10),
            "skills": ["Communication", "Recruiting", "Excel"]
        },
        {
            "employee_id": "E004",
            "name": "Sarah Wilson",
            "department": "Engineering",
            "salary": 90000,
            "joining_date": datetime(2021, 11, 5),
            "skills": ["Python", "Machine Learning", "TensorFlow", "MongoDB"]
        },
        {
            "employee_id": "E005",
            "name": "David Brown",
            "department": "HR",
            "salary": 55000,
            "joining_date": datetime(2023, 6, 1),
            "skills": ["HR Management", "Employee Relations", "Excel"]
        },
        {
            "employee_id": "E006",
            "name": "Emily Davis",
            "department": "Marketing",
            "salary": 65000,
            "joining_date": datetime(2022, 12, 15),
            "skills": ["Digital Marketing", "Analytics", "Python", "SQL"]
        }
    ]

    try:
        await collection.delete_many({})
        await collection.insert_many(sample_employees)
        await collection.create_index([("employee_id", 1)], unique=True)
        print("✅ Seeded database with sample data")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
