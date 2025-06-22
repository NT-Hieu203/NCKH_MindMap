<!-- view/UploadPage.vue -->
<template>
    <div class="upload-page-container">
      <h1 class="page-title">Tải lên tài liệu PDF của bạn</h1>
      <p class="page-description">Vui lòng chọn một file PDF để tạo Mindmap Ontology.</p>
  
      <div class="upload-card">
        <input type="file" ref="pdfInput" @change="handleFileChange" accept=".pdf" style="display: none;">
        <button @click="selectFile" class="select-file-button" :disabled="isUploading">
          <span v-if="!selectedFile">Chọn File PDF</span>
          <span v-else>{{ selectedFile.name }} (Đã chọn)</span>
        </button>
  
        <button @click="uploadFile" :disabled="!selectedFile || isUploading" class="upload-button">
          <span v-if="!isUploading">Tạo Mindmap</span>
          <span v-else>Đang xử lý...</span>
        </button>
  
        <div v-if="isUploading" class="loading-indicator">
          <div class="spinner"></div>
          <p>Đang tải lên và xử lý Mindmap của bạn. Quá trình này có thể mất vài phút.</p>
        </div>
  
        <div v-if="uploadMessage" :class="['message', messageType]">
          {{ uploadMessage }}
        </div>
      </div>
  
      <!-- <div class="mindmap-display-area" v-if="initialMindmapData && initialMindmapData.length > 0">
        <h2 class="section-title">Mindmap đã tạo:</h2>
        <p class="section-description">Bạn có thể tương tác với Mindmap này hoặc bắt đầu trò chuyện.</p>
        <MindMapViewer :data="initialMindmapData" class="mindmap-viewer"></MindMapViewer>
        <div class="action-buttons">
          <button @click="goToMindMapChat" class="chat-button">Trò chuyện với Mindmap này</button>
        </div>
      </div> -->
  
      <div class="back-home">
        <button @click="goToHome" :disabled="isUploading" class="go-back-button">Quay lại trang chủ</button>
      </div>
    </div>
  </template>
  
  <script>
  import MindMapViewer from '../components/MindMapViewer.vue';
  import MindmapService from '../service/mindmap.service.js'; // Import service mới
  
  export default {
    name: 'UploadPage',
    components: {
      MindMapViewer
    },
    data() {
      return {
        selectedFile: null,
        isUploading: false,
        uploadMessage: '',
        messageType: '', // 'success' or 'error'
        initialMindmapData: null,
      };
    },
    methods: {
      selectFile() {
        this.$refs.pdfInput.click();
      },
      handleFileChange(event) {
        this.selectedFile = event.target.files[0];
        this.uploadMessage = ''; // Xóa các tin nhắn cũ
        this.initialMindmapData = null; // Xóa dữ liệu mindmap cũ
      },
      async uploadFile() {
        if (!this.selectedFile) {
          this.uploadMessage = 'Vui lòng chọn một file PDF trước.';
          this.messageType = 'error';
          return;
        }
  
        this.isUploading = true;
        this.uploadMessage = '';
        this.messageType = '';
  
        try {
          const responseData = await MindmapService.uploadPdf(this.selectedFile);
  
          if (responseData && responseData.initial_data) {
            this.initialMindmapData = responseData.initial_data;
            // Lưu initialMindmapData vào sessionStorage để MindMapChatPage có thể truy cập
            sessionStorage.setItem('mindmapDataForChat', JSON.stringify(this.initialMindmapData));
  
            this.uploadMessage = 'Upload và tạo Mindmap thành công!';
            this.messageType = 'success';
            this.$router.push('/chat_with_mindmap');
            console.log("Mindmap Data:", this.initialMindmapData);
            console.log("Session ID (managed by cookie):", responseData.session_id);
          } else {
            this.uploadMessage = 'Upload thành công nhưng không nhận được dữ liệu Mindmap.';
            this.messageType = 'error';
          }
        } catch (error) {
          console.error('Lỗi khi upload file:', error);
          if (error.response && error.response.data && error.response.data.error) {
            this.uploadMessage = `Lỗi: ${error.response.data.error}`;
          } else {
            this.uploadMessage = 'Đã xảy ra lỗi khi upload hoặc xử lý file PDF.';
          }
          this.messageType = 'error';
        } finally {
          this.isUploading = false;
        }
      },
      goToMindMapChat() {
        this.$router.push('/chat_with_mindmap');
      },
      goToHome() {
        this.$router.push('/');
      }
    }
  };
  </script>
  
  <style scoped>
  .upload-page-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px;
    max-width: 900px;
    margin: 40px auto;
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
    text-align: center;
    width: 100%;
  }
  
  .page-title {
    color: #2c3e50;
    margin-bottom: 15px;
    font-size: 2.2em;
  }
  
  .page-description {
    color: #555;
    font-size: 1.05em;
    margin-bottom: 30px;
  }
  
  .upload-card {
    background-color: #f8faff;
    border: 1px dashed #a7c7ed;
    border-radius: 10px;
    padding: 30px;
    width: 100%;
    max-width: 500px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    align-items: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.07);
    margin-bottom: 30px;
  }
  
  .select-file-button, .upload-button {
    padding: 12px 25px;
    border: none;
    border-radius: 6px;
    font-size: 1.05em;
    cursor: pointer;
    transition: background-color 0.3s ease, transform 0.2s ease, opacity 0.3s ease;
    font-weight: bold;
    width: 100%;
    max-width: 250px;
  }
  
  .select-file-button:hover:not(:disabled) {
    background-color: #529c8e;
    transform: translateY(-2px);
  }
  
  .upload-button:hover:not(:disabled) {
    background-color: #357bd8;
    transform: translateY(-2px);
  }
  
  .select-file-button:disabled, .upload-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  .loading-indicator {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-top: 20px;
    color: #4a90e2;
  }
  
  .spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #4a90e2;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin-bottom: 10px;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  
  .message {
    padding: 10px 15px;
    border-radius: 6px;
    margin-top: 20px;
    width: 100%;
    text-align: left;
  }
  
  .message.success {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
  }
  
  .message.error {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
  }
  
  .mindmap-display-area {
    width: 100%;
    height: 600px; /* Chiều cao cố định để hiển thị mindmap */
    margin-top: 40px;
    background-color: #f0f4f7;
    border-radius: 10px;
    box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 20px;
  }
  
  .section-title {
    color: #2c3e50;
    font-size: 1.8em;
    margin-bottom: 10px;
  }
  
  .section-description {
    color: #666;
    font-size: 0.95em;
    margin-bottom: 20px;
  }
  
  .mindmap-viewer {
    width: 95%;
    height: 70%; /* Chiếm phần lớn diện tích hiển thị */
    border: 1px solid #ccc;
    border-radius: 8px;
    overflow: hidden; /* Đảm bảo mindmap không tràn ra ngoài */
  }
  
  .action-buttons {
    margin-top: 25px;
  }
  
  .chat-button {
    background-color: #f7941d;
    color: white;
    padding: 12px 30px;
    border: none;
    border-radius: 6px;
    font-size: 1.1em;
    font-weight: bold;
    cursor: pointer;
    transition: background-color 0.3s ease, transform 0.2s ease;
  }
  
  .chat-button:hover {
    background-color: #e0830a;
    transform: translateY(-2px);
  }
  
  .go-back-button {
    margin-top: 30px;
    background: none;
    border: 1px solid #ccc;
    padding: 10px 20px;
    border-radius: 6px;
    cursor: pointer;
    color: #555;
    transition: background-color 0.3s ease, color 0.3s ease;
  }
  
  .go-back-button:hover {
    background-color: #f0f0f0;
    color: #333;
  }
  </style>
  