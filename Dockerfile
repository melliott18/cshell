ARG BASE_IMAGE=debian:bookworm-slim
FROM ${BASE_IMAGE}

# Debian slim excludes message catalogs by default; retain French libc
# diagnostics so CSH-042 exercises LC_MESSAGES as well as locale names.
RUN echo 'path-include=/usr/share/locale/fr/*' > /etc/dpkg/dpkg.cfg.d/zz-cshell-locale \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3 procps locales ed busybox acl \
    && localedef -i en_US -f UTF-8 en_US.UTF-8 \
    && localedef -i fr_FR -f UTF-8 fr_FR.UTF-8 \
    && localedef -i de_DE -f UTF-8 de_DE.UTF-8 \
    && localedef -i zh_CN -f GB18030 zh_CN.GB18030 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 cshell \
    && mkdir /work \
    && chown cshell:cshell /work

WORKDIR /work
COPY --chown=cshell:cshell Makefile Dockerfile ./
COPY --chown=cshell:cshell include/ include/
COPY --chown=cshell:cshell src/ src/
COPY --chown=cshell:cshell tests/ tests/
COPY --chown=cshell:cshell tools/ tools/
# .dockerignore selects only the documentation used by ownership checks.
COPY --chown=cshell:cshell docs/ docs/

USER cshell
# Build the selected source target with Linux tools, never a host executable.
ARG TEST_TARGET=cshell
RUN if [ -n "$TEST_TARGET" ]; then make "$TEST_TARGET"; fi

CMD ["make", "test"]
