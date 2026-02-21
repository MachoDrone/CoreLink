FROM nvidia/cuda:12.2.0-base-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies (native Ubuntu packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    libpam0g \
    libpam0g-dev \
    openssl \
    curl \
    ethtool \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22.x (required for @nosana/kit probe)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (3rd-party allowed inside container)
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Download frontend vendor libraries (bundled, no CDN at runtime)
RUN mkdir -p /app/static/vendor/css /app/static/vendor/js && \
    curl -sL -o /app/static/vendor/css/bootstrap.min.css \
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" && \
    curl -sL -o /app/static/vendor/js/bootstrap.bundle.min.js \
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" && \
    curl -sL -o /app/static/vendor/js/socket.io.min.js \
        "https://cdn.socket.io/4.7.5/socket.io.min.js"

# Install Nosana probe npm dependencies (cached unless package.json changes)
COPY app/nosana/package.json /app/nosana/package.json
RUN cd /app/nosana && npm install --ignore-scripts --no-optional 2>/dev/null; exit 0

# Copy application code
COPY app/ /app/

# Copy and prepare entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Persistent data directory (mounted as volume)
RUN mkdir -p /data/ssl

EXPOSE 443/tcp
EXPOSE 47100/udp
EXPOSE 47101/udp

ENTRYPOINT ["/entrypoint.sh"]
