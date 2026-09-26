FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3 procps \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 cshell \
    && mkdir /work \
    && chown cshell:cshell /work

WORKDIR /work
COPY --chown=cshell:cshell Makefile ./
COPY --chown=cshell:cshell include/ include/
COPY --chown=cshell:cshell src/ src/
COPY --chown=cshell:cshell tests/ tests/

USER cshell
# Build the selected source target with Linux tools, never a host executable.
ARG TEST_TARGET=cshell
RUN if [ -n "$TEST_TARGET" ]; then make "$TEST_TARGET"; fi

CMD ["make", "test"]
