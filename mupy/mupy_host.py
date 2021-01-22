from . import version
from .host import Host

PYTHONPATH = '/flash/lib'
    
YAML = f"""

#shell:
#  bin:          '/bin/dash'
#  env:          {{ 'FOO': 'bar' }}

directory:
  stock:        "{Host.STOCK}"
  build:        "{Host.BUILD}"

targets:

  - name:       ghost
    mode:       local
    type:       cpython
    tags:       +host

  - name:       python
    mode:       docker
    type:       cpython
    tags:       +host

  - name:       unix
    mode:       docker
    precompile: false
    tags:       +host

  - name:       stm32
    mode:       cross
    meta:
      baud:     115200
      port:     "/dev/ttyACM0"

version:
  name:         "{version.NAME}"
  version:      "{version.VERSION}"

mode:

  cpython:
    type:       docker
    meta:
      dockerfile: |
        FROM python:3.7.9-slim-stretch
        ENV PYTHONPATH={PYTHONPATH}
        CMD ["python3"]

  micropython:
    type:       docker
    meta:
      message:  "~3 minutes"
      dockerfile: |
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
            cp mpy-cross /usr/local/bin && \
            cd .. && \
            cd ports/unix && \
            make submodules && \
            make && \
            make install && \
            apt-get purge --auto-remove -y build-essential libffi-dev git pkg-config && \
            cd ../../.. && \
            mkdir $LIBDIR && \
            cp -a micropython/extmod/uasyncio/ $LIBDIR && \
            rm -rf micropython

        WORKDIR /flash

        #RUN micropython -m upip install -p $LIBDIR logging traceback

        #COPY ./app/main.py ./

        CMD ["micropython", "main.py"]
"""
