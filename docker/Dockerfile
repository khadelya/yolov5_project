FROM ubuntu:20.04

LABEL description="Docker image with YOLO framework"
LABEL version="1.0"
LABEL maintainer="kh.adelya@mail.ru"

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update && \
    apt install --no-install-recommends -y \
    software-properties-common
RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt update && \
    apt install --no-install-recommends -y \
        git \
        ca-certificates \
        python3.10 \
        python-is-python3 \
        python3-pip \
        libgdal-dev \
        gdal-bin \
        libproj15 \
        libproj19 \
        libproj-dev

RUN mkdir -p /usr/src/app

RUN git clone https://github.com/ultralytics/yolov5 /usr/src/yolov5

RUN python -m pip install --upgrade pip
WORKDIR /usr/src/yolov5
RUN pip install \
    --no-cache \
    -r requirements.txt \
    albumentations \
    wandb \
    gsutil \
    notebook \
    Pillow>=9.1.0 \
    torch \
    torchvision \
    pyproj \
    --extra-index-url https://download.pytorch.org/whl/cu113

WORKDIR /usr/src/app
