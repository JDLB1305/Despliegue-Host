# Usa una imagen base ligera de Python
FROM python:3.10-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de tu proyecto al contenedor
COPY . /app

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    && apt-get clean

# Instala las dependencias de Python
RUN python -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Expone el puerto 5000 (el que usa Flask por defecto)
EXPOSE 5000

# Define el comando que ejecutará la aplicación Flask
CMD ["venv/bin/python", "app.py"]
