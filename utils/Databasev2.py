from mysql.connector import pooling, errors

host = "localhost"
user = "root"
password = "S@msun2204" 
database = "fras"

# Set up the connection pool
pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    pool_reset_session=True,
    host=host,
    user=user,
    password=password,
    database=database
)

def get_connection():
    """Get a connection from the pool."""
    try:
        return pool.get_connection()
    except errors.PoolError as e:
        print(f"Error getting connection from pool: {e}")
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
    except (errors.DatabaseError, Exception) as e:
        print(f"An error occurred: {e}")
        try:
            connection.rollback()
        except errors.Error as rollback_error:
            print(f"Rollback failed: {rollback_error}")
        return None
    finally:
        connection.close()