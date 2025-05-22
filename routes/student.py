import io
import os
from PIL import Image
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
import numpy as np
from utils.functions import convert_flutter_to_mysql_time
from utils.face_recognition import detect_face, get_embedding

EMBEDDING_FOLDER = 'face_embeddings'

student = Blueprint('student', __name__)

@student.route('/classes', methods=['GET'])
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

@student.route('/schedule', methods=['POST'])
@jwt_required()
def get_schedule():
    data = request.get_json()
    class_id = data.get('class_id')
    day = data.get('day')

    if not all([class_id, day]):
        return jsonify({'message': 'Missing parameters.'}), 400

    schedule_query = """
    SELECT 
        ts.timetable_id,
        ts.subject_code,
        s.subject_name,
        ts.start_time,
        ts.end_time,
        ts.room_number,
        t.teacher_name,
        t.teacher_surname
    FROM timetable ts
    LEFT JOIN class_subjects cs ON ts.class_id = cs.class_id AND ts.subject_code = cs.subject_code
    LEFT JOIN teacher t ON cs.teacher_id = t.teacher_id
    LEFT JOIN subject s ON ts.subject_code = s.subject_code  -- Fetch subject name from DB
    WHERE ts.class_id = %s AND ts.day = %s
    ORDER BY ts.start_time
    """
    schedule_results = current_app.config['DATABASE'].execute_query(schedule_query, (class_id, day))

    if not schedule_results:
        return jsonify([]), 200

    subjects = [
        {
            'timetable_id': row[0],
            'subject_code': row[1],
            'subject_name': row[2],  # Now fetched from DB
            'start_time': str(row[3]),
            'end_time': str(row[4]),
            'room_number': row[5],
            'teacher_name': row[6],
            'teacher_surname': row[7],
            'day': day
        }
        for row in schedule_results
    ]

    return jsonify(subjects), 200


@student.route('/attendance', methods=['POST'])
@jwt_required()
def get_attendance():
    data = request.get_json()
    student_id = get_jwt_identity()['id']
    timetable_ids = data.get('timetable_ids')
    date = data.get('date')

    if not all([student_id, timetable_ids, date]):
        return jsonify({'message': 'Missing parameters.'}), 400
    
    try:
        date = convert_flutter_to_mysql_time(date)
    except ValueError:
        return jsonify({"message": "Invalid date."}), 400
    
    attendance_data=[]
    
    for timetable_id in timetable_ids:
        attendance_query = """
        SELECT 
            status,
            marked_at,
            room_number
        FROM attendance
        WHERE student_id = %s AND timetable_id = %s AND date = %s
        """
        attendance_result = current_app.config['DATABASE'].execute_query(attendance_query, (student_id, timetable_id, date.date()))
        
        if not attendance_result:
            attendance_data.append({
                'timetable_id': timetable_id,
                'date': date,
                'status': None,
                'marked_at': None,
                'room_number': None
            })
            continue
    
        status = attendance_result[0][0]
        marked_at = str(attendance_result[0][1])
        room_number = attendance_result[0][2]
        
        # Format the response
        attendance_data.append({
            'timetable_id': timetable_id,
            'date': date,
            'status': status,
            'marked_at': marked_at,
            'room_number': room_number
        })

    return jsonify(attendance_data), 200

@student.route('/subject_stats', methods=['GET'])
@jwt_required()
def get_subject_stats():
    class_id = request.args.get('class_id')
    student_id = get_jwt_identity()['id']

    query = """
        SELECT class_subjects.subject_code, s.subject_name
        FROM class_subjects
        JOIN subject s ON class_subjects.subject_code = s.subject_code  -- Fetch subject name from DB
        WHERE class_subjects.class_id = %s
        GROUP BY class_subjects.subject_code, s.subject_name
    """
    result = current_app.config['DATABASE'].execute_query(query, (class_id,))

    subject_stats = []
    
    if result:
        for row in result:
            subject_code = row[0]
            subject_name = row[1]

            # Query to get both attended and total classes
            attendance_query = """
                SELECT 
                COUNT(CASE WHEN attendance.status = 1 THEN 1 END) AS attended_classes,
                COUNT(*) AS total_classes
                FROM attendance
                JOIN timetable ON attendance.timetable_id = timetable.timetable_id
                WHERE attendance.student_id = %s
                AND timetable.subject_code = %s
            """
            attendance_result = current_app.config['DATABASE'].execute_query(attendance_query, (student_id, subject_code))

            attended_classes = attendance_result[0][0] if attendance_result else 0
            total_classes = attendance_result[0][1] if attendance_result else 0

            subject_stats.append({
                'subject_code': subject_code,
                'subject_name': subject_name,  # Now fetched from DB
                'attended': attended_classes,
                'total': total_classes
            })

    return jsonify(subject_stats), 200


@student.route('/attendance_stats', methods=['GET'])
@jwt_required()
def get_attendance_stats():
    subject_code = request.args.get('subject_code')
    student_id = get_jwt_identity()['id']

    query = """
        SELECT 
            attendance.timetable_id,
            attendance.status,
            attendance.date,
            timetable.start_time,
            timetable.end_time
        FROM attendance
        JOIN timetable ON attendance.timetable_id = timetable.timetable_id
        WHERE attendance.student_id = %s
        AND timetable.subject_code = %s
    """
    
    result = current_app.config['DATABASE'].execute_query(query, (student_id, subject_code))

    attendance_stats = []

    if result:
        for row in result:
            timetable_id = row[0]
            status = row[1]
            date = row[2]
            start_time = row[3]
            end_time = row[4]

            attendance_stats.append({
                'timetable_id': timetable_id,
                'status': status,
                'date': str(date),
                'start_time': str(start_time),
                'end_time': str(end_time)
            })
    
    return jsonify(attendance_stats), 200

@student.route('/update_facedata', methods=['POST'])
@jwt_required()
def upload_face():
    user_id = get_jwt_identity()['id']
    file = request.files.get('image')

    if not file:
        return jsonify({"success": False, "message": "No image uploaded"}), 400

    try:
        image_stream = io.BytesIO(file.read())
        pil_image = Image.open(image_stream).convert("RGB")
        img_np = np.array(pil_image)
    except Exception as e:
        return jsonify({"success": False, "message": f"Invalid image data: {e}"}), 400

    face_img = detect_face(img_np, max_det=1)
    if face_img is None:
        return jsonify({"success": False, "roll_number": user_id, "message": "Face not detected"}), 200

    embedding = get_embedding(face_img)
    if embedding is None:
        return jsonify({"success": False, "roll_number": user_id, "message": "Embedding failed"}), 200

    embedding_file = os.path.join(EMBEDDING_FOLDER, f"{user_id}.npy")
    np.save(embedding_file, embedding)

    return jsonify({"success": True, "roll_number": user_id}), 200