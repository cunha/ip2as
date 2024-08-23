FROM python:3.7-bullseye

WORKDIR /app
COPY . /app
RUN python3 setup.py install

ENTRYPOINT ["/bin/bash"]
