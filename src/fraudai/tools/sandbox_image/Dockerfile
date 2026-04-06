FROM python:3.11-slim

# Install analysis dependencies used by Harvey, Jessica, Mike, and Rachel.
# Nothing is installed at runtime -- the image is immutable.
RUN pip install --no-cache-dir \
    pandas==2.2.* \
    numpy>=2.1,<3 \
    scikit-learn==1.6.* \
    scipy>=1.13,<2 \
    networkx==3.4.* \
    matplotlib>=3.9,<4 \
    && rm -rf /root/.cache

# Security: non-root user with minimal shell
RUN useradd -m -s /bin/bash sandbox
USER sandbox
WORKDIR /workspace

# Pre-create output directory so the sandbox user can write to it
RUN mkdir -p /workspace/output

# No ENTRYPOINT -- commands are passed at runtime by SandboxEngine
