FROM ubuntu:18.04

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -y update && apt-get dist-upgrade -yq && apt-get install -yq --no-install-recommends \
    python python-pip python-dev build-essential \
    libxml2-dev libxslt1-dev zlib1g-dev git cmake

# RUN apt-get -y update && apt-get install -yq --no-install-recommends \
#     autoconf automake libtool \
#     autoconf-archive \
#     pkg-config \
#     ffmpeg \
#     libavutil-dev \
#     libavcodec-dev \
#     libavfilter-dev \
#     libavformat-dev \
#     libavdevice-dev \
#     libpng12-dev \
#     libjpeg8-dev \
#     libtiff5-dev \
#     zlib1g-dev \
#     libleptonica-dev \
#     libfreetype6-dev \
#     tesseract-ocr

# RUN mkdir /opencv && cd /opencv && \
#     git clone https://github.com/Itseez/opencv.git . && \
#     git checkout 3.2.0 && \
#     mkdir build && cd build && \
#     cmake -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=/usr/local .. && \
#     make -j4 && make install





RUN  pip install --upgrade pip 
RUN  pip install --upgrade virtualenv
RUN  pip install cython setuptools

RUN \
    pip install \
        BeautifulSoup==3.2.0 \
        Django==1.11.0 \
        Markdown==2.6.8 \
        Pillow==4.0.0 \
        django-extensions==1.7.6 \
        django-haystack==2.8.1 \
        pysolr==3.6.0 \
        wsgiref==0.1.2 \
        feedparser==4.1 \
        django-compressor==2.1.1 \
        requests==2.13 \
        requests-oauthlib==0.6.1 \
        lxml==3.7.3 \
        cssselect==0.9.1 \
        PyBrowserID \
        google-api-python-client==1.5.0 \
        webob==1.2.2 \
        jsonfield==1.0.3 \
        python-memcached==1.58 \
        django-imagekit==4.0 \
        google-api-python-client==1.5.0 \
        numpy

RUN pip install \
    beautifulsoup4==4.3.2 \
    ply==3.4 \
    slimit \
    fuzzywuzzy[speedup] \
    python-Levenshtein 

RUN pip install django-libsass==0.7
RUN pip install -e git+git://github.com/rhymeswithcycle/alpheus.git#egg=alpheus


RUN apt-get -y update && apt-get install -yq --no-install-recommends libmysqlclient-dev mysql-server

RUN pip install MySQL-python

WORKDIR /openParl
ENTRYPOINT ./runserver.sh
# ENTRYPOINT bash


