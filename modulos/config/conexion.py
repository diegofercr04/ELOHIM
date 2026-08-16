import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        conn = mysql.connector.connect(
            host     = "be5bmntqvmjb45dbc68h-mysql.services.clever-cloud.com",
            port     = 3306,
            user     = "ufrsewvahgrdaghy",
            password = "UxDnJbPxibZaLwBC6Xt1",
            database = "be5bmntqvmjb45dbc68h",
        )
        return conn
    except Error:
        return None
