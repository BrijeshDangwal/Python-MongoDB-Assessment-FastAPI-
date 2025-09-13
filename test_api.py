import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

async def test_api():
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Employee Management API\n")

        # Health Check
        async with session.get(f"{BASE_URL}/health") as response:
            print("1. Health Check:", response.status, await response.json())
        # Create Employee
        new_employee = {
            "employee_id": "E999",
            "name": "Test User",
            "department": "Testing",
            "salary": 70000,
            "joining_date": "2023-09-01",
            "skills": ["Testing", "QA", "Python"]
        }
        async with session.post(f"{BASE_URL}/employees", json=new_employee) as response:
            print("2. Create Employee:", response.status, await response.json())
        # Get Employee by ID
        async with session.get(f"{BASE_URL}/employees/E001") as response:
            print("3. Get Employee E001:", response.status, await response.json())
        # Update Employee
        update_data = {"salary": 80000}
        async with session.put(f"{BASE_URL}/employees/E001", json=update_data) as response:
            print("4. Update Employee E001:", response.status, await response.json())
        # List Employees by Department
        async with session.get(f"{BASE_URL}/employees?department=Engineering") as response:
            print("5. List Engineering Employees:", response.status, len(await response.json()))
        # Average Salary by Department
        async with session.get(f"{BASE_URL}/employees/avg-salary") as response:
            print("6. Avg Salary by Dept:", response.status, await response.json())
        # Search by Skill
        async with session.get(f"{BASE_URL}/employees/search?skill=Python") as response:
            print("7. Search by Skill 'Python':", response.status, len(await response.json()))
        # Delete Employee
        async with session.delete(f"{BASE_URL}/employees/E999") as response:
            print("8. Delete E999:", response.status, await response.json())

if __name__ == "__main__":
    asyncio.run(test_api())
