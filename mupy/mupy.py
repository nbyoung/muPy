from . import version
from .content import Host

PYTHONPATH = '/flash/lib'
    
YAML = f"""
default:
  app:          first
  target:       python

directory:
  lib:          "{Host.LIB}"
  app:          "{Host.APP}"
  dev:          "{Host.DEV}"
  build:        "{Host.BUILD}"
  
libs:

  - name:       slogan
    directory:  "message"

apps:

  - name:       first
    directory:  "hello"
    libs:
      - slogan

targets:

  - name:       python
    mode:       docker
    type:       cpython

  - name:       unix
    mode:       docker
    precompile: false

  - name:       stm32
    mode:       cross

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

files:

  - path:       "app/hello/main.py"
    content: |
      from slogan import MESSAGE
      print(MESSAGE)

  - path:       "lib/message/__init__.py"
    content: |
      MESSAGE = "Hello, world!"

  - path:       "dev/lib/message/__init__.py"
    content: |
      MESSAGE = "MuPy rocks!"
"""
