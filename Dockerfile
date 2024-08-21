FROM ubuntu:latest

RUN apt update
RUN apt install python3 python3-pip -y
RUN apt install libcairo2-dev pkg-config python3-dev -y

WORKDIR /app

COPY requirements.txt requirements.txt
COPY start.sh start.sh
RUN pip3 install -r requirements.txt
RUN chmod +x ./start.sh

COPY . .

CMD chmod +x ./start.sh ; ./start.sh
