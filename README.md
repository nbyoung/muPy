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

Get started with no hardware using the three built-in targets.
Transition to a hardware target when you're ready.

| `ghost` | Host | CPython | 
| `python` | Docker | CPython | 
| `unix` | Docker | Micropython's ports/unix | 
| `stm32` | Hardware | STM32F769 |

Kick-start your Micropython project with the _nuPy_ application
framework that builds and runs on out-of-the-box on _muPy_.
