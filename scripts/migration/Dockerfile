# Generic control/build environment. Framework and model dependencies belong in
# the migration's derived Dockerfile, not in a model-specific Harness image.
ARG BASE_IMAGE=python:3.11-slim-bookworm
FROM ${BASE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential python3-venv libomp-dev libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/harness
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN python3 -m venv /opt/control && /opt/control/bin/pip install --no-cache-dir . \
    && python3 -m venv /opt/source && python3 -m venv /opt/target
# Capture runs from source in each framework interpreter, so both also need the
# shared runtime dependencies even though neither needs the Harness wheel.
RUN /opt/source/bin/pip install --no-cache-dir 'numpy>=1.24,<2' 'PyYAML>=6.0' \
    && /opt/target/bin/pip install --no-cache-dir 'numpy>=1.24,<2' 'PyYAML>=6.0'
COPY scripts ./scripts
ENV PATH="/opt/control/bin:${PATH}"
WORKDIR /work
CMD ["bash"]
