from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required
import utils.Databasev2 as db_connection
from routes.authentication import authentication
from routes.student import student
from routes.teacher import teacher
from routes.admin import admin
import datetime

# cloudflared tunnel --url http://localhost:5000

app = Flask(__name__)
app.register_blueprint(authentication, url_prefix='/auth')
app.register_blueprint(student, url_prefix='/student')
app.register_blueprint(teacher, url_prefix='/teacher')
app.register_blueprint(admin, url_prefix='/admin')

app.config['SECRET_KEY'] = '1042ddc714c0fb5544eb905972575812cc23719610ab2549'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 60 * 60 * 24
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 60 * 60 * 24 * 10

bcrypt = Bcrypt(app)
app.config['BCRYPT'] = bcrypt

app.config['DATABASE'] = db_connection
app.config['JWT_VERIFY_SUB'] = False
jwt = JWTManager(app)

blacklist = set()
@jwt.token_in_blocklist_loader
def check_if_token_in_blacklist(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return jti in blacklist

@app.route('/students', methods=['GET'])
@jwt_required()
def get_students():
    batch_id = request.args.get('batch_id')

    query = "SELECT student_id, student_name, student_surname, student_email FROM student"
    params = []

    if batch_id:
        query += " WHERE batch_id = %s"
        params.append(batch_id)

    result = db_connection.execute_query(query, params)

    students = []
    if result:
        for row in result:
            student_info = {
                'student_id': row[0],
                'student_name': row[1],
                'student_surname': row[2],
                'student_email': row[3],
            }
            students.append(student_info)

    return jsonify(students), 200

@app.route('/get_holidays', methods=['GET'])
def get_holidays():
    # Get the year from the query parameters
    year = request.args.get('year')
    
    try:
        year = int(year)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid year."}), 400

    # Query to fetch holidays for the specified year from the database
    query = "SELECT date, holiday_name FROM holiday_list WHERE YEAR(date) = %s"
    params = [year]

    result = db_connection.execute_query(query, params)

    holidays_for_year = {}
    if result:
        for row in result:
            holiday_date = row[0].strftime("%Y-%m-%d")
            holiday_name = row[1]
            holidays_for_year[holiday_date] = holiday_name

    # Return the holidays as a JSON response
    return jsonify(holidays_for_year), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)