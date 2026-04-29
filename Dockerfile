FROM python:3.14-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --user --no-cache-dir -r requirements.txt


FROM python:3.14-slim AS runtime

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY --from=builder /root/.local /home/app/.local

COPY --chown=app:app . .

ENV PATH=/home/app/.local/bin:$PATH

USER app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
