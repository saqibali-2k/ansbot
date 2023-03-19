From python:3.9-slim-bullseye

RUN pip install numpy python-dotenv discord peewee

WORKDIR /home/

ADD discbot /home/discbot

WORKDIR /home/discbot

CMD ["/usr/local/bin/python3","main.py"]