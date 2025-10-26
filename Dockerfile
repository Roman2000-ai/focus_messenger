# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.12 AS  builder



EXPOSE 8000

WORKDIR /app
# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt --no-cache-dir




FROM python:3.12-slim

WORKDIR /app
COPY . /app

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN chmod +x ./run.sh
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["./run.sh"]
