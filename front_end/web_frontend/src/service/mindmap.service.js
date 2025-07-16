  
import axios from 'axios';
import { io } from 'socket.io-client'; 


// URL cơ sở cho API backend
const API_BASE_URL = 'http://localhost:5000/api';

// Instance Axios vẫn được giữ lại cho các request HTTP cần thiết
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Quan trọng để quản lý session qua cookie
});

/**
 * Đây là một class Service mới, được thiết kế theo mô hình Singleton (chỉ có một thể hiện duy nhất).
 * Nó quản lý cả kết nối WebSocket và các yêu cầu HTTP.
 */
class MindmapService {
  socket; // Thuộc tính để giữ kết nối socket

  constructor() {
    this.socket = null;
  }

  // --- CÁC PHƯƠNG THỨC HTTP (Dùng cho các tác vụ không real-time) ---

  /**
   * Lấy thông tin session ban đầu khi tải ứng dụng.
   * @returns {Promise<Object>} Dữ liệu session, bao gồm session_id, lịch sử chat cũ, và trạng thái ontology.
   */
  async getSession() {
    try {
      const response = await api.get('/get-session');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi lấy session:', error);
      throw error;
    }
  }
  async resetSession () {
    try {
      // Backend cần có endpoint này để dọn dẹp và tạo session mới
      const response = await api.post('/reset-session');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi reset session:', error);
      throw error;
    }
  }
  async getSessionInfo () {
    try {
      const response = await api.get('/session-info');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi lấy thông tin session:', error);
      throw error;
    }
  }
  async clearChatHistory() {
    try {
      const response = await api.post('/clear-chat-history');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi xóa lịch sử chat:', error);
      throw error;
    }
  }
  async getChatHistory () {
    try {
      const response = await api.get('/get-chat-history');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi lấy lịch sử chat:', error);
      throw error;
    }
  }
  async  get_available_mindmap () { 
    try {
      const response = await api.get('/get_available_mindmap');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi lấy mindmap có sẵn:', error);
      throw error;
    }
  }

  /**
   * Tải file PDF lên server.
   * Server sẽ nhận file và bắt đầu một tác vụ xử lý ở chế độ nền.
   * @param {File} pdfFile - File PDF để tải lên.
   * @param {string} sessionId - Session ID hiện tại của người dùng.
   * @returns {Promise<Object>} Một thông báo xác nhận rằng file đã được nhận.
   */
  async uploadPdf(pdfFile, sessionId) {
    const formData = new FormData();
    formData.append('pdf_file', pdfFile);
    formData.append('session_id', sessionId); // Server cần session_id để biết gửi tiến trình cho ai

    try {
      const response = await api.post('/upload-pdf', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Lỗi khi tải lên PDF:', error);
      throw error;
    }
  }

  // --- CÁC PHƯƠNG THỨC WEBSOCKET ---

  /**
   * Khởi tạo kết nối WebSocket đến server và thiết lập các trình lắng nghe sự kiện.
   * @param {string} sessionId - Session ID để tham gia vào "phòng" chat riêng.
   * @param {Object} eventCallbacks - Một object chứa các hàm callback để xử lý sự kiện từ server.
   * Ví dụ: { onNewMessage: (data) => { ... }, onOntologyProgress: (data) => { ... } }
   */
  connect(sessionId, eventCallbacks) {
    if (this.socket) {
      this.socket.disconnect();
    }

    this.socket = io("http://localhost:5000");

    // Lắng nghe sự kiện kết nối thành công
    this.socket.on('connect', () => {
      console.log('Socket.IO connected with ID:', this.socket.id);
      // Tham gia vào phòng riêng của session
      this.socket.emit('join_room', { session_id: sessionId });
    });

    // Đăng ký các hàm callback để Vue component có thể phản ứng với sự kiện
    if (eventCallbacks) {
      this.socket.on('new_message', eventCallbacks.onNewMessage);
      this.socket.on('ontology_progress', eventCallbacks.onOntologyProgress);
      this.socket.on('ontology_complete', eventCallbacks.onOntologyComplete);
      this.socket.on('ontology_error', eventCallbacks.onOntologyError);
      this.socket.on('chat_error', eventCallbacks.onChatError);
    }
    
    this.socket.on('disconnect', () => {
      console.log('Socket.IO disconnected');
    });

  }

  /**
   * Ngắt kết nối WebSocket.
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  // --- CÁC HÀM GỬI SỰ KIỆN (EMITTERS) ---

  /**
   * Gửi tin nhắn chat đến server qua WebSocket.
   * Thay thế cho cả `chatWithNewOntology` và `chatWithDefaultOntology`.
   * @param {string} message - Nội dung tin nhắn.
   * @param {string} mode - Chế độ chat ('available' hoặc 'new').
   * @param {string} sessionId - Session ID của người gửi.
   */
  sendMessage(message, mode, sessionId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('send_message', {
        session_id: sessionId,
        message: message,
        mode: mode,
      });
    } else {
      console.error("Socket chưa được kết nối. Không thể gửi tin nhắn.");
    }
  }
  // chatWithNewOntology (message, sessionId) {
  //   if (this.socket && this.socket.connected) {
  //     this.socket.emit('send_message_newOnto', {message});
  //   } else {
  //     console.error("Socket chưa được kết nối. Không thể gửi tin nhắn.");
  //   }
  // }

}

// Xuất ra một thể hiện duy nhất của class (Singleton Pattern)
// để toàn bộ ứng dụng dùng chung một service và một kết nối socket.
export default new MindmapService();
