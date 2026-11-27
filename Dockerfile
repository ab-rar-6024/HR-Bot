FROM python:3.11-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN useradd -m app && mkdir -p /srv/data /srv/models && chown -R app /srv
USER app
ENV VERIFYOPS_HOME=/srv VERIFYOPS_DATA=/srv/data
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","2"]
