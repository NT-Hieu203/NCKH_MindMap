from flask import Flask, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import redis
import pickle
from owlready2 import *
from dotenv import load_dotenv
from openai import OpenAI
from werkzeug.utils import secure_filename
import os
import json
import uuid
import time
from sentence_transformers import SentenceTransformer
from collections import defaultdict

# Import các module xử lý chính (giả định đã được đơn giản hóa bên trong)
from MainProcessor import process_PDF_file, create_ontology
from LLMquery import *

# Giả định YOLOv10 và easyocr không yêu cầu cấu hình đặc biệt cho chế độ tuần tự
from doclayout_yolo import YOLOv10
import easyocr

# --- Cấu hình Flask App ---
app = Flask(__name__)

# QUAN TRỌNG: Phải set SECRET_KEY trước khi sử dụng session
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev_secret_key_for_local_project_12345')

# --- Cấu hình CORS với credentials ---
CORS(app,
     supports_credentials=True,
     origins=["http://localhost:3001", "http://127.0.0.1:3001"],  # Đảm bảo đúng cổng và địa chỉ frontend của bạn
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
     )

# --- Cấu hình thư mục lưu trữ file ---
UPLOAD_FOLDER = 'pdf_upload'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Thư mục để lưu trữ các ontology được tạo
GENERATED_ONTOLOGIES_FOLDER = 'generated_ontologies'
if not os.path.exists(GENERATED_ONTOLOGIES_FOLDER):
    os.makedirs(GENERATED_ONTOLOGIES_FOLDER)

# --- Load biến môi trường và Khởi tạo OpenAI Client ---
load_dotenv(dotenv_path="secrect.env")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Khởi tạo các model ---
model_detect_layout = YOLOv10("model/model_detect_layout/doclayout_yolo_docstructbench_imgsz1024.pt")
reader = easyocr.Reader(['vi', 'en'], gpu=False)

# --- Load Ontology mặc định (nếu có) ---
ONTO_AVAILABLE_PATH = "static/MINDMAP.owl"
ontology_available = None
current_ontology = None
relation = None
is_loaded = False
type_ontology = None


# Sử dụng 'eventlet' cho các tác vụ bất đồng bộ
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- CÁC TRÌNH XỬ LÝ SỰ KIỆN SOCKET.IO ---
@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

@socketio.on('join_room')
def on_join(data):
    """Client tham gia một 'phòng' dựa trên session_id của họ"""
    session_id = data['session_id']
    join_room(session_id)
    print(f"Client {request.sid} đã tham gia phòng {session_id}")
    # Khởi tạo dữ liệu nếu cần
    if session_id not in chat_histories:
        chat_histories[session_id] = []

def load_ontologies(type, onto_path = None):
    if type == "Available":
        try:
            if os.path.exists(ONTO_AVAILABLE_PATH):
                ontology_available = get_ontology(f"file://{os.path.abspath(ONTO_AVAILABLE_PATH)}").load()
                print(f"Ontology mặc định '{ONTO_AVAILABLE_PATH}' đã được tải.")
                relation = find_relation(ontology_available)
                return ontology_available, relation
            else:
                print(f"Warning: File ontology mặc định '{ONTO_AVAILABLE_PATH}' không tồn tại. Bỏ qua việc tải.")
                return None, None
        except Exception as e:
            print(f"Không thể tải ontology mặc định '{ONTO_AVAILABLE_PATH}': {e}")
    else:
        try:
            if os.path.exists(onto_path):
                ontology_available = get_ontology(f"file://{os.path.abspath(onto_path)}").load()
                print(f"Ontology mới '{onto_path}' đã được tải.")
                relation = find_relation(ontology_available)
                return ontology_available, relation
            else:
                print(f"Warning: File ontology mới '{onto_path}' không tồn tại. Bỏ qua việc tải.")
                return None, None
        except Exception as e:
            print(f"Không thể tải ontology mới '{onto_path}': {e}")
# --- Model Embedding ---
# model_embedding_name = "model/model_embedding" #lưu model embedding nếu muốn tải về sử dụng local
model_embedding_name = 'paraphrase-multilingual-MiniLM-L12-v2'
model_embedding = SentenceTransformer(model_embedding_name)

# --- Lịch sử Chat trong memory ---
chat_histories = {}

# Redis client để quản lý trạng thái ontology cho từng session
try:
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
    # Test connection
    redis_client.ping()
    print("Kết nối Redis thành công")
except Exception as e:
    print(f"Không thể kết nối Redis: {e}")
    redis_client = None


# --- Session Management Helper Functions ---
def create_new_session():
    """Tạo session ID mới"""
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    session.permanent = True
    print(f'Tạo session_id mới: {session_id}')
    return session_id


def get_current_session_id():
    """Lấy session ID hiện tại, không tạo mới"""
    return session.get('session_id')


def initialize_user_data(session_id):
    """Khởi tạo dữ liệu cho user mới"""
    if session_id not in chat_histories:
        chat_histories[session_id] = []
        print(f'Khởi tạo chat history cho session: {session_id}')


def validate_session_for_new_ontology(session_id):
    """Kiểm tra session có ontology mới hợp lệ không"""
    if not session_id:
        return False, "Không có session hợp lệ"

    ontology_info = get_ontology_state(session_id)
    if not ontology_info:
        return False, "Session chưa có ontology nào được tạo"

    if ontology_info.get('status') != 'completed':
        return False, "Ontology chưa được xây dựng xong"

    ontology_path = ontology_info.get('ontology_path')
    if not ontology_path or not os.path.exists(ontology_path):
        return False, "File ontology không tồn tại"

    return True, "Session hợp lệ"


# --- Hàm kiểm tra loại file ---
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Hàm trợ giúp để tương tác với Redis cho trạng thái ontology
def get_ontology_state(session_id):
    if not redis_client:
        return None
    try:
        key = f"ontology_state:{session_id}"
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"Lỗi đọc ontology state: {e}")
        return None


def set_ontology_state(session_id, state_dict):
    if not redis_client:
        print("Redis không khả dụng, không thể lưu ontology state")
        return
    try:
        key = f"ontology_state:{session_id}"
        redis_client.set(key, json.dumps(state_dict))
        redis_client.expire(key, 3600 * 24)  # Hết hạn sau 24 giờ
        print(f"Đã lưu ontology state cho session: {session_id}")
    except Exception as e:
        print(f"Lỗi lưu ontology state: {e}")


def cleanup_session_data(session_id):
    """Dọn dẹp dữ liệu của session cũ"""
    # Xóa chat history
    chat_histories.pop(session_id, None)

    # Xóa ontology state từ Redis
    if redis_client:
        try:
            redis_client.delete(f"ontology_state:{session_id}")
        except Exception as e:
            print(f"Lỗi xóa ontology state: {e}")

    print(f"Đã dọn dẹp dữ liệu cho session: {session_id}")


# --- Routes API ---

@app.route("/api/get-session", methods=["GET"])
def get_session():
    """Endpoint để lấy session hiện tại (không tạo mới)"""
    session_id = get_current_session_id()

    if session_id:
        initialize_user_data(session_id)
        return jsonify({
            "session_id": session_id,
            "message": "Session hiện tại"
        })
    else:
        return jsonify({
            "session_id": None,
            "message": "Chưa có session. Vui lòng upload PDF hoặc chat với ontology có sẵn để tạo session mới."
        })

@app.route("/api/upload-pdf", methods=["POST"])
def upload_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "Không có tệp PDF"}), 400

    pdf_file = request.files['pdf_file']
    session_id = request.form.get('session_id') # Client phải gửi session_id kèm theo

    if not session_id:
        return jsonify({"error": "Thiếu session_id"}), 400
    
    if pdf_file and allowed_file(pdf_file.filename):
        filename = secure_filename(pdf_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        pdf_file.save(file_path)
        
        # Bắt đầu tác vụ xử lý trong background để không block request
        socketio.start_background_task(
            target=process_and_build_ontology,
            session_id=session_id,
            file_path=file_path
        )
        
        # Trả về ngay lập tức cho client biết là đã nhận file
        return jsonify({
            "message": "✅ Đã nhận tệp và đang trong quá trình phân tích, thời gian phân tích có thể mất vài phút.",
            "session_id": session_id
        }), 202 # 202 Accepted
    
    return jsonify({"error": "Tệp không hợp lệ"}), 400

def process_and_build_ontology(session_id, file_path):
    """
    Hàm này chạy ở background, xử lý PDF và gửi cập nhật tiến trình qua WebSocket.
    """
    with app.app_context(): # Cần app_context để emit từ background task
        try:
            # Gửi cập nhật tiến trình
            socketio.emit('ontology_progress', {'status': 'Đang xử lý file PDF...'}, room=session_id)
            clustering_tree = process_PDF_file(client, model_embedding, model_detect_layout, reader, file_path)
            
            socketio.emit('ontology_progress', {'status': 'Đang xây dựng ontology...'}, room=session_id)
            ontology_filename = f"{session_id}_ontology.owl"
            ontology_iri = f"http://www.semanticweb.org/{session_id}_MINDMAP"
            ontology_save_path = os.path.join(GENERATED_ONTOLOGIES_FOLDER, ontology_filename)
            create_ontology(model_embedding, clustering_tree, ontology_save_path, ontology_iri)
            
            # Cập nhật trạng thái hoàn thành trong Redis
            set_ontology_state(session_id, {
                'status': 'completed',
                'timestamp': time.time(),
                'ontology_path': ontology_save_path,
                'created_from': 'pdf_upload'
            })
            
            # Gửi thông báo hoàn thành
            socketio.emit('ontology_complete', {
                'status': 'Hoàn thành!',
                'message': 'Ontology đã được xây dựng thành công.',
                'initial_data': clustering_tree,
                'session_id': session_id
            }, room=session_id)
            
        except Exception as e:
            print(f"Lỗi background task: {e}")
            socketio.emit('ontology_error', {'error': f'Lỗi xử lý file: {str(e)}'}, room=session_id)
        finally:
            # Dọn dẹp file PDF tạm
            if os.path.exists(file_path):
                os.remove(file_path)


@app.route("/api/get_available_mindmap", methods=["GET"])
def get_available_mindmap():
    """Endpoint để lấy thông tin về ontology mặc định"""
    
    filename = 'static/clustering_tree.pkl'
    # Corrected line: Directly use the absolute path
    file_path = os.path.abspath(filename)
    
    clustering_tree = None # Initialize to None in case of error
    try:
        with open(file_path, 'rb') as file:
            clustering_tree = pickle.load(file)
    except FileNotFoundError:
        print(f"\nLỗi: Không tìm thấy tệp {file_path}. Đảm bảo tệp tồn tại.")
        return jsonify({
            "message": f"Lỗi: Không tìm thấy tệp {file_path}.",
            "initial_data": None
        }), 404
    except Exception as e:
        print(f"\nĐã xảy ra lỗi khi tải file '{file_path}': {e}")
        return jsonify({
            "message": f"Đã xảy ra lỗi khi xử lý tệp: {e}",
            "initial_data": None
        }), 500

    return jsonify({
        "message": "Tệp đã được xử lý và Ontology đã được xây dựng.",
        "initial_data": clustering_tree
    }), 200

@socketio.on('send_message')
def handle_send_message(data):
    """
    Xử lý tất cả các tin nhắn chat từ client.
    """
    session_id = data.get('session_id')
    question = data.get('message')
    chat_mode = data.get('mode') # 'available' hoặc 'new'

    if not all([session_id, question, chat_mode]):
        emit('chat_error', {'chat_error': 'Dữ liệu không hợp lệ.'})
        return

    # Thêm tin nhắn người dùng vào lịch sử
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    chat_histories[session_id].append({"sender": "user", "text": question})
    
    bot_response = "Xin lỗi, đã có lỗi xảy ra."
    
    try:
        if chat_mode == 'available':
            # --- Logic cho chat với ontology có sẵn ---
            ontology, relation = load_ontologies("Available")
            if ontology and relation:
                entities = find_entities_from_question_PP1(client, relation, question, chat_histories[session_id])
                raw_info = find_question_info(ontology, model_embedding, question, json.loads(entities))
                if not raw_info: raw_info.append("Không có thông tin cho câu hỏi từ ontology mặc định.")
                k_similar_info = find_similar_info_from_raw_informations(model_embedding, question, raw_info)
                bot_response = generate_response(client, k_similar_info, question, chat_histories[session_id])
            else:
                bot_response = "Không thể tải ontology mặc định."

        elif chat_mode == 'new':
            # --- Logic cho chat với ontology mới ---
            ontology_info = get_ontology_state(session_id)
            if ontology_info and ontology_info.get('status') == 'completed':
                ontology_path = ontology_info.get('ontology_path')
                ontology, relation = load_ontologies("New", onto_path=ontology_path)
                if ontology and relation:
                    entities = find_entities_from_question_PP1(client, relation, question, chat_histories[session_id])
                    raw_info = find_question_info(ontology, model_embedding, question, json.loads(entities))
                    if not raw_info: raw_info.append("Không có thông tin cho câu hỏi từ ontology mới.")
                    k_similar_info = find_similar_info_from_raw_informations(model_embedding, question, raw_info)
                    bot_response = generate_response(client, k_similar_info, question, chat_histories[session_id])
                else:
                    bot_response = f"Không thể tải ontology mới từ đường dẫn: {ontology_path}"
            else:
                bot_response = "Ontology mới chưa sẵn sàng. Vui lòng upload và chờ xử lý xong."

    except Exception as e:
        print(f"Lỗi khi xử lý chat: {e}")
        import traceback
        traceback.print_exc()
        bot_response = f"Đã xảy ra lỗi khi xử lý yêu cầu của bạn: {e}"

    # Thêm phản hồi của bot vào lịch sử
    chat_histories[session_id].append({"sender": "bot", "text": bot_response})
    
    # Gửi phản hồi về cho client trong phòng của họ
    emit('new_message', {"sender": "bot", "text": bot_response}, room=session_id)

@app.route("/api/get-chat-history", methods=["GET"])
def get_chat_history():
    """Endpoint để lấy lịch sử chat của session hiện tại"""
    current_user_id = get_current_session_id()

    if not current_user_id:
        return jsonify({
            "session_id": None,
            "chat_history": [],
            "message": "Chưa có session"
        })

    initialize_user_data(current_user_id)

    return jsonify({
        "session_id": current_user_id,
        "chat_history": chat_histories.get(current_user_id, [])
    })


@app.route("/api/clear-chat-history", methods=["POST"])
def clear_chat_history():
    """Endpoint để xóa lịch sử chat của session hiện tại"""
    current_user_id = get_current_session_id()

    if not current_user_id:
        return jsonify({"error": "Không có session hợp lệ"}), 400

    chat_histories[current_user_id] = []

    return jsonify({
        "message": "Lịch sử chat đã được xóa",
        "session_id": current_user_id
    })


@app.route("/api/reset-session", methods=["POST"])
def reset_session_route():
    """Endpoint để xóa session hiện tại và tạo session mới."""
    current_session_id = get_current_session_id()
    if current_session_id:
        cleanup_session_data(current_session_id)  # Xóa dữ liệu của session cũ
        print(f"Đã dọn dẹp dữ liệu cho session cũ: {current_session_id}")

    new_session_id = create_new_session()  # Tạo session mới
    initialize_user_data(new_session_id)  # Khởi tạo chat history cho session mới

    return jsonify({
        "session_id": new_session_id,
        "message": "Session đã được reset và tạo mới."
    }), 200
@app.route("/api/session-info", methods=["GET"])
def get_session_info():
    """Endpoint để lấy thông tin chi tiết về session"""
    current_user_id = get_current_session_id()

    if not current_user_id:
        return jsonify({
            "session_id": None,
            "chat_history_length": 0,
            "ontology_status": None,
            "ontology_timestamp": None,
            "message": "Chưa có session"
        })

    initialize_user_data(current_user_id)
    ontology_info = get_ontology_state(current_user_id)

    return jsonify({
        "session_id": current_user_id,
        "chat_history_length": len(chat_histories.get(current_user_id, [])),
        "ontology_status": ontology_info.get('status') if ontology_info else None,
        "ontology_timestamp": ontology_info.get('timestamp') if ontology_info else None,
        "has_new_ontology": bool(ontology_info and ontology_info.get('status') == 'completed')
    })


# --- Middleware và Error Handlers ---

@app.before_request
def before_request():
    """Middleware chạy trước mỗi request"""
    print(f"Request: {request.method} {request.path}")
    current_session = get_current_session_id()
    if current_session:
        print(f"Current session: {current_session}")
    else:
        print("No current session")


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint không tồn tại"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Lỗi server nội bộ"}), 500


# --- Chạy ứng dụng ---
if __name__ == "__main__":
    print("Đang khởi động Flask app...")
    print(f"Secret key được set: {'Có' if app.config['SECRET_KEY'] else 'Không'}")
    print(f"Redis kết nối: {'Có' if redis_client else 'Không'}")

    # Chạy Flask app ở chế độ tuần tự
    # app.run(debug=True, host='0.0.0.0', port=5000)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)