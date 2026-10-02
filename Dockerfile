ARG BASE_IMAGE=debian:bookworm-slim
FROM ${BASE_IMAGE} AS development

# Debian slim excludes message catalogs by default; retain French libc
# diagnostics so CSH-042 exercises LC_MESSAGES as well as locale names.
RUN echo 'path-include=/usr/share/locale/fr/*' > /etc/dpkg/dpkg.cfg.d/zz-cshell-locale \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3 procps locales ed busybox acl tini \
    && localedef -i en_US -f UTF-8 en_US.UTF-8 \
    && localedef -i fr_FR -f UTF-8 fr_FR.UTF-8 \
    && localedef -i de_DE -f UTF-8 de_DE.UTF-8 \
    && localedef -i zh_CN -f GB18030 zh_CN.GB18030 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 cshell \
    && useradd --create-home --uid 10001 --gid 10001 cshell \
    && mkdir /work \
    && chown cshell:cshell /work

WORKDIR /work
COPY tests/locales/csh_067 /tmp/csh_067
RUN localedef -i /tmp/csh_067 -f UTF-8 csh_067.UTF-8 \
    && localedef -i ja_JP -f EUC-JP ja_JP.EUC-JP
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

# Pipeline executes this target's CMD without a host-side test wrapper.
FROM development AS test
RUN mkdir -p /work/test-results
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["python3", "tests/container_report.py", "--output", "/work/test-results"]

# Compile independently of optional TEST_TARGET and the test toolchain/layers.
FROM ${BASE_IMAGE} AS build
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY Makefile ./
COPY include/ include/
COPY src/ src/
RUN make -j2

FROM ${BASE_IMAGE} AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 cshell \
    && useradd --create-home --uid 10001 --gid 10001 --shell /usr/local/bin/cshell cshell \
    && mkdir /work \
    && chown 10001:10001 /work
COPY --from=build /build/cshell /usr/local/bin/cshell
ENV HOME=/home/cshell LANG=C.UTF-8
USER 10001:10001
WORKDIR /work
# Forward termination to the command group and reap orphaned descendants.
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/cshell"]
CMD []
