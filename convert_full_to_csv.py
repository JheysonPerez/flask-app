import re
import csv
import os

input_file = 'backup_completo.sql'
output_dir = 'csvs_migracion'
os.makedirs(output_dir, exist_ok=True)

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extrae esquemas para columnas (de CREATE TABLE) - regex fix para 'public.tabla'
table_schemas = {}
create_matches = re.findall(r'CREATE TABLE ([\w.]+) \((.*?)\);', content, re.DOTALL | re.IGNORECASE)
for full_table_name, cols_def in create_matches:
    table_name = full_table_name.split('.')[-1]  # Solo 'categorias'
    cols = re.findall(r'^\s*(\w+)\s+\w+', cols_def, re.MULTILINE)
    table_schemas[table_name] = cols

print(f'Schemas encontrados: {list(table_schemas.keys())}')

# Maneja COPY (principal para tu dump) - regex fix para 'public.tabla'
copy_sections = re.split(r'(?=COPY [\w.]+)', content)
current_table = None
current_columns = []
all_rows = []

for section in copy_sections:
    if not section.strip():
        continue
    
    # Detecta COPY public.tabla (col1, col2) FROM stdin;
    copy_match = re.search(r'COPY ([\w.]+) \(([^)]+)\) FROM stdin;', section, re.IGNORECASE)
    if copy_match:
        full_table_name = copy_match.group(1)
        current_table = full_table_name.split('.')[-1]  # Solo 'categorias'
        cols_str = copy_match.group(2)
        current_columns = [col.strip().strip('"') for col in cols_str.split(',')] if cols_str else table_schemas.get(current_table, [])
        
        # Extrae datos hasta \.
        data_start = section.find('FROM stdin;') + len('FROM stdin;')
        data_end = section.find('\\.', data_start)
        if data_end == -1:
            data_end = len(section)
        data_lines = section[data_start:data_end].strip().split('\n')
        
        all_rows = []
        for line in data_lines:
            if line.strip() and line.strip() != '\\.':
                # Split por tab (\t), maneja \N para NULL
                fields = line.split('\t')
                cleaned_row = []
                for field in fields:
                    field = field.strip()
                    if field == '\\N':
                        cleaned_row.append('')
                    else:
                        # Limpia escapes
                        field = field.replace('\\"', '"').replace("''", "'")
                        cleaned_row.append(field)
                if len(cleaned_row) == len(current_columns):
                    all_rows.append(cleaned_row)
        
        # Guarda CSV si hay datos
        if all_rows:
            csv_path = os.path.join(output_dir, f'{current_table}.csv')
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                if current_columns:
                    writer.writerow(current_columns)
                writer.writerows(all_rows)
            print(f'CSV creado: {csv_path} ({len(all_rows)} filas)')
        
        current_table = None
        current_columns = []
        all_rows = []

# Si hay INSERTs (por si acaso), maneja como antes - regex fix
insert_sections = re.split(r'(?=INSERT INTO [\w.]+)', content)
for section in insert_sections:
    if not section.strip():
        continue
    
    table_match = re.search(r'INSERT INTO ([\w.]+)', section)
    if table_match:
        full_table_name = table_match.group(1)
        current_table = full_table_name.split('.')[-1]
        cols_match = re.search(r'\(([^)]+)\)', section)
        if cols_match:
            current_columns = [col.strip().strip('"').strip('`') for col in cols_match.group(1).split(',')]
        all_rows = []
        continue
    
    if current_table:
        values_match = re.findall(r'\(([^)]+)\)', section)
        for val_group in values_match:
            vals = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', val_group)
            cleaned_vals = []
            for v in vals:
                v = v.strip().strip("'").strip('"')
                cleaned_vals.append('' if v.upper() == 'NULL' else v)
            if len(cleaned_vals) == len(current_columns):
                all_rows.append(cleaned_vals)
        
        if all_rows:
            csv_path = os.path.join(output_dir, f'{current_table}.csv')
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                if current_columns:
                    writer.writerow(current_columns)
                writer.writerows(all_rows)
            print(f'CSV creado (INSERT): {csv_path} ({len(all_rows)} filas)')

print('¡Conversión completada! Revisa csvs_migracion/.')