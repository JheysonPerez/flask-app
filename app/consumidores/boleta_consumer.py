# Librerías necesarias: entorno, JSON, tiempo, errores, mensajería, email y carga de .env
import os
import json
import time
import traceback
import pika
from email.message import EmailMessage
import smtplib
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno desde el archivo .env

# Configuración de variables desde el entorno
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')

SMTP_SERVER   = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
SMTP_PORT     = int(os.getenv('MAIL_PORT', 587))
SMTP_USER     = os.getenv('MAIL_USERNAME')
SMTP_PASS     = os.getenv('MAIL_PASSWORD')
MAIL_USE_TLS  = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'

boletas = []   # Lista para almacenar boletas recibidas

# Envía un correo electrónico con los detalles de la boleta
def enviar_correo(destino, asunto, cuerpo):
    try:
        if not SMTP_USER or not SMTP_PASS:
            raise ValueError("Credenciales SMTP no configuradas correctamente")

        msg = EmailMessage()
        msg["Subject"] = asunto
        msg["From"]    = SMTP_USER
        msg["To"]      = destino
        msg.set_content(cuerpo)

        print(f"[EMAIL] Conectando a {SMTP_SERVER}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            if MAIL_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[EMAIL] Correo enviado exitosamente a {destino}")
    except Exception as e:
        print(f"[EMAIL] Error al enviar correo: {e}")
        traceback.print_exc()

# Función que procesa los mensajes recibidos desde RabbitMQ
def callback(ch, method, properties, body):
    try:
        print(f"[BOLETA] Mensaje recibido: {body}")
        data = json.loads(body)

        if not isinstance(data, dict):
            raise ValueError("El cuerpo del mensaje no es un JSON válido")

        # Solo procesa si es boleta
        if data.get("tipo_comprobante") != "boleta":
            print("[BOLETA] Ignorado: no es boleta")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Almacena boleta en memoria tal cual llega
        boletas.append(data)
        print(f"[BOLETA] Boleta almacenada: {data}")

        # Envia correo si se especificó destino
        email_destino = data.get("email_destino")
        if email_destino:
            cuerpo = "Detalle de la boleta:\n\n" + \
                     "\n".join(f"{k}: {v}" for k, v in data.items())
            enviar_correo(
                destino=email_destino,
                asunto=f"Boleta {data.get('numero', 'N/A')}",
                cuerpo=cuerpo
            )
        else:
            print("[BOLETA] 'email_destino' no presente; no se envía correo.")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[BOLETA] Error procesando mensaje: {e}")
        traceback.print_exc()
        ch.basic_ack(delivery_tag=method.delivery_tag)

# Conexión con RabbitMQ y consumo de mensajes de la cola 'cola_boletas'
def consumir():
    intentos = 10
    for i in range(intentos):
        try:
            print(f"[BOLETA] Conectando a RabbitMQ ({i+1}/{intentos}) en '{RABBITMQ_HOST}'…")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(RABBITMQ_HOST, 5672,
                                          heartbeat=600,
                                          blocked_connection_timeout=300)
            )
            channel = connection.channel()
            channel.queue_declare(queue="cola_boletas", durable=True)
            channel.basic_consume(queue="cola_boletas",
                                  on_message_callback=callback,
                                  auto_ack=False)
            print("[BOLETA] Conectado y esperando mensajes en 'cola_boletas'…")
            channel.start_consuming()
            break
        except pika.exceptions.AMQPConnectionError as e:
            print(f"[BOLETA] No se pudo conectar: {e}. Reintentando en 5 s…")
            time.sleep(5)
        except Exception as e:
            print(f"[BOLETA] Error inesperado: {e}")
            traceback.print_exc()
            break

# Punto de entrada principal del script
if __name__ == "__main__":
    print("[BOLETA] Iniciando consumidor de boletas…")
    consumir()
