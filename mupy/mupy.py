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
      dockerfile: |
        FROM debian:stretch-slim
        CMD ["echo", "Hello, Unix!"]

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
