@echo off
echo Starting Employee Management API...

if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
echo Make sure MongoDB is running on localhost:27017
python seed_data.py
python main.py
pause
