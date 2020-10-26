from . import version

YAML = """

default:
  target:       cpython
  app:          first

directory:
  lib:          "lib"
  app:          "app"
  dev:          "dev"
  build:        "build"
  
libs:

  - name:       slogan
    directory:  "message"

apps:

  - name:       first
    directory:  "hello"
    libs:
      - slogan

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

targets:

  - name:       cpython
    type:       docker
    meta:
      dockerfile: |
        FROM python:3.7.9-slim-stretch
        ENV PYTHONPATH={pythonpath}
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
  name:         "{name}"
  version:      "{version}"

""".format(
    name=version.NAME,
    version=version.VERSION,
    pythonpath='/flash/lib'
)
