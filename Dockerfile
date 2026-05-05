FROM qmcgaw/gluetun:v3.41.1

RUN apk add --no-cache python3 py3-pip && \
    python3 -m venv /app/venv

COPY requirements.txt /app/requirements.txt
RUN /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

COPY vpn.py /app/vpn.py
COPY main.py /app/main.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
