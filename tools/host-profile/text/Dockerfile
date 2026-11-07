# Build on the repository's test image; stock provider evidence stays separate.
ARG TEXT_BASE=cshell-text:ci
FROM ${TEXT_BASE}
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates xz-utils lzip \
    && rm -rf /var/lib/apt/lists/*
USER cshell
RUN make host-text-providers
