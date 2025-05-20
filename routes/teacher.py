import base64
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from utils.functions import convert_flutter_to_mysql_time
import os

teacher = Blueprint('teacher', __name__)

@teacher.route('/classes', methods=['GET'])
@jwt_required()
def get_classes():
    teacher_id = request.args.get('teacher_id')

    query = """
        SELECT 
            cs.class_id, 
            cs.subject_code,
            c.batch_id,
            c.year,
            c.semester_type,
            b.branch_id,
            br.branch_name,
            br.course_duration,
            b.batch_of,
            b.batch
        FROM class_subjects cs
        JOIN class c ON cs.class_id = c.class_id
        JOIN batch b ON c.batch_id = b.batch_id
        JOIN branch br ON b.branch_id = br.branch_id
        WHERE cs.teacher_id = %s;
    """

    result = current_app.config['DATABASE'].execute_query(query, (teacher_id,))

    classes = []
    if result:
        for row in result:
            cs_info = {
                'class_id': row[0],
                'subject_code': row[1],
                'batch_id': row[2],
                'year': row[3],
                'semester_type': row[4],
                'branch_id': row[5],
                'branch_name': row[6],
                'course_duration': row[7],
                'batch_of': row[8],
                'batch': row[9],
            }
            classes.append(cs_info)

    return jsonify(classes), 200

@teacher.route('/schedule', methods=['POST'])
@jwt_required()
def get_teacher_schedule():
    data = request.get_json()
    class_subjects = data.get('class_subjects')
    day = data.get('day')

    if not all([class_subjects, day]):
        return jsonify({'message': 'Missing parameters.'}), 400

    if not 1<= day <= 7:
        return jsonify({'message': 'day must be between 1 and 7'}), 400

    schedule = []
    for class_subject in class_subjects:
        query = """
        SELECT 
            t.timetable_id,
            s.subject_code,
            s.subject_name,
            t.start_time,
            t.end_time,
            t.room_number,
            c.batch_id
        FROM timetable t
        JOIN class c ON c.class_id = t.class_id
        JOIN subject s ON s.subject_code = t.subject_code
        WHERE t.class_id = %s AND t.day = %s AND t.subject_code = %s
        """
        results = current_app.config['DATABASE'].execute_query(query, (class_subject['class_id'], day, class_subject['subject_code'],))

        if results:
            schedule.append({
                'timetable_id': results[0][0],
                'subject_code': results[0][1],
                'subject_name': results[0][2],
                'start_time': str(results[0][3]),
                'end_time': str(results[0][4]),
                'room_number': results[0][5],
                'batch_id': results[0][6]
            })

    return jsonify(schedule), 200

@teacher.route('/attendance_status', methods=['POST'])
@jwt_required()
def get_attendance_status():
    data = request.get_json()
    timetable_ids = data.get('timetable_ids')
    date = data.get('date')

    if not all([timetable_ids, date]):
        return jsonify({'message': 'Missing parameters.'}), 400
    
    try:
        date = convert_flutter_to_mysql_time(date)
    except ValueError:
        return jsonify({"message": "Invalid date."}), 400
    
    attendance_data=[]
    
    for timetable_id in timetable_ids:
        attendance_query = """
            SELECT 
                marked_at,
                room_number
            FROM attendance
            WHERE timetable_id = %s AND date = %s
            LIMIT 1
        """
        attendance_result = current_app.config['DATABASE'].execute_query(attendance_query, (timetable_id, date.date()))
        
        if not attendance_result:
            attendance_data.append({
                'timetable_id': timetable_id,
                'date': date,
                'status': 0,
                'marked_at': None,
                'room_number': None
            })
            continue
    
        marked_at = str(attendance_result[0][0])
        room_number = attendance_result[0][1]
        
        # Format the response
        attendance_data.append({
            'timetable_id': timetable_id,
            'date': date,
            'status': 1,
            'marked_at': marked_at,
            'room_number': room_number
        })

    return jsonify(attendance_data), 200

@teacher.route('/attendance', methods=['GET'])
@jwt_required()
def teacher_get_attendance():
    timetable_id = request.args.get('timetable_id')
    date = request.args.get('date')

    query = "SELECT * FROM attendance WHERE date = %s AND timetable_id = %s"
    params = (date, timetable_id)

    result = current_app.config['DATABASE'].execute_query(query, params)
    attendance_list = []

    if result:
        for row in result:
            attendance_info = {
                'student_id': row[0],
                'timetable_id': row[1],
                'status': row[2],
                'marked_at': row[3],
                'room_number': row[4],
                'date': row[5]
            }
            attendance_list.append(attendance_info)

    return jsonify(attendance_list), 200

@teacher.route('/update_attendance', methods=['POST'])
@jwt_required()
def update_attendance():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No attendance records provided"}), 400

    for record in data:
        student_id = record['student_id']
        timetable_id = record['timetable_id']
        status = record['status']
        date = record['date']
        room_number = record['room_number']

        query = """
            INSERT INTO attendance (student_id, timetable_id, status, date, room_number)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status), marked_at = CURRENT_TIMESTAMP
        """
        params = [student_id, timetable_id, status, date, room_number]
        current_app.config['DATABASE'].execute_query(query, params)

    return jsonify({"message": "Attendance updated successfully"}), 200

@teacher.route('/session_stats', methods=['GET'])
@jwt_required()
def get_session_stats():
    teacher_id = get_jwt_identity()
    class_ids = request.args.get('class_ids')

    timetable_query = """
        SELECT 
            timetable_id, subject_code, class_id, start_time, end_time, room_number, day
        FROM timetable
        WHERE teacher_id = %s
    """
    timetable_results = current_app.config['DATABASE'].execute_query(timetable_query, (teacher_id,))

    if not timetable_results:
        return jsonify({'message': 'No timetable entries found for the teacher.'}), 404

    # Step 2: Filter by class_ids if provided
    timetable_data = []
    for row in timetable_results:
        timetable_id, subject_code, class_id, start_time, end_time, room_number, day = row
        if class_ids and class_id not in class_ids:
            continue

        # Step 3: Check if any attendance records exist for the timetable_id
        attendance_check_query = """
            SELECT COUNT(*)
            FROM attendance
            WHERE timetable_id = %s
        """
        attendance_count = current_app.config['DATABASE'].execute_query(attendance_check_query, (timetable_id,))[0][0]

        # Step 4: Prepare the response with attendance status
        timetable_data.append({
            'timetable_id': timetable_id,
            'subject_code': subject_code,
            'class_id': class_id,
            'start_time': str(start_time),
            'end_time': str(end_time),
            'room_number': room_number,
            'day': day,
            'attendance_taken': True if attendance_count > 0 else False,
            'attendance_count': attendance_count
        })

    return jsonify(timetable_data), 200


@teacher.route('/mark_attendance', methods=['POST'])
@jwt_required()
def mark_attendance():
    data = request.get_json()
    if not data or 'photo' not in data:
        return jsonify({'error': 'No photo data provided'}), 400

    try:
        # Decode the base64 string and save the image
        photo_base64 = data['photo']
        filename = data.get('filename', 'photo.jpg')  # Use provided filename or default
        file_path = os.path.join("photos", filename)

        os.makedirs("photos", exist_ok=True)  # Ensure directory exists
        with open(file_path, "wb") as photo_file:
            photo_file.write(base64.b64decode(photo_base64))
    except Exception as e:
        return jsonify({'error': f'Failed to decode image: {str(e)}'}), 500

    # Placeholder for additional processing (e.g., image recognition)
    return jsonify({'message': 'Attendance marked successfully', 'file_path': file_path}), 200