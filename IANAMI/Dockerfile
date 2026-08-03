#imagen a instalar
FROM python:3.12-slim-trixie

#usamos el directorio de trabajo
WORKDIR /src/IANAMI

#ESTABLECER VARIABLES DEL ENTORNO 
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

#ACTUALIZAR PIP
RUN pip install --upgrade pip

#actualizar e instalar conectores de postgresql
RUN apt-get update && apt-get install -y gcc libpq-dev python3-dev musl-dev postgresql-client

#Copiar los requisitos del proyecto
COPY ./req.txt .

# Creamos unas carpetas para los staticos y los datos 
RUN mkdir /src/IANAMI/data

RUN mkdir /src/IANAMI/data/static

RUN mkdir /src/IANAMI/data/media

#instalar dependencias 
RUN pip install -r req.txt

#Copiar el proyecto entero
COPY . /src/IANAMI