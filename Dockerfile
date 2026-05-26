FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей (если нужны для psycopg2 и других пакетов)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt для кэширования слоёв
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём папку для данных
RUN mkdir -p /app/data

# Открываем порт
EXPOSE 5000

# Запуск приложения
CMD ["python", "run.py"]