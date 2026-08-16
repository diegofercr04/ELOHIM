import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        conn = mysql.connector.connect(
            host     = "bqwqkwibpyrhqrgzogtz-mysql.services.clever-cloud.com",
            port     = 3306,
            user     = "u6a7ljiihtq4xord",
            password = "sGwCSZAc1jljmQ3nfr54",
            database = "bqwqkwibpyrhqrgzogtz"
        )
        return conn
    except Error:
        return None
