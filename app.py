from flask import Flask, jsonify, render_template, request
import sqlite3
import MySQLdb
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Cambia esto a una clave secreta real

def extract_schema(sqlite_db):
    """Extracts the schema from the SQLite database."""
    conn = sqlite3.connect(sqlite_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema = {}
    for table_name in tables:
        table_name = table_name[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        schema[table_name] = [(col[1], col[2]) for col in columns]  # (column_name, data_type)
    
    conn.close()
    return schema

def create_mysql_schema(mysql_config, schema, ssl_cert):
    """Creates the MySQL schema based on the extracted SQLite schema."""
    # Guardar el certificado SSL en un archivo temporal
    with tempfile.NamedTemporaryFile(delete=False) as temp_ssl_cert:
        temp_ssl_cert.write(ssl_cert)
        temp_ssl_cert.flush()
        ssl_cert_path = temp_ssl_cert.name

    conn = MySQLdb.connect(**mysql_config, ssl={'ca': ssl_cert_path})
    cursor = conn.cursor()
    
    total_tables = len(schema)
    processed_tables = 0
    
    for table, columns in schema.items():
        # Verificar si la tabla ya existe
        cursor.execute(f"SHOW TABLES LIKE '{table}';")
        if cursor.fetchone():
            print(f"Tabla {table} ya existe, se salta.")
            processed_tables += 1
            continue
        
        column_defs = []
        for name, dtype in columns:
            # Escapar nombres de columnas
            escaped_name = f"`{name}`"
            column_defs.append(f"{escaped_name} {dtype}")
        
        column_defs_str = ', '.join(column_defs)
        create_table_query = f"CREATE TABLE `{table}` ({column_defs_str});"
        
        try:
            cursor.execute(create_table_query)
        except MySQLdb.ProgrammingError as e:
            print(f"Error creando la tabla {table}: {e}")
        
        processed_tables += 1
        # Aquí podrías enviar el progreso a través de un mecanismo de WebSocket o similar

    conn.commit()
    cursor.close()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles the main page and migration process."""
    if request.method == 'POST':
        sqlite_db = request.form['sqlite_db']
        mysql_config = {
            'user': request.form['mysql_user'],
            'passwd': request.form['mysql_password'],
            'host': request.form['mysql_host'],
            'db': request.form['mysql_database']
        }
        
        ssl_cert = request.files['ssl_cert'].read() if 'ssl_cert' in request.files else None
        
        schema = extract_schema(sqlite_db)
        create_mysql_schema(mysql_config, schema, ssl_cert)
        
        return jsonify({"message": "¡Migración completada con éxito!"})
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
