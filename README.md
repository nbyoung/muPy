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

Get started with no hardware using the three built-in _soft_ targets.
Transition to a hardware target when you're ready.

Target | Mode | Micro/Python | Tested
-- | -- | -- | --
`@ghost` | Local | CPython| Python 3.8.5
`@python` | Docker | CPython | Python 3.7.9
`@unix` | Docker | `ports/unix` | Micropython v1.12
`@stm32` | Hardware | `ports/stm32` | v1.12 on STM32F769

Kick-start your Micropython project with the _nuPy_ application
framework that builds and runs on out-of-the-box on _muPy_.
