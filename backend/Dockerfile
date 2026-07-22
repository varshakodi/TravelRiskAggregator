# Recipe for the backend image: a frozen, portable box with the app and
# everything it needs. Built and verified by CI on every push.
FROM python:3.11-slim

WORKDIR /app

# Dependencies first, code second: Docker caches layers top-down, so as long
# as requirements.txt is unchanged, rebuilds skip the slow pip install.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Apply migrations, then serve. $PORT is provided by platforms like Render;
# defaults to 8000 for local/compose use.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
