# muPy
_Multi-target application builder for MicroPython_

Express the design of your project with standalone configuration files.

* `component.mupy`

Separate components into user-defined _grades_, typically ranging from
_A_ to _C_.

Build and run your project with a single command.
* `mupy run component^entry@target`

Mix-and-match components from other projects with zero changes to source
code. Simply edit the `*.mupy` configuration file, then build and run.

Get started with no hardware. Start using hardware target when you're ready.

Target | Mode | Micro/Python | Tested | Install
-- | -- | -- | -- | --
`@ghost` | Local | CPython| Python 3.8.5 | pip install mupy
`@python` | Docker | CPython | Python 3.7.9 | pip install 'mupy[docker]'
`@unix` | Docker | `ports/unix` | Micropython uPy v1.12 | pip install 'mupy[docker]'
`@stm32` | Hardware | `ports/stm32` | uPy v1.12 on STM32F769 | pip install 'mupy[docker]'

### Requirements

* Linux
* Python 3.6+
  * Tested on Python 3.8.5
* Docker (optional), for
  * Running the Micropython `@unix` target
  * Cross-compiling to any hardware target

### Developers

Use a virtual environment:
* `source venv/bin/activate`

Package and install the muPy command as follows:
* `python setup.py bdist_wheel`
* `pip install dist/mupy-0.0.4-py3-none-any.whl`
  * `--force-reinstall` override equal versions
  * `--verbose` observe the details

### nuPy

Kick-start your Micropython project with the _nuPy_ application
framework that builds and runs on _muPy_.

### Example

```
stock/
├── A
│   ├── demo.py
│   ├── hello.mupy
│   └── hello.py
└── B
    ├── demo.py
    ├── hello.mupy
    └── hello.py
```

* `stock/A/hello.mupy` and `stock/B/hello.mupy`
```
exports:        [ demo ]

parts:

  - name:       demo
    path:       "demo.py"
    uses:       [ hello ]

  - name:       hello
    path:       "hello.py"
```

* `stock/A/demo.mupy` and `stock/B/demo.mupy`
```
from hello import MESSAGE

def main():
    print(MESSAGE)

main()
```

* `stock/A/hello.mupy`
```
MESSAGE = 'Hello, world!'
```

* `stock/B/hello.mupy`
```
MESSAGE = 'Hello, muPy!'
```

* `mupy run hello^demo@ghost --grade A`
```
Hello, world!
```

* `mupy run hello^demo@ghost --grade B`
```
Hello, muPy!
```

