ARG BASE_IMAGE=debian:bookworm-slim
FROM ${BASE_IMAGE}
# Package scripts must never start services during provisioning.
RUN printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d \
    && chmod 755 /usr/sbin/policy-rc.d \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       build-essential python3 at cron bsd-mailx exim4-daemon-light \
       cups-daemon cups-client sharutils libbsd-dev busybox ed locales acl \
    && localedef -i fr_FR -f UTF-8 fr_FR.UTF-8 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 cshell \
    && useradd --create-home --uid 10002 recipient \
    && printf 'cshell\n' > /etc/at.allow \
    && printf 'cshell\n' > /etc/cron.allow \
    && printf 'dc_eximconfig_configtype=local\ndc_other_hostnames=localhost\ndc_local_interfaces=127.0.0.1\ndc_readhost=\ndc_relay_domains=\ndc_minimaldns=false\ndc_relay_nets=\ndc_smarthost=\nCFILEMODE=644\ndc_use_split_config=false\ndc_hide_mailname=false\ndc_mailname_in_oh=true\ndc_localdelivery=mail_spool\n' > /etc/exim4/update-exim4.conf.conf \
    && printf 'localhost\n' > /etc/mailname \
    && update-exim4.conf \
    && printf 'CSH-078 disposable services v1\n' > /etc/cshell-service-fixture
WORKDIR /work
COPY Makefile Dockerfile ./
COPY include/ include/
COPY src/ src/
COPY tests/ tests/
COPY tools/ tools/
COPY docs/ docs/
RUN make -j2 cshell build/tests/host_utility_helper build/tests/host_printf_faults host-profile \
    && cc -std=c99 -Wall -Wextra -Werror -fPIC -shared -o build/tests/host_service_clock.so tests/host_service_clock.c -ldl \
    && mkdir -p /work/build/host-services/bin \
    && cp tools/host-services/at tools/host-services/batch tools/host-services/logger build/host-services/bin/ \
    && chmod 755 build/host-services/bin/at build/host-services/bin/batch build/host-services/bin/logger \
    && mkdir -p /work/build/tests \
    && chmod 755 /work /work/build /work/build/tests
CMD ["python3", "tests/host_services.py", "./cshell", "--services", "--path", "/work/build/host-services/bin:/work/build/host-profile/bin:/usr/bin:/bin", "--record", "/work/build/tests/host-services.json"]
