from flask import Flask, request, jsonify, session
from flask_cors import CORS
import redis
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
explication = None
is_loaded = False
type_ontology = None

def load_ontologies(type, onto_path = None):
    if type == "Available":
        try:
            if os.path.exists(ONTO_AVAILABLE_PATH):
                ontology_available = get_ontology(f"file://{os.path.abspath(ONTO_AVAILABLE_PATH)}").load()
                print(f"Ontology mặc định '{ONTO_AVAILABLE_PATH}' đã được tải.")
                relation = find_relation(ontology_available)
                entities_with_annotation_sumarry = get_entities_with_annotation(ontology_available, 'summary')
                explication = create_explication(entities_with_annotation_sumarry)
                return ontology_available, relation, explication
            else:
                print(f"Warning: File ontology mặc định '{ONTO_AVAILABLE_PATH}' không tồn tại. Bỏ qua việc tải.")
                return None, None, None
        except Exception as e:
            print(f"Không thể tải ontology mặc định '{ONTO_AVAILABLE_PATH}': {e}")
    else:
        try:
            if os.path.exists(onto_path):
                ontology_available = get_ontology(f"file://{os.path.abspath(onto_path)}").load()
                print(f"Ontology mới '{onto_path}' đã được tải.")
                relation = find_relation(ontology_available)
                entities_with_annotation_sumarry = get_entities_with_annotation(ontology_available, 'summary')
                explication = create_explication(entities_with_annotation_sumarry)
                return ontology_available, relation, explication
            else:
                print(f"Warning: File ontology mới '{onto_path}' không tồn tại. Bỏ qua việc tải.")
                return None, None, None
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
    if pdf_file.filename == '':
        return jsonify({"error": "Chưa chọn tệp"}), 400

    if pdf_file and allowed_file(pdf_file.filename):
        # TẠO SESSION MỚI khi upload PDF
        user_session_id = create_new_session()
        initialize_user_data(user_session_id)

        print(f"Tạo session mới cho upload PDF: {user_session_id}")

        # Xóa các ontology cũ của session này nếu có (phòng trường hợp)
        old_ontology_info = get_ontology_state(user_session_id)
        if old_ontology_info:
            old_ontology_path = old_ontology_info.get('ontology_path')
            if old_ontology_path and os.path.exists(old_ontology_path):
                try:
                    os.remove(old_ontology_path)
                    print(f"Đã xóa ontology cũ: {old_ontology_path}")
                except Exception as e:
                    print(f"Lỗi khi xóa ontology cũ {old_ontology_path}: {e}")

        # Tạo tên file duy nhất và an toàn để lưu
        filename = secure_filename(pdf_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        pdf_file.save(file_path)
        print(f"File PDF đã lưu tạm thời: {file_path}")

        try:
            # 1. Thực hiện process_PDF_file đồng bộ
            print(f"Bắt đầu process_PDF_file đồng bộ cho {file_path}")
            clustering_tree = process_PDF_file(client, model_embedding, model_detect_layout, reader, file_path)
            print("process_PDF_file hoàn tất.")

            # 2. Xây dựng ontology ngay lập tức (tuần tự)
            print("Bắt đầu xây dựng ontology đồng bộ.")
            ontology_filename = f"{user_session_id}_ontology.owl"
            ontology_iri = f"http://www.semanticweb.org/{user_session_id}_MINDMAP"
            ontology_save_path = os.path.join(GENERATED_ONTOLOGIES_FOLDER, ontology_filename)
            create_ontology(model_embedding, clustering_tree, ontology_save_path, ontology_iri)
            print(f"Ontology đã được xây dựng và lưu tại: {ontology_save_path}")

            # Cập nhật trạng thái trong Redis
            set_ontology_state(user_session_id, {
                'status': 'completed',
                'timestamp': time.time(),
                'ontology_path': ontology_save_path,
                'created_from': 'pdf_upload'
            })

            # Dọn dẹp file PDF tạm thời
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Đã xóa file PDF tạm thời sau khi xử lý: {file_path}")

            return jsonify({
                "message": "Tệp đã được xử lý và Ontology đã được xây dựng.",
                "initial_data": clustering_tree,
                "session_id": user_session_id,
                "ontology_status": "completed",
                "ontology_path": ontology_save_path
            }), 200

        except Exception as e:
            print(f"Lỗi trong quá trình xử lý PDF hoặc xây dựng ontology: {e}")
            import traceback
            traceback.print_exc()
            # Dọn dẹp file PDF tạm nếu có lỗi
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": f"Lỗi xử lý file PDF: {str(e)}"}), 500

    return jsonify({"error": "Tệp không hợp lệ hoặc không có tệp được chọn"}), 400


@app.route("/api/chat_with_available_onto", methods=["POST"])
def chat_with_available_onto_route():
    global relation, explication, is_loaded, type_ontology, ontology_available
    if type_ontology != "Available":
        is_loaded = False
        type_ontology = "Available"

    if is_loaded == False:
        ontology_available, relation, explication = load_ontologies(type_ontology)
        is_loaded = True
    if ontology_available is None:
        return jsonify({"error": "Ontology mặc định chưa được tải hoặc không tồn tại."}), 500
    if relation is None or explication is None:
        return jsonify({"error": "Dữ liệu khởi tạo cho ontology mặc định chưa sẵn sàng."}), 500

    # TẠO SESSION MỚI nếu chưa có khi chat với ontology có sẵn
    current_user_id = get_current_session_id()
    if not current_user_id:
        current_user_id = create_new_session()
        print(f"Tạo session mới cho chat với ontology có sẵn: {current_user_id}")

    initialize_user_data(current_user_id)

    print(f"Chat với ontology mặc định cho session: {current_user_id}")

    data = request.json
    question = data.get("message", "")

    if not question:
        return jsonify({"error": "Không có tin nhắn được cung cấp"}), 400
    start_time = time.time()
    try:
        entities = find_entities_from_question_PP1(client, relation, explication, question, chat_histories[current_user_id])
        print('tìm được: ', entities)
        raw_informations_from_ontology = find_question_info(ontology_available, json.loads(entities))

        if len(raw_informations_from_ontology) == 0:
            raw_informations_from_ontology.append("Không có thông tin cho câu hỏi từ ontology mặc định.")

        k_similar_info = find_similar_info_from_raw_informations(model_embedding, question, raw_informations_from_ontology)
        bot_response = generate_response(client, k_similar_info, question, chat_histories[current_user_id])
    except Exception as e:
        print(f"Lỗi trong quá trình chat với ontology mặc định: {e}")
        import traceback
        traceback.print_exc()
        bot_response = "Xin lỗi, tôi không thể trả lời câu hỏi của bạn với ontology mặc định vào lúc này."

    end_time = time.time()
    print("Thời gian thực thi (Default Ontology Chat):", end_time - start_time, "giây")

    # Lưu vào lịch sử chat
    chat_histories[current_user_id].append({"sender": "user", "text": question})
    chat_histories[current_user_id].append({"sender": "bot", "text": bot_response})

    return jsonify({
        "response": bot_response,
        "session_id": current_user_id
    })


@app.route("/api/chat_newOnto", methods=["POST"])
def chat_with_new_ontology():
    global is_loaded, type_ontology, relation, explication, current_ontology
    if type_ontology != "New":
        type_ontology = "New"
        is_loaded = False

    # PHẢI CÓ SESSION HỢP LỆ từ việc upload PDF trước đó
    current_user_id = get_current_session_id()

    if not current_user_id:
        return jsonify({
            "error": "Không có session hợp lệ. Vui lòng upload PDF trước khi chat với ontology mới."
        }), 400

    # Kiểm tra session có ontology mới hợp lệ không
    is_valid, message = validate_session_for_new_ontology(current_user_id)
    if not is_valid:
        return jsonify({"error": message}), 400

    initialize_user_data(current_user_id)
    print(f"Chat với ontology mới cho session: {current_user_id}")

    current_ontology_info = get_ontology_state(current_user_id)
    ontology_path = current_ontology_info.get('ontology_path')
    print(f"Đang sử dụng ontology mới từ: {ontology_path}")
    if is_loaded == False:
        current_ontology, relation, explication = load_ontologies(type_ontology, ontology_path)
        is_loaded = True

    if current_ontology is None or relation is None or explication is None:
        return jsonify({"error": "Không thể tải Ontology mới cho chat"}), 500

    data = request.json
    question = data.get("message", "")

    if not question:
        return jsonify({"error": "Không có tin nhắn được cung cấp"}), 400

    start_time = time.time()
    bot_response = ""
    try:
        entities = find_entities_from_question_PP1(client, relation, explication, question,
                                                   chat_histories[current_user_id])
        print('[New] tìm được: ', entities)

        raw_informations_from_ontology = find_question_info(current_ontology, json.loads(entities))
        if len(raw_informations_from_ontology) == 0:
            raw_informations_from_ontology.append("[New] Không có thông tin cho câu hỏi từ ontology mới.")

        k_similar_info = find_similar_info_from_raw_informations(model_embedding, question,
                                                                 raw_informations_from_ontology)
        bot_response = generate_response(client, k_similar_info, question, chat_histories[current_user_id])

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Lỗi trong quá trình chat với ontology mới: {e}")
        bot_response = "Xin lỗi, tôi không thể trả lời câu hỏi của bạn với ontology mới vào lúc này."

    end_time = time.time()
    print("Thời gian thực thi (New Ontology Chat):", end_time - start_time, "giây")

    # Lưu vào lịch sử chat
    chat_histories[current_user_id].append({"sender": "user", "text": question})
    chat_histories[current_user_id].append({"sender": "bot", "text": bot_response})

    return jsonify({
        "response": bot_response,
        "session_id": current_user_id
    })


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
    app.run(debug=True, host='0.0.0.0', port=5000)