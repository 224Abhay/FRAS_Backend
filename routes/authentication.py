from flask import Blueprint, request, jsonify, current_app
import random
import base64
from email.mime.text import MIMEText
# from googleapiclient.errors import HttpError
# import os
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token

def get_user_details(email_id, role):
    if role == "student":
        query = """
                SELECT 
                    s.student_id,
                    s.student_name,
                    s.student_surname,
                    s.student_email,
                    s.batch_id,
                    b.batch_of,
                    b.batch,
                    b.branch_id,
                    br.branch_name,
                    br.course_duration
                FROM 
                    student AS s
                JOIN 
                    batch AS b ON s.batch_id = b.batch_id
                JOIN
                    branch AS br ON b.branch_id = br.branch_id
                WHERE 
                    s.student_email = %s
                """
        db_data = current_app.config['DATABASE'].execute_query(query, (email_id,))

        final_data = {
            'student_id' : db_data[0][0],
            'student_name' : db_data[0][1],
            'student_surname' : db_data[0][2],
            'student_email' : db_data[0][3],
            'batch_id' : db_data[0][4],
            'batch_of' : db_data[0][5],
            'batch' : db_data[0][6],
            'branch_id' : db_data[0][7],
            'branch_name' : db_data[0][8],
            'course_duration' : db_data[0][9]
        }

    elif role == "teacher":
        query = "SELECT * FROM teacher WHERE teacher_email = %s"
        db_data = current_app.config['DATABASE'].execute_query(query,(email_id,))

        final_data = {
            'teacher_id' : db_data[0][0],
            'teacher_name' : db_data[0][1],
            'teacher_surname' : db_data[0][2],
            'teacher_email' : db_data[0][3],
        }

    elif role == "admin":
        query = "SELECT * FROM admin WHERE admin_email = %s"
        db_data = current_app.config['DATABASE'].execute_query(query,(email_id,))

        final_data = {
            'admin_id' : db_data[0][0],
            'admin_name' : db_data[0][1],
            'admin_surname' : db_data[0][2],
            'admin_email' : db_data[0][3]
            
        }
    return final_data

authentication = Blueprint('authentication', __name__)

verification_codes = {}
@authentication.route('/verification_code', methods=['POST'])
def send_verification_code():
    def send_code(recipient_email, verification_code):
        SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
        
        def create_message(sender, to, subject, message_text):
            message = MIMEText(message_text)
            message['to'] = to
            message['from'] = sender
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            return {'raw': raw}
        
        def send_message(service, user_id, message):
            try:
                message = service.users().messages().send(userId=user_id, body=message).execute()
                return message
            except HttpError as error:
                print(f'An error occurred: {error}')
                print(f'Details: {error.content}')
                return None

        sender_email = "identify.fras@gmail.com"
        
        subject = "Navrachana University Verification Code for FRAS"
        message_text = f"Your verification code is: {verification_code}"
        
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        try:
            service = build("gmail", "v1", credentials=creds)

            message = create_message(sender_email, recipient_email, subject, message_text)

            send_message(service, "me", message)

            return True

        except HttpError as error:
            print(f"An error occurred: {error}")
    
    request_data = request.get_json()
    email_id = request_data.get('email_id')
    
    query = "SELECT password FROM credential WHERE email_id = %s"
    db_data = current_app.config['DATABASE'].execute_query(query, (email_id,))

    if db_data:
        if db_data[0][0] == "P@ssw0rd":
            code = str(random.randint(1000,9999))
            print(code)
            
            verification_codes[email_id] = code

            if True:
                return jsonify({"message": "Verification code sent to your email."}), 200
            else:
                return jsonify({"message": "Failed to send verification email."}), 500
            
        return jsonify({"message": "User already exists. Please proceed to login."}), 400

    return jsonify({"message": "Email does not exist in our records. Please contact admin for assistance."}), 404

@authentication.route('/confirm_code', methods=['POST'])
def confirm_code():
    request_data = request.get_json()
    email_id = request_data.get('email_id')
    password= request_data.get('password')
    confirmation_code = request_data.get('confirmation_code')

    if email_id in verification_codes:
        if verification_codes[email_id] == confirmation_code:
            del verification_codes[email_id]

            query = "UPDATE credential SET password = %s WHERE email_id = %s"
            current_app.config['DATABASE'].execute_query(query, (current_app.config['BCRYPT'].generate_password_hash(password).decode('utf-8'), email_id))

            query = "SELECT role FROM credential WHERE email_id = %s"
            role = current_app.config['DATABASE'].execute_query(query, (email_id,))[0][0]

            user_details = get_user_details(email_id, role)

            access_token = create_access_token(identity={'id': next(iter(user_details.values()))})
            refresh_token = create_refresh_token(identity={'id': next(iter(user_details.values()))})

            return jsonify({
                'message': 'Registration Successful.',
                'role': role,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_details': user_details
            }), 200
        else:
            return jsonify({"message": "Invalid verification code. Please try again."}), 400
    else:
        return jsonify({"message": "Verification code not found. Please register again."}), 404

@authentication.route('/login', methods=['POST'])
def login():
    request_data = request.get_json()
    email_id = request_data.get('email_id')
    password = request_data.get('password')

    query = "SELECT password, role FROM credential WHERE email_id = %s"
    db_data = current_app.config['DATABASE'].execute_query(query, (email_id,))
    
    if db_data:
        if db_data[0][0] != "P@ssw0rd":
            role = db_data[0][1]
            if current_app.config['BCRYPT'].check_password_hash(db_data[0][0], password):
                
                user_details = get_user_details(email_id, role)

                access_token = create_access_token(identity={'id': next(iter(user_details.values()))})
                refresh_token = create_refresh_token(identity={'id': next(iter(user_details.values()))})

                return jsonify({
                    'message': 'Login Successful.',
                    'role': role,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user_details': user_details
                }), 200
            else:
                return jsonify({'message': 'Invalid credential. Check your Password.'}), 401
        else:
            return jsonify({'message': 'Register First'}), 401

    return jsonify({'message': 'Email does not exist in our records. Please contact admin for assistance.'}), 404

@authentication.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)

    return jsonify({
        'access_token': new_access_token
    }), 200

@authentication.route('/validate', methods=['POST'])
@jwt_required()
def validate():
    current_user = get_jwt_identity()
    if current_user:
        return jsonify({'message': 'Verification Successful'}), 200
    else:
        return jsonify({'message': 'Unauthorized'}), 401