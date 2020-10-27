from . import version
from .content import Host

PYTHONPATH = '/flash/lib'
    
YAML = f"""
default:
  target:       cpython
  app:          first

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

  - name:       cpython
    type:       docker
    meta:
      dockerfile: |
        FROM python:3.7.9-slim-stretch
        ENV PYTHONPATH={PYTHONPATH}
        CMD ["python3"]

  - name:       unix
    type:       docker
    meta:
      dockerfile: |
        FROM debian:stretch-slim
        CMD ["echo", "Hello, Unix!"]

  - name:       stm32
    type:       cross
    meta:

version:
  name:         "{version.NAME}"
  version:      "{version.VERSION}"

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
