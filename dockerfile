# Usa una imagen base ligera de Python
FROM python:3.10-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de tu proyecto al contenedor
COPY . /app

# Actualiza herramientas esenciales de Python
RUN pip install --upgrade pip setuptools==65.5.1 wheel

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala dependencias sin instalar dependencias adicionales automáticas
RUN pip install --no-deps -r requirements.txt

# Expone el puerto 5000 (el que usa Flask por defecto)
EXPOSE 5000

# Define el comando que ejecutará la aplicación Flask
CMD ["python", "app.py"]
