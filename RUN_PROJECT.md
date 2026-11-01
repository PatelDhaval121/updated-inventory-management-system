# Run the Project

## Prerequisites
- Python 3.10+ installed
- Virtual environment recommended

## 1. Install dependencies
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Apply database migrations
```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

## 3. Create a superuser (optional)
```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

## 4. Start the development server
```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## 5. Open the app
Visit:
```text
http://127.0.0.1:8000/
```

## Notes
- If you want to run tests:
```powershell
.\.venv\Scripts\python.exe manage.py test
```
- On Windows, `python` may point to the Microsoft Store alias instead of the project interpreter. Using the repo virtual environment directly avoids that issue.
- If you hit host-related issues locally, the project has been configured to allow `127.0.0.1`, `localhost`, and `0.0.0.0`.




.
cd "C:\Users\OMEN\Desktop\updated inventory management system\updated inventory management system\sales-and-inventory-management"
.\.venv\Scripts\activate
python manage.py check
python manage.py runserver