// service/mindmap.service.js
import axios from 'axios';

// Định nghĩa URL cơ sở cho API backend của bạn
const API_BASE_URL = 'http://localhost:5000/api';

// Tạo một instance Axios tùy chỉnh để đảm bảo `withCredentials` luôn được bật
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Rất quan trọng để gửi và nhận cookie session
});

const MindmapService = {
  /**
   * Lấy thông tin session hiện tại từ backend.
   * Backend sẽ không tạo session mới nếu chưa có.
   * @returns {Promise<Object>} Thông tin session (session_id, message)
   */
  getSession: async () => {
    try {
      const response = await api.get('/get-session');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi lấy session:', error);
      throw error;
    }
  },

  /**
   * Tải lên file PDF và bắt đầu quá trình xử lý để tạo Mindmap/Ontology mới.
   * Endpoint này sẽ tạo một session ID mới trên backend.
   * @param {File} pdfFile - File PDF được chọn để tải lên.
   * @returns {Promise<Object>} Dữ liệu trả về từ backend (initial_data, session_id, ontology_status, ontology_path)
   */
  uploadPdf: async (pdfFile) => {
    const formData = new FormData();
    formData.append('pdf_file', pdfFile);

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
  },

  /**
   * Gửi tin nhắn để trò chuyện với Ontology mới được tạo từ PDF.
   * Yêu cầu một session đã có ontology mới.
   * @param {string} message - Tin nhắn của người dùng.
   * @returns {Promise<Object>} Phản hồi từ bot và session_id.
   */
  chatWithNewOntology: async (message) => {
    try {
      const response = await api.post('/chat_newOnto', { message });
      return response.data;
    } catch (error) {
      console.error('Lỗi khi trò chuyện với ontology mới:', error);
      throw error;
    }
  },

  /**
   * Gửi tin nhắn để trò chuyện với Ontology mặc định có sẵn.
   * Sẽ tạo session mới nếu chưa có.
   * @param {string} message - Tin nhắn của người dùng.
   * @returns {Promise<Object>} Phản hồi từ bot và session_id.
   */
  chatWithDefaultOntology: async (message) => {
    try {
      const response = await api.post('/chat_with_available_onto', { message });
      return response.data;
    } catch (error) {
      console.error('Lỗi khi trò chuyện với ontology mặc định:', error);
      throw error;
    }
  },

  /**
   * Lấy lịch sử chat của session hiện tại.
   * @returns {Promise<Object>} Lịch sử chat (chat_history, session_id).
   */
  getChatHistory: async () => {
    try {
      const response = await api.get('/get-chat-history');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi lấy lịch sử chat:', error);
      throw error;
    }
  },

  /**
   * Xóa lịch sử chat của session hiện tại.
   * @returns {Promise<Object>} Thông báo thành công và session_id.
   */
  clearChatHistory: async () => {
    try {
      const response = await api.post('/clear-chat-history');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi xóa lịch sử chat:', error);
      throw error;
    }
  },

  /**
   * Lấy thông tin chi tiết về session hiện tại.
   * @returns {Promise<Object>} Thông tin session (has_new_ontology, ontology_status, etc.)
   */
  getSessionInfo: async () => {
    try {
      const response = await api.get('/session-info');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi lấy thông tin session:', error);
      throw error;
    }
  },

  /**
   * Xóa session hiện tại và tạo một session mới trên backend.
   * Dùng khi cần đảm bảo một khởi đầu sạch sẽ cho một luồng mới.
   * @returns {Promise<Object>} Thông tin session mới.
   */
  resetSession: async () => {
    try {
      // Backend cần có endpoint này để dọn dẹp và tạo session mới
      const response = await api.post('/reset-session');
      return response.data;
    } catch (error) {
      console.error('Lỗi khi reset session:', error);
      throw error;
    }
  },
};

export default MindmapService;
