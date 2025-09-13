
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
import os
from contextlib import asynccontextmanager

# Pydantic models for request/response validation
class EmployeeBase(BaseModel):
    name: str
    department: str
    salary: float = Field(gt=0, description="Salary must be positive")
    joining_date: date
    skills: List[str]

class EmployeeCreate(EmployeeBase):
    employee_id: str = Field(..., description="Unique employee identifier")

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = Field(None, gt=0, description="Salary must be positive")
    joining_date: Optional[date] = None
    skills: Optional[List[str]] = None

class EmployeeResponse(EmployeeBase):
    employee_id: str

class AverageSalaryResponse(BaseModel):
    department: str
    avg_salary: float

# Global variables for database connection
mongodb_client: AsyncIOMotorClient = None
database = None
collection = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mongodb_client, database, collection

    # MongoDB connection
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    database = mongodb_client.assessment_db
    collection = database.employees

    # Create index on employee_id for better performance
    await collection.create_index([("employee_id", ASCENDING)], unique=True)

    print("Connected to MongoDB and created indexes")
    yield

    # Shutdown
    if mongodb_client:
        mongodb_client.close()
        print("Disconnected from MongoDB")

# Initialize FastAPI app
app = FastAPI(
    title="Employee Management API",
    description="A FastAPI application for managing employee records with MongoDB",
    version="1.0.0",
    lifespan=lifespan
)

# Helper function to convert MongoDB document to dict
def employee_helper(employee) -> dict:
    if employee:
        employee["_id"] = str(employee["_id"])
        # Convert date to string for JSON serialization
        if "joining_date" in employee:
            employee["joining_date"] = employee["joining_date"].isoformat()
        return employee
    return None

# CRUD Operations

@app.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(employee: EmployeeCreate):
    """Create a new employee record"""
    try:
        # Check if employee_id already exists
        existing_employee = await collection.find_one({"employee_id": employee.employee_id})
        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with ID {employee.employee_id} already exists"
            )

        # Convert date to datetime for MongoDB storage
        employee_dict = employee.dict()
        employee_dict["joining_date"] = datetime.combine(employee.joining_date, datetime.min.time())

        # Insert the employee
        result = await collection.insert_one(employee_dict)

        if result.inserted_id:
            new_employee = await collection.find_one({"_id": result.inserted_id})
            return employee_helper(new_employee)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create employee"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: str):
    """Get employee by ID"""
    try:
        employee = await collection.find_one({"employee_id": employee_id})
        if employee:
            return employee_helper(employee)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(employee_id: str, employee_update: EmployeeUpdate):
    """Update employee details (partial updates allowed)"""
    try:
        # Check if employee exists
        existing_employee = await collection.find_one({"employee_id": employee_id})
        if not existing_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )

        # Prepare update data (only include non-None fields)
        update_data = {}
        for field, value in employee_update.dict(exclude_unset=True).items():
            if value is not None:
                if field == "joining_date":
                    update_data[field] = datetime.combine(value, datetime.min.time())
                else:
                    update_data[field] = value

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )

        # Update the employee
        result = await collection.update_one(
            {"employee_id": employee_id},
            {"$set": update_data}
        )

        if result.modified_count:
            updated_employee = await collection.find_one({"employee_id": employee_id})
            return employee_helper(updated_employee)

        # If no documents were modified, return the existing employee
        return employee_helper(existing_employee)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str):
    """Delete employee record"""
    try:
        result = await collection.delete_one({"employee_id": employee_id})

        if result.deleted_count:
            return {"message": f"Employee with ID {employee_id} deleted successfully"}

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

# Querying & Aggregation

@app.get("/employees", response_model=List[EmployeeResponse])
async def list_employees_by_department(
    department: Optional[str] = Query(None, description="Filter by department"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size")
):
    """List employees by department with pagination, sorted by joining_date (newest first)"""
    try:
        # Build query filter
        query_filter = {}
        if department:
            query_filter["department"] = department

        # Calculate skip value for pagination
        skip = (page - 1) * size

        # Query with sorting and pagination
        cursor = collection.find(query_filter).sort("joining_date", -1).skip(skip).limit(size)
        employees = []

        async for employee in cursor:
            employees.append(employee_helper(employee))

        return employees

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.get("/employees/avg-salary", response_model=List[AverageSalaryResponse])
async def get_average_salary_by_department():
    """Get average salary by department using MongoDB aggregation"""
    try:
        pipeline = [
            {
                "$group": {
                    "_id": "$department",
                    "avg_salary": {"$avg": "$salary"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "department": "$_id",
                    "avg_salary": {"$round": ["$avg_salary", 2]}
                }
            },
            {
                "$sort": {"department": 1}
            }
        ]

        cursor = collection.aggregate(pipeline)
        results = []

        async for result in cursor:
            results.append(AverageSalaryResponse(**result))

        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.get("/employees/search", response_model=List[EmployeeResponse])
async def search_employees_by_skill(
    skill: str = Query(..., description="Skill to search for"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size")
):
    """Search employees by skill with pagination"""
    try:
        # Calculate skip value for pagination
        skip = (page - 1) * size

        # Query employees with the specified skill
        cursor = collection.find(
            {"skills": {"$in": [skill]}}
        ).skip(skip).limit(size)

        employees = []
        async for employee in cursor:
            employees.append(employee_helper(employee))

        return employees

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        await database.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Employee Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
