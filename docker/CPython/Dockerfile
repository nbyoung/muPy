
FROM python:3.7.9-slim-stretch

ARG HOME=/flash

WORKDIR $HOME

COPY ./app/main.py ./

ENV PYTHONPATH=${HOME}/lib

CMD ["python3", "./main.py"]
