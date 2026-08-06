# Run the Project

## Prerequisites
- Python 3.10+ installed
- Virtual environment recommended

## 1. Install dependencies
```bash
pip install -r requirements.txt
```

## 2. Apply database migrations
```bash
python manage.py migrate
```

## 3. Create a superuser (optional)
```bash
python manage.py createsuperuser
```

## 4. Start the development server
```bash
python manage.py runserver 0.0.0.0:8000
```

## 5. Open the app
Visit:
```text
http://127.0.0.1:8000/
```

## Notes
- If you want to run tests:
```bash
python manage.py test
```
- If you hit host-related issues locally, the project has been configured to allow `127.0.0.1`, `localhost`, and `0.0.0.0`.
