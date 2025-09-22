import os
import json
import pika
import time
import traceback
import requests
from email.message import EmailMessage
import smtplib
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()
SUNAT_TOKEN = os.getenv('SUNAT_TOKEN')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
SMTP_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('MAIL_PORT', 587))
SMTP_USER = os.getenv('MAIL_USERNAME')
SMTP_PASS = os.getenv('MAIL_PASSWORD')
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'

# Lista para almacenar las facturas temporalmente
facturas = []

# Consultar datos del RUC en la SUNAT
def obtener_datos_sunat(ruc: str):
    url = "https://apiperu.dev/api/ruc"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUNAT_TOKEN}"
    }
    payload = json.dumps({"ruc": ruc})
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[SUNAT] Error {response.status_code}: {response.text}")
            return {"error": "Error al consultar SUNAT"}
    except requests.RequestException as e:
        print(f"[SUNAT] Excepción: {e}")
        return {"error": "Excepción al conectar con SUNAT"}

# Enviar correo con la información de la factura
def enviar_correo(destino, asunto, cuerpo):
    try:
        if not SMTP_USER or not SMTP_PASS:
            raise ValueError("Credenciales SMTP no configuradas correctamente.")
        
        msg = EmailMessage()
        msg['Subject'] = asunto
        msg['From'] = SMTP_USER
        msg['To'] = destino
        msg.set_content(cuerpo)

        print(f"[EMAIL] Conectando a servidor SMTP: {SMTP_SERVER}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            if MAIL_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        print(f"[EMAIL] Correo enviado exitosamente a {destino}")
    except Exception as e:
        print(f"[EMAIL] Error al enviar el correo a {destino}: {e}")
        traceback.print_exc()

# Procesar los mensajes recibidos de la cola
def callback(ch, method, properties, body):
    try:
        print(f"[FACTURA] Mensaje recibido: {body}")
        data = json.loads(body)

        if not isinstance(data, dict):
            raise ValueError("El cuerpo del mensaje no es un JSON válido")

        tipo = data.get('tipo_comprobante')
        if tipo != 'factura':
            print(f"[FACTURA] Ignorado tipo comprobante: {tipo}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        ruc = data.get('ruc')
        if not ruc:
            print("[FACTURA] No se recibió RUC, ignorando mensaje.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Consultar datos desde SUNAT sin normalizar
        datos_sunat = obtener_datos_sunat(ruc)
        if 'data' in datos_sunat:
            data.update(datos_sunat['data'])
        else:
            data.update({"sunat_error": datos_sunat.get("error", "Desconocido")})

        # Guardar la factura
        facturas.append(data)
        print(f"[FACTURA] Factura almacenada: {data}")

        # Enviar correo si se especifica un destino
        email_destino = data.get('email_destino')
        if email_destino:
            cuerpo_correo = "Detalle de la factura:\n\n"
            for key, value in data.items():
                cuerpo_correo += f"{key}: {value}\n"
            enviar_correo(
                destino=email_destino,
                asunto=f"Factura {data.get('ruc', 'N/A')}",
                cuerpo=cuerpo_correo
            )
        else:
            print("[FACTURA] No se encontró 'email_destino' para enviar correo.")

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("[FACTURA] ✅ Factura procesada exitosamente.")

    except Exception as e:
        print(f"[FACTURA] Error al procesar mensaje: {e}")
        traceback.print_exc()
        ch.basic_ack(delivery_tag=method.delivery_tag)

# Intentar conexión a RabbitMQ y escuchar la cola
def consumir():
    intentos = 10
    for i in range(intentos):
        try:
            print(f"[FACTURA] Intentando conectar a RabbitMQ ({i+1}/{intentos}) en host '{RABBITMQ_HOST}'...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(RABBITMQ_HOST, 5672, heartbeat=600, blocked_connection_timeout=300)
            )
            channel = connection.channel()
            channel.queue_declare(queue='cola_facturas', durable=True)
            channel.basic_consume(queue='cola_facturas', on_message_callback=callback, auto_ack=False)
            print("[FACTURA] Conectado y esperando mensajes en 'cola_facturas'...")
            channel.start_consuming()
            break
        except pika.exceptions.AMQPConnectionError as e:
            print(f"[FACTURA] No se pudo conectar a RabbitMQ: {e}. Reintentando en 5 segundos...")
            time.sleep(5)
        except Exception as e:
            print(f"[FACTURA] Error inesperado al conectar a RabbitMQ: {e}")
            traceback.print_exc()
            break

# Iniciar consumidor al ejecutar el script
if __name__ == "__main__":
    print("[FACTURA] Iniciando consumidor de facturas...")
    consumir()
