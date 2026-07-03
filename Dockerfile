FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей с правильными именами пакетов для Debian Trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    wget \
    gnupg \
    libpango-1.0-0 \
    libjpeg62-turbo-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка Playwright и браузеров
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps

# Копируем только requirements.txt для кэширования слоёв
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём папку для данных
RUN mkdir -p /app/data

# Открываем порт для Railway
EXPOSE 8080

# Запуск приложения с портом 8080 для Railway
CMD ["python", "run.py", "--mode", "both", "--port", "8080"]