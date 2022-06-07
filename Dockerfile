FROM python:3-slim

USER root

RUN apt-get update \
    && apt-get install -y git curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root
ENV PATH "$PATH:/root"

# coca
RUN curl -LJO  https://github.com/modernizing/coca/releases/download/v2.3.0/coca_linux \
    && mv ./coca_linux ./coca \
    && chmod +x ./coca \
    && ./coca version

# linkediff
COPY . .
RUN pip install --no-cache-dir .

# ready
WORKDIR /usr/src/app
CMD ["bash"]
