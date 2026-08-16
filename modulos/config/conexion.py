import mysql.connector
from mysql.connector import Error
import time

def get_connection(intentos=3):
    for i in range(intentos):
        try:
            conn = mysql.connector.connect(
                host               = "be5bmntqvmjb45dbc68h-mysql.services.clever-cloud.com",
                port               = 3306,
                user               = "ufrsewvahgrdaghy",
                password           = "UxDnJbPxibZaLwBC6Xt1",
                database           = "be5bmntqvmjb45dbc68h",
                connection_timeout = 10,
                autocommit         = False,
                use_pure           = True    # ← fuerza el conector puro de Python
            )                               #   evita problemas con C-extension
            if conn.is_connected():
                return conn
        except Error:
            if i < intentos - 1:
                time.sleep(1)
            continue
    return None
