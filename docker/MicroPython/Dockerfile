
FROM debian:stretch-slim

ARG LIBDIR=/usr/lib/micropython

RUN apt-get update && \
    apt-get install -y build-essential libffi-dev git pkg-config python3 && \
    rm -rf /var/lib/apt/lists/* && \
    git clone https://github.com/micropython/micropython.git && \
    cd micropython && \
    git submodule update --init && \
    cd mpy-cross && \
    make && \
    cd .. && \
    cd ports/unix && \
    make submodules && \
    make && \
    make install && \
    apt-get purge --auto-remove -y build-essential libffi-dev git pkg-config python3 && \
    cd ../../.. && \
    mkdir $LIBDIR && \
    cp -a micropython/extmod/uasyncio/ $LIBDIR && \
    rm -rf micropython

WORKDIR /flash

RUN micropython -m upip install -p $LIBDIR logging traceback

COPY ./app/main.py ./

CMD ["micropython", "main.py"]
