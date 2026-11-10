# Reproducible CPU validation fixture, not a general model environment.
FROM jittor-harness:standalone-check
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG TORCH_FIND_LINKS=https://download.pytorch.org/whl/cpu/torch/
RUN /opt/source/bin/pip install --no-cache-dir numpy==1.26.4 \
    && /opt/source/bin/pip install --no-cache-dir torch==2.4.1+cpu --find-links "${TORCH_FIND_LINKS}"
RUN /opt/target/bin/pip install --no-cache-dir numpy==1.26.4 jittor==1.3.11.0
COPY scripts/migration/Smoke.Dockerfile /opt/harness/scripts/migration/Smoke.Dockerfile
COPY scripts/migration/*.py /opt/harness/scripts/migration/
ENV DISABLE_MULTIPROCESSING=1 OMP_NUM_THREADS=2
