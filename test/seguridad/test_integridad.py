import requests
import re
from app.extensions import db
from app.main import create_app
from app.models.usuario import Usuario
from sqlalchemy import inspect, CheckConstraint, event
from sqlalchemy.orm import Session
from sqlalchemy import String, Text, Integer
import os
from pathlib import Path

app = create_app()


def test_integridad_datos(app_url="http://127.0.0.1:5000"):
    """SIn-1-G: Protección contra modificaciones no autorizadas"""
    from flask import current_app
    import re
    
    rutas_modificacion = []
    with app.test_request_context():
        for rule in current_app.url_map.iter_rules():
            # Buscar rutas que sugieren modificación de datos
            if any(x in rule.rule.lower() for x in ['edit', 'actualizar', 'modificar', 'update', 'delete', 'remove']):
                ruta_concreta = re.sub(r'<[^>]+>', '1', rule.rule)
                rutas_modificacion.append(ruta_concreta)
    
    print(f"\nRutas de modificación detectadas: {rutas_modificacion}")
    modificaciones_no_autorizadas = 0
    total_rutas = len(rutas_modificacion)
    rutas_modificadas = []
    rutas_protegidas = []

    for ruta in rutas_modificacion:
        try:
            r = requests.post(app_url + ruta, data={"campo": "valor_modificado"}, allow_redirects=False)
            if r.status_code in [200, 201]:
                modificaciones_no_autorizadas += 1
                rutas_modificadas.append((ruta, r.status_code))
            else:
                rutas_protegidas.append((ruta, r.status_code if r is not None else None))
        except Exception as e:
            print(f"Error probando modificación en {ruta}: {e}")

    X = 1 - (modificaciones_no_autorizadas / total_rutas) if total_rutas > 0 else 1
    print("\n" + "="*80)
    print("                           TEST DE INTEGRIDAD")
    print("="*80)
    print("\nMétrica SIn-1-G: Protección contra Modificaciones No Autorizadas")
    print("-"*65)
    print("Fórmula: X = 1 - (A / B)")
    print(f"A = {modificaciones_no_autorizadas} modificaciones no autorizadas")
    print(f"B = {total_rutas} rutas críticas")
    print(f"Resultado: X = {X:.2f}")
    if rutas_modificadas:
        print("Rutas modificadas sin protección:")
        for r, s in rutas_modificadas:
            print(f" - {r} -> status {s}")
    if rutas_protegidas:
        print("Rutas protegidas (no modificadas):")
        for r, s in rutas_protegidas:
            print(f" - {r} -> status {s}")
    assert X >= 0.8, f"SIn-1-G: Integridad débil ({modificaciones_no_autorizadas}/{total_rutas} accesos no protegidos)"


def test_prevencion_corrupcion_interna():
    print("\nMétrica SIn-2-G: Prevención de Corrupción Interna")
    print("-"*65)
    print("Fórmula: X = A / B")

    controles = {
        "validaciones_orm": {
            "descripcion": "validaciones ORM (nullable=False / CheckConstraint / validaciones)",
            "detectado": False,
            "detalles": []
        },
        "integridad_referencial": {
            "descripcion": "restricciones de integridad referencial (ForeignKey)",
            "detectado": False,
            "detalles": []
        },
        "transacciones_seguras": {
            "descripcion": "uso de transacciones seguras (session.begin / context manager)",
            "detectado": False,
            "detalles": []
        },
        "backups_automaticos": {
            "descripcion": "backups automáticos",
            "detectado": False,
            "detalles": []
        }
    }

    # 1. Detectar validaciones ORM y FK inspeccionando modelos
    with app.app_context():
        for table_name, table in db.metadata.tables.items():
            # Revisar columnas para nullable=False y foreign keys
            for column in table.columns:
                if not column.nullable:
                    controles["validaciones_orm"]["detectado"] = True
                    controles["validaciones_orm"]["detalles"].append(
                        f"{table_name}.{column.name}: not nullable"
                    )
                
                if column.foreign_keys:
                    controles["integridad_referencial"]["detectado"] = True
                    for fk in column.foreign_keys:
                        controles["integridad_referencial"]["detalles"].append(
                            f"{table_name}.{column.name} -> {fk.target_fullname}"
                        )
            
            # Revisar constraints a nivel de tabla
            for constraint in table.constraints:
                if isinstance(constraint, CheckConstraint):
                    controles["validaciones_orm"]["detectado"] = True
                    controles["validaciones_orm"]["detalles"].append(
                        f"{table_name}: {constraint}"
                    )

    # 2. Detectar uso de transacciones
    from flask import current_app
    import inspect
    
    # Buscar en rutas y modelos
    def scan_source_for_transactions(obj):
        if hasattr(obj, "__source__"):
            source = obj.__source__
        else:
            try:
                source = inspect.getsource(obj)
            except:
                return
                
        if re.search(r"session\.begin|db\.session\.begin|with\s+db\.session|@db\.session", source):
            controles["transacciones_seguras"]["detectado"] = True
            controles["transacciones_seguras"]["detalles"].append(
                f"Transacción detectada en {obj.__name__}"
            )

    # Buscar en blueprints y vistas
    with app.test_request_context():
        for endpoint, view_func in current_app.view_functions.items():
            if hasattr(view_func, "view_class"):
                scan_source_for_transactions(view_func.view_class)
            else:
                scan_source_for_transactions(view_func)
                
    # 3. Detectar backups automáticos 
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    backup_indicators = {
        "archivos": [
            r"backup.*\.sh$",
            r".*dump.*\.sql$",
            r"cron.*backup.*",
            r"docker-compose.*\.ya?ml$"
        ],
        "contenido": [
            r"pg_dump",
            r"mysqldump",
            r"backup",
            r"BACKUP",
            r"cron\.d"
        ]
    }
    
    def check_file_content(filepath):
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                for pattern in backup_indicators["contenido"]:
                    if re.search(pattern, content):
                        controles["backups_automaticos"]["detectado"] = True
                        controles["backups_automaticos"]["detalles"].append(
                            f"Backup detectado en {filepath}: {pattern}"
                        )
                        return True
        except:
            pass
        return False
    
    # Buscar evidencia de backups
    for root, _, files in os.walk(repo_root):
        for fname in files:
            # Verificar nombre de archivo
            for pattern in backup_indicators["archivos"]:
                if re.search(pattern, fname, re.IGNORECASE):
                    filepath = os.path.join(root, fname)
                    controles["backups_automaticos"]["detectado"] = True
                    controles["backups_automaticos"]["detalles"].append(
                        f"Archivo de backup encontrado: {fname}"
                    )
                    check_file_content(filepath)
            
            # Verificar contenido de archivos de configuración
            if fname in ["docker-compose.yml", "docker-compose.yaml", "Procfile", "crontab"]:
                filepath = os.path.join(root, fname)
                check_file_content(filepath)
                
    # Generar reporte
    implementados = [k for k, v in controles.items() if v["detectado"]]
    faltantes = [k for k, v in controles.items() if not v["detectado"]]
    
    A = len(implementados)
    B = len(controles)
    X = A / B if B > 0 else 1
    
    print("\nControles implementados:")
    for control in implementados:
        print(f"\n- {controles[control]['descripcion']}:")
        for detalle in controles[control]["detalles"]:
            print(f"  * {detalle}")
            
    print("\nControles faltantes:")
    for control in faltantes:
        print(f"- {controles[control]['descripcion']}")
        
    print(f"\nA = {A} controles implementados")
    print(f"B = {B} controles recomendados")
    print(f"Resultado: X = {X:.2f}")
    
    assert X >= 0.5, "SIn-2-G: Pocas medidas internas de integridad implementadas"


def test_prevencion_desbordamiento():
    print("\nMétrica SIn-3-S: Prevención de Desbordamiento de Datos")
    print("-"*65)
    print("Fórmula: X = A / B")
    
    entradas_revisadas = {}
    
    with app.app_context():
        for table_name, table in db.metadata.tables.items():
            for column in table.columns:
                # Solo nos interesan campos de texto/string que podrían desbordarse
                if isinstance(column.type, (String, Text)):
                    maxlen = getattr(column.type, 'length', None)
                    tipo = 'string' if isinstance(column.type, String) else 'text'
                    entradas_revisadas[f"{table_name}.{column.name}"] = {
                        "maxlength": maxlen,
                        "type": tipo
                    }

    accesos_controlados = sum(1 for v in entradas_revisadas.values() if v["maxlength"])
    total_accesos = len(entradas_revisadas)
    X = accesos_controlados / total_accesos if total_accesos > 0 else 0
    campos_con_limite = [name for name, v in entradas_revisadas.items() if v["maxlength"]]
    campos_sin_limite = [name for name, v in entradas_revisadas.items() if not v["maxlength"]]

    print(f"A = {accesos_controlados} campos con límites definidos: {campos_con_limite}")
    print(f"B = {total_accesos} campos totales analizados: {list(entradas_revisadas.keys())}")
    if campos_sin_limite:
        print("Campos sin límite de longitud detectados (posible riesgo de desbordamiento):")
        for c in campos_sin_limite:
            print(f" - {c} (type={entradas_revisadas[c]['type']})")
    print(f"Resultado: X = {X:.2f}")
    assert X >= 0.75, "SIn-3-S: Falta control de límites en campos de entrada"


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        test_integridad_datos()
        test_prevencion_corrupcion_interna()
        test_prevencion_desbordamiento()
