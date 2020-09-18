
# Docker

### Usage

* CPython
```
uPy$ docker build --tag upy:cpy docker/CPython
uPy$ docker run -it --network host --mount type=bind,src=`pwd`/app,dst=/flash --name cpy -d upy:cpy
uPy$ docker exec -it cpy bash
root@5184d7502e4e:/flash# python -c "import main; main.debug()"
DEBUG:main:forever tock
DEBUG:main:network address=192.168.1.11 gateway=192.168.1.1
DEBUG:main:forever tick
...
^C
root@thermal:/flash# exit
uPy$ docker exec -it cpy bash
```

* MicroPython
```
uPy$ docker build --tag upy:upy docker/MicroPython
uPy$ docker run -it --mount type=bind,src=`pwd`/app,dst=/flash --mount type=bind,src=`pwd`/app/lib,dst=/root/.micropython/lib --name upy upy:upy bash
root@a2ffbe782708:/flash# micropython
MicroPython v1.13-48-gb31cb21a3 on 2020-09-13; linux version
Use Ctrl-D to exit, Ctrl-E for paste mode
>>> import main
>>> main.debug()
DEBUG:main:forever tock
DEBUG:main:network DHCP
...
^C
>>> ^D
root@a2ffbe782708:/flash# exit
uPy$ docker exec -it upy bash
```
