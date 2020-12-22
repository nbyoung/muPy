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

### Example



### Requirements

* Linux
* Python 3.6+
  * Tested on Python 3.8.5
* Docker (optional), for
  * Running the Micropython `@unix` target
  * Cross-compiling to any hardware target

### nuPy

Kick-start your Micropython project with the _nuPy_ application
framework that builds and runs on _muPy_.
