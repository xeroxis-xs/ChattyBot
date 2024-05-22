FROM python:3.12-alpine
EXPOSE 8000
WORKDIR /app

COPY requirements.txt /app

RUN pip install -r requirements.txt --no-cache-dir

COPY . /app

CMD ["python3", "-m", "streamlit", "run", "/app/Home.py", "--server.address", "0.0.0.0", "--server.port", "8000"]
