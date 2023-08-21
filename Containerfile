ARG UPSTREAM_TAG=38

FROM public.ecr.aws/docker/library/fedora:${UPSTREAM_TAG}

ARG PYTHON_VERSION=3.11
ENV PYTHON_VERSION=${PYTHON_VERSION}

RUN dnf install -y xmlsec1-openssl strongswan pipx mc "python${PYTHON_VERSION}" \
    && dnf install -y --skip-broken "python${PYTHON_VERSION}-devel" \
    && dnf clean all

RUN useradd -m -U -s /bin/bash dev \
    && chown -R dev:dev /home/dev

RUN echo -e '#!/bin/bash\npoetry install\nexec $*' > /usr/local/bin/entrypoint.sh \
    && chmod +x /usr/local/bin/*

USER dev

RUN pipx ensurepath \
    && pipx install poetry

RUN mkdir ~/src

ENV SHELL=/bin/bash
ENV PATH="${PATH}:/home/dev/.local/bin"
WORKDIR /home/dev/src
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
EXPOSE 8080

CMD ["poetry", "shell"]
