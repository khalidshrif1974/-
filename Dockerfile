FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY wsgi.py .
RUN useradd -m appuser && mkdir -p instance && chown appuser instance
USER appuser
CMD ["gunicorn", "-b", "0.0.0.0:8000", "wsgi:app"]
