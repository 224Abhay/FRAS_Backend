from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

admin = Blueprint('admin', __name__)

@admin.route('/branches', methods=['POST'])
@jwt_required()
def create_branch():
    data = request.get_json()
    
    branch_name = data.get('branch_name')
    course_duration = data.get('course_duration')
    
    if not branch_name or not course_duration:
        if not isinstance(course_duration, int) or course_duration <= 0:
            return jsonify({'message': 'Branch not created.', 'error': 'Required Parameters not provided properly.'}), 400
        
        return jsonify({'message': 'Branch not created.', 'error': 'Required Parameters not provided.'}), 400

    query = "INSERT INTO branch (branch_name, course_duration) VALUES (%s, %s)"
    current_app.config['DATABASE'].execute_query(query, (branch_name, course_duration))
    
    return jsonify({'message': 'Branch created successfully'}), 201

@admin.route('/branches', methods=['GET'])
@jwt_required()
def get_branches():
    query = "SELECT * FROM branch"
    result = current_app.config['DATABASE'].execute_query(query)

    branches = []
    if result:
        for row in result:
            branches.append({
                'branch_id': row[0],
                'branch_name': row[1],
                'course_duration': row[2]
            })

    return jsonify(branches), 200

@admin.route('/subjects', methods=['POST'])
@jwt_required()
def create_subject():
    data = request.get_json()
    subject_code = data.get('subject_code')
    subject_name = data.get('subject_name')

    if not subject_code or not subject_name:
        return jsonify({'message': 'Subject not created', 'error': 'Required Parameters are not provided.'}), 400

    query = "INSERT INTO subject (subject_code, subject_name) VALUES (%s, %s)"
    current_app.config['DATABASE'].execute_query(query, (subject_code, subject_name))

    return jsonify({'message': 'Subject created successfully'}), 201

@admin.route('/subjects', methods=['GET'])
@jwt_required()
def get_subjects():
    class_id = request.args.get('class_id')

    if class_id:
        query = """
            SELECT cs.subject_code, cs.teacher_id, c.class_id
            FROM class_subjects cs
            JOIN class c ON cs.class_id = c.class_id
            WHERE c.class_id = %s
        """
        result = current_app.config['DATABASE'].execute_query(query, (class_id,))

        subjects = []
        if result:
            for row in result:
                subjects.append({
                    'subject_code': row[0],
                    'teacher_id': row[1],
                    'class_id': row[2]
                })

        if subjects:
            return jsonify(subjects), 200
        else:
            return jsonify({'message': 'No subjects found for the given class ID'}), 404

    else:
        query = "SELECT subject_code, subject_name FROM subject"
        result = current_app.config['DATABASE'].execute_query(query)

        subjects = []
        if result:
            for row in result:
                subjects.append({
                    'subject_code': row[0],
                    'subject_name': row[1]
                })

        return jsonify(subjects), 200


@admin.route('/batches', methods=['POST'])
def create_batch():
    data = request.get_json()
   
    branch_id = data.get('branch_id')
    batch_of = data.get('batch_of')
    batch = data.get('batch')

    if not branch_id or not batch_of or not batch:
        return jsonify({'message': 'branch ID, batch of (year), and batch are required'}), 400

    try:
        query = """
            INSERT INTO batch (branch_id, batch_of, batch) 
            VALUES (%s, %s, %s)
        """
        current_app.config['DATABASE'].execute_query(query, (branch_id, batch_of, batch))

        return jsonify({'message': 'batch created successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Failed to create batch', 'error': str(e)}), 500

@admin.route('/batches', methods=['GET'])
@jwt_required()
def get_batches():
    branch_id = request.args.get('branch_id')

    query = "SELECT batch_id, batch_of, batch FROM batch WHERE branch_id = %s ORDER BY batch_of DESC, batch"

    result = current_app.config['DATABASE'].execute_query(query, (branch_id,))

    batches = []
    if result:
        for row in result:
            batch_info = {
                'batch_id': row[0],
                'batch_of': row[1],
                'batch': row[2]
            }
            batches.append(batch_info)

    return jsonify(batches), 200

@admin.route('/classes', methods=['POST'])
def create_class():
    data = request.get_json()
    
    # Extract the required fields from the request
    batch_id = data.get('batch_id')
    year = data.get('year')
    semester_type = data.get('semester_type')

    # Validate input
    if not batch_id or not year or not semester_type:
        return jsonify({'message': 'batch ID, year, and semester type are required'}), 400

    # Validate semester_type input
    if semester_type not in ['S', 'A']:  # Check if semester_type is valid
        return jsonify({'message': 'semester type must be either "S" (Spring) or "A" (Autumn)'}), 400

    try:
        # Insert into the database
        query = """
            INSERT INTO class (batch_id, year, semester_type) 
            VALUES (%s, %s, %s)
        """
        current_app.config['DATABASE'].execute_query(query, (batch_id, year, semester_type))

        return jsonify({'message': 'class created successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Failed to create class', 'error': str(e)}), 500

@admin.route('/classes', methods=['GET'])
@jwt_required()
def get_classes():
    branch_id = request.args.get('batch_id')

    query = "SELECT class_id, year, semester_type FROM class WHERE batch_id = %s ORDER BY year DESC, semester_type"

    result = current_app.config['DATABASE'].execute_query(query, (branch_id,))

    classes = []
    if result:
        for row in result:
            batch_info = {
                'class_id': row[0],
                'year': row[1],
                'semester_type': row[2]
            }
            classes.append(batch_info)

    return jsonify(classes), 200

@admin.route('/students', methods=['POST'])
@jwt_required()
def create_student():
    data = request.get_json()

    student_id = data.get('student_id')  # Now student_id is provided
    student_name = data.get('student_name').capitalize()
    student_surname = data.get('student_surname').capitalize()
    student_email = data.get('student_email').lower()
    batch_id = data.get('batch_id')

    try:
        query = """
            INSERT INTO credential (email_id, role) 
            VALUES (%s, %s)
        """

        current_app.config['DATABASE'].execute_query(query, (student_email, "student"))

        query = """
            INSERT INTO student (student_id, student_name, student_surname, student_email, batch_id) 
            VALUES (%s, %s, %s, %s, %s)
        """
        current_app.config['DATABASE'].execute_query(query, (student_id, student_name, student_surname, student_email, batch_id))

        return jsonify({'message': 'Student created successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Failed to create student', 'error': str(e)}), 500

@admin.route('/teachers', methods=['POST'])
@jwt_required()
def create_teacher():
    data = request.get_json()

    teacher_name = data.get('teacher_name').capitalize()
    teacher_surname = data.get('teacher_surname').capitalize()
    teacher_email = data.get('teacher_email').lower()

    try:

        query = """
            INSERT INTO credential (email_id, role) 
            VALUES (%s, %s)
        """

        current_app.config['DATABASE'].execute_query(query, (teacher_email, "teacher"))

        
        query = """
            INSERT INTO teacher (teacher_name, teacher_surname, teacher_email) 
            VALUES (%s, %s, %s)
        """
        current_app.config['DATABASE'].execute_query(query, (teacher_name, teacher_surname, teacher_email))

        return jsonify({'message': 'Teacher created successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Failed to create teacher', 'error': str(e)}), 500

@admin.route('/teachers', methods=['GET'])
@jwt_required()
def get_teachers():
    # Query to retrieve all teachers
    query = "SELECT teacher_id, teacher_name, teacher_surname, teacher_email FROM teacher ORDER BY teacher_name, teacher_surname"
    result = current_app.config['DATABASE'].execute_query(query)

    teachers = []
    if result:
        for row in result:
            teacher_info = {
                'teacher_id': row[0],
                'teacher_name': row[1],
                'teacher_surname': row[2],              # Include year
                'teacher_email': row[3],             # Include batch
            }
            teachers.append(teacher_info)
    
    # Return the list of teachers as JSON
    return jsonify(teachers), 200

@admin.route('/assign_subject', methods=['POST'])
@jwt_required()
def assign_subject():
    data = request.get_json()

    batch_id = data.get('class_id')
    subject_code = data.get('subject_code')  # Changed to match your structure
    teacher_id = data.get('teacher_id')      # Added teacher_id

    if not batch_id or not subject_code or not teacher_id:
        return jsonify({'message': 'Class ID, Subject Code, and Teacher ID are required'}), 400

    try:
        # Insert into the class_subjects table
        query = """
            INSERT INTO class_subjects (class_id, subject_code, teacher_id) 
            VALUES (%s, %s, %s)
        """
        current_app.config['DATABASE'].execute_query(query, (batch_id, subject_code, teacher_id))

        return jsonify({'message': 'Subject assigned to class successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Failed to assign subject to class', 'error': str(e)}), 500

@admin.route('/timetable', methods=['POST'])
@jwt_required()
def add_timetable_entry():
    data = request.get_json()
    query = """
        INSERT INTO timetable (subject_code, class_id, start_time, end_time, room_number, day)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    current_app.config['DATABASE'].execute_query(query, (
        data['subject_code'], 
        data['class_id'], 
        data['start_time'], 
        data['end_time'], 
        data['room_number'], 
        data['day']
    ))
    return jsonify({'message': 'Timetable entry created successfully'}), 201

    
@admin.route('/timetable', methods=['GET'])
@jwt_required()
def get_timetable():
    class_id = request.args.get('class_id')
    
    if class_id is None:
        return jsonify({"error": "class_id is required"}), 400
    
    query = """
        SELECT timetable_id, subject_code, start_time, end_time, room_number, day
        FROM timetable
        WHERE class_id = %s
        ORDER BY FIELD(day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), start_time
    """
    result = current_app.config['DATABASE'].execute_query(query, (class_id,))
    
    if not result:
        return jsonify([]), 200
    
    timetable = []
    if result:
        for row in result:
            timetable_info = {
                'timetable_id': row[0],
                'subject_code': row[1],
                'start_time': str(row[2]),
                'end_time': str(row[3]),
                'room_number': row[4],
                'day': row[5],
            }
            timetable.append(timetable_info)

    return jsonify(timetable), 200

@admin.route('/timetable', methods=['DELETE'])
@jwt_required()
def delete_timetable_entry(timetable_id):
    query = "DELETE FROM timetable WHERE timetable_id = %s"
    current_app.config['DATABASE'].execute_query(query, (timetable_id,))
    return jsonify({'message': 'Timetable entry deleted successfully'}), 200

@admin.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "server working"}), 200