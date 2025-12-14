FROM python:3.11    

RUN apt-get update && wget https://mega.nz/linux/repo/Debian_12/amd64/megacmd-Debian_12_amd64.deb && apt install -y "$PWD/megacmd-Debian_12_amd64.deb"
RUN pip install confluent-kafka pandas

COPY . /app
WORKDIR /app

RUN mkdir data
RUN mega-get "https://mega.nz/folder/EYcF3I7A#shlgKrU69INQxKbrZdDBxQ" ./data

ENV DATASET_DIR=data/events_logs_dataset

CMD ["python", "-u", "producer.py"]