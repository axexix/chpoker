FROM python:3.11

RUN apt-get update \
    && apt-get install -y xmlsec1 strongswan-pki mc

RUN pip install poetry

ENV SHELL="/bin/bash"

WORKDIR /src

EXPOSE 8080

CMD ["poetry", "shell"]
