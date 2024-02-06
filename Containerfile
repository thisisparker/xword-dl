#
# Build: podman build -t xword-dl .
#        podman tag xword-dl:latest xword-dl:$(git describe --tags)
#
# Run: podman run --rm --tz local -v $HOME/my-xwords:/xw:Z xword-dl [...]
#
FROM docker.io/library/alpine:latest
WORKDIR /xw
COPY . /xword-dl
RUN apk update && \
    apk add python3 py3-setuptools py3-pip gcc python3-dev musl-dev libxml2 libxslt libxml2-dev libxslt-dev && \
    python3 -m pip install /xword-dl && \
    apk del gcc python3-dev musl-dev libxslt-dev libxml2-dev
ENTRYPOINT ["/usr/bin/xword-dl"]
