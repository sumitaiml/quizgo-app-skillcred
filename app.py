# app.py - IQBattle: AI-Powered Quiz Battleground
from flask import Flask, request, render_template, jsonify, send_file, session
from flask_cors import CORS
import os
import hashlib

import json
import re
import io
import requests
from datetime import datetime
from urllib.parse import urlparse, unquote
import PyPDF2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='.')
CORS(app)

# Configure battle uploads folder (temporary storage before extraction)
UPLOAD_FOLDER = 'battle_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-battleground-quizgo-2026')

# Supabase Auth configurations
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Import pg8000 for database connection
import pg8000

def get_db_connection():
    """Create a database connection to Supabase PostgreSQL using pg8000"""
    parsed = urlparse(DATABASE_URL)
    username = parsed.username
    password = unquote(parsed.password) if parsed.password else None
    hostname = parsed.hostname
    port = parsed.port or 5432
    database = parsed.path.lstrip('/')
    
    return pg8000.connect(
        user=username,
        password=password,
        host=hostname,
        port=port,
        database=database
    )

def init_db():
    """Initialize the schema in Supabase PostgreSQL"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                pdf_name VARCHAR(255) NOT NULL,
                difficulty VARCHAR(50) NOT NULL,
                question_types VARCHAR(50) NOT NULL,
                questions JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS pdf_hash VARCHAR(64);
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("[DB] Database initialized successfully.")
    except Exception as e:
        print(f"[DB] Failed to initialize database: {e}")

# Initialize database schema on startup
init_db()

def calculate_sha256(file_path):
    """Compute the SHA-256 hash of a file dynamically"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_current_user():

    return session.get('user')

def extract_generated_text(result):
    """Safely extract text from Gemini AI battle response"""
    try:
        candidates = result.get('candidates', [])
        if not candidates or not isinstance(candidates, list):
            raise ValueError('No AI battle candidates found')
        
        content = candidates[0].get('content')
        if isinstance(content, list) and len(content) > 0:
            content = content[0]
        
        parts = content.get('parts')
        if not parts or not isinstance(parts, list):
            raise ValueError('No battle intelligence parts found')
        
        text = parts[0].get('text')
        if not text:
            raise ValueError('No battle text generated')
        
        return text
    except Exception as e:
        print(f"[AI] Battle intelligence extraction failed: {e}")
        print(f"[AI] Full response: {result}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extract battle intelligence from PDF documents"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            # Extract intelligence from all pages
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
                
            return text.strip()
    except Exception as e:
        print(f"[PDF] PDF intelligence extraction failed: {e}")
        return None

def generate_battle_questions(pdf_text, num_questions=8, difficulty="Medium", question_types="mixed"):
    """Generate IQBattle questions using AI battle intelligence"""
    
    # Get AI battle credentials
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("[AI] No AI battle credentials found! Check your .env battle config")
        return None, "your app is down for this period"
        
    print(f"[AI] AI Battle Commander authenticated: {api_key[:10]}...")
    print(f"[AI] Battle mode: {question_types}")
    print(f"[AI] Difficulty protocol: {difficulty}")
    
    # Updated model to gemini-2.5-flash as verified working
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # Battle mode configurations
    battle_modes = {
        "mcq": {
            "name": "MCQ Assault Mode",
            "instruction": "Deploy ONLY multiple choice battle questions with exactly 4 tactical options (A, B, C, D).",
            "example": """
            {
                "question": "What is the primary objective in database normalization?",
                "type": "mcq",
                "options": ["A) Increase storage space", "B) Eliminate data redundancy", "C) Slow down queries", "D) Increase complexity"],
                "correct_answer": "B",
                "explanation": "Database normalization eliminates redundancy and ensures data integrity"
            }"""
        },
        "true_false": {
            "name": "Binary Strike Mode",
            "instruction": "Execute ONLY true/false binary battle decisions.",
            "example": """
            {
                "question": "Database locks are always necessary for maintaining consistency.",
                "type": "true_false",
                "options": ["True", "False"],
                "correct_answer": "False",
                "explanation": "While locks help, there are lock-free methods like optimistic concurrency control"
            }"""
        },
        "fill_blank": {
            "name": "Stealth Mission Mode",
            "instruction": "Launch ONLY fill-in-the-blank stealth operations using _______ for tactical blanks.",
            "example": """
            {
                "question": "The _______ protocol ensures that database transactions appear to execute in _______ order.",
                "type": "fill_blank",
                "options": [],
                "correct_answer": "two-phase locking; serial",
                "explanation": "Two-phase locking protocol ensures serializability by controlling transaction execution order"
            }"""
        },
        "essay": {
            "name": "Intelligence Report Mode",
            "instruction": "Generate ONLY comprehensive intelligence report questions requiring detailed analysis.",
            "example": """
            {
                "question": "Analyze the importance of ACID properties in database management systems and their real-world applications.",
                "type": "essay",
                "options": [],
                "correct_answer": "A complete analysis should cover: 1) Atomicity - all-or-nothing transactions 2) Consistency - data integrity rules 3) Isolation - concurrent transaction handling 4) Durability - permanent data storage 5) Real-world examples in banking, e-commerce, etc.",
                "explanation": "Students should demonstrate understanding of each ACID property and provide practical examples"
            }"""
        }
    }
    
    # Select battle configuration
    if question_types in battle_modes:
        mode_config = battle_modes[question_types]
        battle_instruction = mode_config["instruction"]
        battle_example = mode_config["example"]
        print(f"[AI] Deploying {mode_config['name']}")
    else:
        battle_instruction = "Deploy a STRATEGIC MIX of all battle question types: MCQ Assault, Binary Strike, Stealth Mission, and Intelligence Report."
        battle_example = "Mix of mcq, true_false, fill_blank, and essay questions"
        print(f"[AI] Deploying Mixed Battle Formation")
    
    # AI Battle Command Prompt
    battle_prompt = f"""
    IQBATTLE MISSION BRIEFING
    ========================
    
    Battle Intelligence Source:
    {pdf_text[:3500]}
    
    MISSION PARAMETERS:
    - Deploy exactly {num_questions} battle questions
    - Difficulty Protocol: {difficulty}
    - Battle Mode: {battle_instruction}
    
    TACTICAL REQUIREMENTS:
    - Questions must test intellectual combat skills, not just memory recall
    - Each question needs strategic explanation for battle debriefing
    - Ensure questions are battlefield-ready and unambiguous
    - Base all intelligence strictly on provided battle document
    
    BATTLE FORMATION (JSON ONLY):
    {{
        "questions": [
            {battle_example}
        ]
    }}
    
    DEPLOY BATTLE QUESTIONS NOW - JSON RESPONSE ONLY, NO ADDITIONAL COMMUNICATION
    """
    
    # Battle payload for AI Command Center
    payload = {
        "contents": [{
            "parts": [{
                "text": battle_prompt
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"[AI] AI Battle Commander generating {num_questions} {question_types} questions...")
        print("[AI] Engaging AI battle systems...")
        
        response = requests.post(url, json=payload, headers=headers)
        print(f"[AI] Battle Command Response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract battle intelligence
            generated_text = extract_generated_text(result)
            if not generated_text:
                print("[AI] AI Battle Commander failed to generate intelligence")
                return None, "your app is down for this period"
            
            print("[AI] Battle intelligence successfully extracted")
            
            # Clean battle response
            generated_text = generated_text.strip()
            if generated_text.startswith("```json"):
                generated_text = generated_text[7:]
            elif generated_text.startswith("```"):
                generated_text = generated_text[3:]
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3]
            
            generated_text = generated_text.strip()
            
            # Parse battle data
            try:
                battle_data = json.loads(generated_text)
                
                # Validate battle questions
                if 'questions' in battle_data:
                    question_types_found = [q.get('type', 'mcq') for q in battle_data['questions']]
                    print(f"[AI] Battle questions deployed: {question_types_found}")
                    
                    # Count battle formation
                    formation_count = {}
                    for qtype in question_types_found:
                        formation_count[qtype] = formation_count.get(qtype, 0) + 1
                    print(f"[AI] Battle formation: {formation_count}")
                
                return battle_data, None
            except json.JSONDecodeError as e:
                print(f"[AI] Battle data parsing failed: {e}")
                print(f"[AI] Raw battle response (first 500 chars): {generated_text[:500]}")
                return None, "your app is down for this period"
                
        else:
            print(f"[AI] AI Battle Command Error: {response.status_code}")
            print(f"[AI] Battle failure details: {response.text}")
            
            # Identify specific quota / rate limit issues
            error_msg = response.text
            try:
                resp_json = response.json()
                if 'error' in resp_json:
                    error_msg = resp_json['error'].get('message', response.text)
            except Exception:
                pass
                
            if response.status_code == 429 or "RESOURCE_EXHAUSTED" in error_msg or "QUOTA" in error_msg.upper() or "LIMIT" in error_msg.upper():
                return None, "the API limit is exceeded"
                
            return None, "your app is down for this period"
            
    except Exception as e:
        print(f"[AI] Battle system failure: {e}")
        return None, "your app is down for this period"

@app.route('/')
def battle_arena():
    """Main IQBattle Arena"""
    return render_template('index.html')

@app.route('/features')
def engine_features():
    """Engine Features Specification Page"""
    return render_template('features.html')

@app.route('/security')
def security_protocols():
    """Security and Privacy Page"""
    return render_template('security.html')


@app.route('/upload', methods=['POST'])
def deploy_battle():
    """Deploy PDF battle document and generate IQBattle"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
            
        print('[APP] === IQBATTLE DEPLOYMENT INITIATED ===')
        
        # Validate battle document upload
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No PDF battle document uploaded'}), 400
        
        battle_file = request.files['pdf_file']
        if battle_file.filename == '':
            return jsonify({'error': 'No battle document selected'}), 400
        
        # Extract battle parameters
        num_questions = int(request.form.get('num_questions', 8))
        difficulty = request.form.get('difficulty', 'Medium')
        question_types = request.form.get('question_types', 'mcq')
        
        # Validate battle configuration
        if num_questions < 4:
            return jsonify({'error': 'Minimum 4 questions required for IQBattle deployment'}), 400
        
        # Secure battle document temporarily
        battle_filename = f"battle_document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        battle_path = os.path.join(app.config['UPLOAD_FOLDER'], battle_filename)
        battle_file.save(battle_path)
        
        # Compute SHA-256 hash of the uploaded PDF
        pdf_hash = calculate_sha256(battle_path)
        
        # Check database for existing quiz from the same PDF with matching parameters
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, questions FROM quizzes WHERE pdf_hash = %s AND difficulty = %s AND question_types = %s ORDER BY created_at DESC;",
            (pdf_hash, difficulty, question_types)
        )
        existing_rows = cur.fetchall()
        
        existing_quiz = None
        for q_id, q_data in existing_rows:
            if isinstance(q_data, str):
                try:
                    q_json = json.loads(q_data)
                except Exception:
                    q_json = None
            else:
                q_json = q_data
            
            if q_json and 'questions' in q_json and len(q_json['questions']) == num_questions:
                existing_quiz = q_json
                break
                
        if existing_quiz:
            print(f"[DB] Cache hit! Returning cached quiz for hash: {pdf_hash}")
            if os.path.exists(battle_path):
                os.remove(battle_path)
                
            # Create a clone in the database for the current user's session history
            cur.execute(
                "INSERT INTO quizzes (user_email, pdf_name, difficulty, question_types, questions, pdf_hash) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;",
                (user['email'], battle_file.filename, difficulty, question_types, json.dumps(existing_quiz), pdf_hash)
            )
            quiz_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            
            # Count question types for statistics
            question_formation = {}
            for q in existing_quiz['questions']:
                qtype = q.get('type', 'mcq')
                question_formation[qtype] = question_formation.get(qtype, 0) + 1
                
            return jsonify({
                'success': True,
                'battle_status': 'VICTORY_ACHIEVED',
                'quiz_data': existing_quiz,
                'question_types': question_formation,
                'result_file': f"iqbattle_result_{quiz_id}.json",
                'battle_stats': {
                    'total_questions': sum(question_formation.values()),
                    'battle_mode': question_types,
                    'difficulty_protocol': difficulty,
                    'deployment_time': datetime.now().strftime('%H:%M:%S')
                },
                'message': f'Cached quiz retrieved (SHA-256 match): {sum(question_formation.values())} questions loaded!'
            })
            
        cur.close()
        conn.close()
        
        # Extract battle intelligence (Cache Miss)
        battle_intelligence = extract_text_from_pdf(battle_path)
        if not battle_intelligence or len(battle_intelligence.strip()) < 30:
            if os.path.exists(battle_path):
                os.remove(battle_path)
            return jsonify({'error': 'the PDF also has the error. Failed to extract text from PDF.'}), 400
        
        # Generate IQBattle questions
        battle_questions, error_msg = generate_battle_questions(battle_intelligence, num_questions, difficulty, question_types)
        if not battle_questions:
            if os.path.exists(battle_path):
                os.remove(battle_path)
            
            # If the PDF does not contain "error", warn that the PDF also has the error
            if "error" not in battle_intelligence.lower():
                return jsonify({'error': f"{error_msg}. the PDF also has the error."}), 500
            return jsonify({'error': error_msg}), 500
        
        # Clean up temporary PDF upload
        if os.path.exists(battle_path):
            os.remove(battle_path)
            
        # Store quiz in Supabase Postgres Database with pdf_hash
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO quizzes (user_email, pdf_name, difficulty, question_types, questions, pdf_hash) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;",
            (user['email'], battle_file.filename, difficulty, question_types, json.dumps(battle_questions), pdf_hash)
        )
        quiz_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Count question types for statistics
        question_formation = {}

        if 'questions' in battle_questions:
            for q in battle_questions['questions']:
                qtype = q.get('type', 'mcq')
                question_formation[qtype] = question_formation.get(qtype, 0) + 1
        
        return jsonify({
            'success': True,
            'battle_status': 'VICTORY_ACHIEVED',
            'quiz_data': battle_questions,
            'question_types': question_formation,
            'result_file': f"iqbattle_result_{quiz_id}.json",
            'battle_stats': {
                'total_questions': sum(question_formation.values()),
                'battle_mode': question_types,
                'difficulty_protocol': difficulty,
                'deployment_time': datetime.now().strftime('%H:%M:%S')
            },
            'message': f'IQBattle deployed: {sum(question_formation.values())} questions ready for intellectual combat!'
        })
        
    except Exception as e:
        print(f"[APP] IQBATTLE SYSTEM FAILURE: {e}")
        return jsonify({
            'error': f'Battle system failure: {str(e)}',
            'battle_status': 'MISSION_FAILED'
        }), 500

@app.route('/auth/signup', methods=['POST'])
def auth_signup():
    try:
        data = request.get_json(force=True)
        email = (data.get('email') or '').strip().lower()
        password = (data.get('password') or '').strip()
        name = (data.get('name') or '').strip()

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Sign up using Supabase Admin Auth API to bypass email validation rate limits
        signup_url = f"{SUPABASE_URL}/auth/v1/admin/users"
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "name": name or email.split('@')[0]
            }
        }
        
        response = requests.post(signup_url, headers=headers, json=payload)
        res_data = response.json()
        
        if response.status_code != 200 and response.status_code != 201:
            err_msg = res_data.get('msg') or res_data.get('error_description') or res_data.get('message') or 'Signup failed'
            return jsonify({'error': err_msg}), response.status_code

        # Authenticate the user immediately to get the access token
        login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        login_headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        login_payload = {
            "email": email,
            "password": password
        }
        
        login_response = requests.post(login_url, headers=login_headers, json=login_payload)
        login_res_data = login_response.json()
        
        if login_response.status_code != 200:
            err_msg = login_res_data.get('error_description') or login_res_data.get('message') or 'Failed to log in after signup'
            return jsonify({'error': err_msg}), login_response.status_code

        access_token = login_res_data.get('access_token')
        user_info = login_res_data.get('user', {})
        user_metadata = user_info.get('user_metadata', {})
        
        session['user'] = {
            'email': email,
            'name': user_metadata.get('name') or name or email.split('@')[0],
            'access_token': access_token
        }
        
        return jsonify({'success': True, 'user': session['user']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/login', methods=['POST'])
def auth_login():
    try:
        data = request.get_json(force=True)
        email = (data.get('email') or '').strip().lower()
        password = (data.get('password') or '').strip()

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Login using Supabase Auth endpoint
        login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "password": password
        }
        
        response = requests.post(login_url, headers=headers, json=payload)
        res_data = response.json()
        
        if response.status_code != 200:
            err_msg = res_data.get('error_description') or res_data.get('message') or 'Invalid email or password'
            return jsonify({'error': err_msg}), response.status_code

        user_info = res_data.get('user', {})
        user_metadata = user_info.get('user_metadata', {})
        
        session['user'] = {
            'email': user_info.get('email') or email,
            'name': user_metadata.get('name') or email.split('@')[0],
            'access_token': res_data.get('access_token')
        }
        
        return jsonify({'success': True, 'user': session['user']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/auth/me', methods=['GET'])
def auth_me():
    user = get_current_user()
    if not user:
        return jsonify({'authenticated': False}), 200
    return jsonify({'authenticated': True, 'user': user}), 200

@app.route('/download/<filename>')
def download_battle_results(filename):
    """Download IQBattle results archive from database"""
    try:
        # Extract ID from filename (e.g. iqbattle_result_12.json)
        match = re.search(r'\d+', filename)
        if not match:
            return jsonify({'error': 'Invalid battle archive ID'}), 400
        quiz_id = int(match.group())
        
        # Connect to DB and fetch the quiz details
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT pdf_name, difficulty, question_types, questions, created_at FROM quizzes WHERE id = %s;", (quiz_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Quiz not found'}), 404
            
        pdf_name, difficulty, question_types, questions_data, created_at = row
        
        # Load questions data
        if isinstance(questions_data, str):
            questions = json.loads(questions_data)
        else:
            questions = questions_data
            
        # Reconstruct file data
        archive_data = {
            'battle_document': pdf_name,
            'deployment_timestamp': created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at),
            'battle_parameters': {
                'num_questions': len(questions.get('questions', [])),
                'difficulty_protocol': difficulty,
                'battle_mode': question_types,
                'question_formation': {}
            },
            'battle_system': 'IQBattle_v3.0_Supabase_State_Less',
            'battle_commander': 'Google_AI_Gemini_2.5_Flash',
            'battle_data': questions
        }
        
        # Count formations
        for q in questions.get('questions', []):
            qtype = q.get('type', 'mcq')
            archive_data['battle_parameters']['question_formation'][qtype] = archive_data['battle_parameters']['question_formation'].get(qtype, 0) + 1
            
        # Create output buffer
        mem_file = io.BytesIO()
        mem_file.write(json.dumps(archive_data, indent=2).encode('utf-8'))
        mem_file.seek(0)
        
        return send_file(
            mem_file,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({
            'error': f'Battle archive retrieval failed: {str(e)}',
            'battle_status': 'ARCHIVE_NOT_FOUND'
        }), 404

@app.route('/api/battle-stats')
def get_battle_statistics():
    """Get IQBattle deployment statistics from Supabase Database"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
            
        battle_stats = {
            'total_battles': 0,
            'battle_formations': {},
            'difficulty_protocols': {},
            'recent_battles': [],
            'battle_system_status': 'OPERATIONAL'
        }
        
        # Query DB for stats
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get total battles
        cur.execute("SELECT COUNT(*) FROM quizzes;")
        battle_stats['total_battles'] = cur.fetchone()[0]
        
        # Get difficulty counts
        cur.execute("SELECT difficulty, COUNT(*) FROM quizzes GROUP BY difficulty;")
        for diff, count in cur.fetchall():
            battle_stats['difficulty_protocols'][diff] = count
            
        # Get question type formations
        # Let's pull the last 100 quizzes and aggregate their questions in Python
        cur.execute("SELECT questions FROM quizzes ORDER BY created_at DESC LIMIT 100;")
        for (q_data,) in cur.fetchall():
            if isinstance(q_data, str):
                q_json = json.loads(q_data)
            else:
                q_json = q_data
                
            for q in q_json.get('questions', []):
                qtype = q.get('type', 'mcq')
                battle_stats['battle_formations'][qtype] = battle_stats['battle_formations'].get(qtype, 0) + 1
                
        # Get user's recent battles
        cur.execute("SELECT id, pdf_name, difficulty, question_types, questions, created_at FROM quizzes WHERE user_email = %s ORDER BY created_at DESC LIMIT 10;", (user['email'],))
        for quiz_id, pdf_name, difficulty, qtypes, q_data, created_at in cur.fetchall():
            if isinstance(q_data, str):
                q_json = json.loads(q_data)
            else:
                q_json = q_data
                
            num_questions = len(q_json.get('questions', []))
            
            battle_stats['recent_battles'].append({
                'battle_id': f"iqbattle_result_{quiz_id}.json",
                'deployment_time': created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at),
                'questions_deployed': num_questions,
                'battle_mode': qtypes,
                'difficulty': difficulty
            })
            
        cur.close()
        conn.close()
        
        return jsonify(battle_stats)
    except Exception as e:
        return jsonify({
            'error': f'Battle statistics retrieval failed: {str(e)}',
            'battle_system_status': 'STATISTICS_ERROR'
        }), 500

@app.route('/api/battle-health')
def battle_system_health():
    """IQBattle system health check"""
    try:
        health_status = {
            'battle_system': 'IQBattle_v3.0',
            'ai_commander': 'Google_AI_Gemini_2.5_Flash',
            'system_status': 'OPERATIONAL',
            'ai_credentials_loaded': bool(os.getenv("GOOGLE_API_KEY")),
            'supabase_url_loaded': bool(os.getenv("SUPABASE_URL")),
            'database_connected': False,
            'max_arsenal_size': '16MB',
            'supported_battle_modes': ['mcq', 'true_false', 'fill_blank', 'essay'],
            'last_system_check': datetime.now().isoformat()
        }
        
        # Check DB connectivity
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            cur.fetchone()
            cur.close()
            conn.close()
            health_status['database_connected'] = True
        except Exception as db_err:
            print(f"Database health check error: {db_err}")
            
        # Overall status check
        if all([
            health_status['ai_credentials_loaded'],
            health_status['supabase_url_loaded'],
            health_status['database_connected']
        ]):
            health_status['overall_status'] = 'READY_FOR_BATTLE'
        else:
            health_status['overall_status'] = 'SYSTEM_COMPROMISED'
        
        return jsonify(health_status)
    except Exception as e:
        return jsonify({
            'battle_system': 'IQBattle_v3.0',
            'system_status': 'CRITICAL_FAILURE',
            'error': str(e),
            'last_system_check': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("=" * 50)
    print("[APP] QUIZGO PROFESSIONAL SYSTEM v3.0")
    print("=" * 50)
    print("[APP] AI-Powered Quiz Generation Starting...")
    print("[APP] AI Engine: Google AI Gemini 2.5 Flash")
    print("[APP] Database: Supabase PostgreSQL (State-Less Mode)")
    print("=" * 50)
    
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
