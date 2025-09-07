from locust import HttpUser, task, between
import random

class PublicProductUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def obtener_productos_publicos(self):
        """Consulta pública de productos"""
        with self.client.get("/api/productos", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("La respuesta no es una lista de productos.")
                except Exception as e:
                    response.failure(f"Error al parsear JSON: {e}")
            else:
                response.failure(f"Status {response.status_code}: {response.text}")


class DashboardVentasUser(HttpUser):
    wait_time = between(2, 4)

    @task
    def obtener_dashboard_ventas(self):
        """Consulta pública del dashboard de ventas"""
        with self.client.get("/api/dashboard/ventas", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "fechas" in data and "montos" in data:
                        response.success()
                    else:
                        response.failure("Faltan datos en la respuesta.")
                except Exception as e:
                    response.failure(f"Error al parsear JSON: {e}")
            else:
                response.failure(f"Status {response.status_code}: {response.text}")


class ClienteProductosTestUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def obtener_productos_clientes(self):
        """Consulta pública de productos creados por clientes"""
        with self.client.get("/cliente/test/productos_clientes", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Respuesta no es una lista de productos de clientes.")
                except Exception as e:
                    response.failure(f"Error al parsear JSON: {e}")
            else:
                response.failure(f"Status {response.status_code}: {response.text}")


class CategoriasPublicUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def listar_categorias(self):
        """Consulta pública de categorías"""
        with self.client.get("/categorias/", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("La respuesta no es una lista de categorías.")
                except Exception as e:
                    response.failure(f"Error al parsear JSON: {e}")
            else:
                response.failure(f"Status {response.status_code}: {response.text}")


class CompraTestUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def realizar_compra(self):
        """Simula una compra (modo test)"""
        tipo_comprobante = random.choice(["boleta", "factura"])

        datos_compra = {
            "cliente_id": 2,
            "tipo_comprobante": tipo_comprobante,
            "email_destino": "jheysonperezramirez6@gmail.com"
        }

        if tipo_comprobante == "boleta":
            datos_compra["dni"] = "72257140"
        else:
            datos_compra["ruc"] = "20123456789"

        with self.client.post("/api/test/compra", json=datos_compra, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                try:
                    error = response.json()
                    mensaje_error = error.get("msg", "") + " | " + error.get("error", "")
                except Exception:
                    mensaje_error = response.text
                response.failure(f"[Compra Fallida] Status {response.status_code} → {mensaje_error}")
