FROM postgis/postgis:16-3.4

RUN apt-get update && apt-get install -y locales && \
    localedef -i ru_RU -c -f UTF-8 -A /usr/share/locale/locale.alias ru_RU.UTF-8


ENV LANG=ru_RU.UTF-8
ENV LC_ALL=ru_RU.UTF-8
