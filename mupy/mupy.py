from . import version

YAML = """

default:
  target:       cpython
  app:          example

directory:
  lib:          "lib"
  app:          "app"
  dev:          "dev"
  build:        "build"
  
libs:

  - name:       example
    directory:  "example"

apps:

  - name:       example
    directory:  "example"
    libs:
      - example

files:

  - path:       "app/example/main.py"
    content: |
      from example import message
      print(f'Hello, {{message}}!')

  - path:       "lib/example/__init__.py"
    content: |
      message = "world"

  - path:       "dev/lib/example/__init__.py"
    content: |
      message = "MuPy"

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
