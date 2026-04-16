FROM python:3.11-slim

WORKDIR /app

# Install bot engine as a local package
COPY ../bot /app/bot
RUN pip install --no-cache-dir -e /app/bot

# Install API dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
