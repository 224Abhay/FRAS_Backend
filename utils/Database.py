import mysql.connector
from mysql.connector import Error

host = "localhost"
user = "root"
password = "S@msun2204"
database = "fras"

def get_connection():
    """Establish a direct connection to the database."""
    try:
        return mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
    except Error as e:
        print(f"Error connecting to the database: {e}")
        return None

def execute_query(query, params=None):
    connection = get_connection()
    if connection is None:
        print("No connection available.")
        return None

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            else:
                connection.commit()
                return None
    except Error as e:
        print(f"An error occurred: {e}")
        try:
            connection.rollback()
        except Error as rollback_error:
            print(f"Rollback failed: {rollback_error}")
        return None
    finally:
        connection.close()
