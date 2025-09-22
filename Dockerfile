FROM python:3.10

WORKDIR /app

# Copiar y instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el contenido del proyecto
COPY . .

# Configurar Flask para usar 'app.main' como el archivo principal
ENV FLASK_APP=app.main

# Expone el puerto 5000
EXPOSE 5000

# Ejecutar la aplicación Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
