<!-- view/HomePage.vue -->
<template>
    <div class="home-page-container">
      <h1>Chào mừng đến với ứng dụng Mindmap!</h1>
      <p>Sử dụng để tạo Mindmap từ tài liệu PDF của bạn hoặc khám phá kiến thức lịch sử Việt Nam bằng cách trò chuyện.</p>
      <div class="navigation-cards">
        <div class="card" @click="goToUpload">
          <h2>Tạo Mindmap mới</h2>
          <p>Upload file PDF của bạn để tạo Mindmap và trò chuyện.</p>
          <button class="primary-button">Upload PDF</button>
        </div>
        <div class="card" @click="goToDefaultChat">
          <h2>Tìm hiểu kiến thức</h2>
          <p>Trò chuyện với về kiến thức chung của lịch sử Việt Nam giai đoạn 1945-2000.</p>
          <button class="secondary-button">Trò chuyện ngay</button>
        </div>
      </div>
      <div class="app-description">
        <h3>Tính năng chính:</h3>
        <ul>
          <li>Chuyển đổi PDF thành Mindmap thông minh.</li>
          <li>Tương tác, trò chuyện với Mindmap để tìm kiếm thông tin.</li>
          <li>Hỗ trợ giải đáp thắc mắc về kiến thức lịch sử Việt Nam giai đoạn 1945-2000.</li>
        </ul>
      </div>
    </div>
  </template>
  
  <script>
  import MindmapService from '../service/mindmap.service.js'; // Import service mới
  
  export default {
    name: 'HomePage',
    methods: {
      goToUpload() {
        this.$router.push('/upload');
      },
      async goToDefaultChat() {
        try {
          // Reset session trước khi chuyển đến trang chat với ontology mặc định
          await MindmapService.resetSession();
          console.log("Session đã được reset cho chat mặc định.");
        } catch (error) {
          console.error("Không thể reset session trước khi vào chat mặc định:", error);
          // Xử lý lỗi nếu cần, nhưng vẫn cố gắng chuyển hướng để người dùng có thể tiếp tục
        } finally {
          this.$router.push('/default_chat');
        }
      }
    }
  };
  </script>
  
  <style scoped>
  .home-page-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    max-width: 900px;
    margin: 40px auto;
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
    text-align: center;
  }
  
  h1 {
    color: #2c3e50;
    margin-bottom: 20px;
    font-size: 2.5em;
  }
  
  p {
    color: #555;
    font-size: 1.1em;
    line-height: 1.6;
    margin-bottom: 30px;
  }
  
  .navigation-cards {
    display: flex;
    gap: 30px;
    margin-bottom: 40px;
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .card {
    background-color: #f8faff;
    border: 1px solid #e0e7ff;
    border-radius: 10px;
    padding: 25px;
    flex: 1;
    min-width: 280px;
    max-width: 400px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    cursor: pointer;
  }
  
  .card:hover {
    transform: translateY(-8px);
    box-shadow: 0 12px 25px rgba(0, 0, 0, 0.15);
  }
  
  .card h2 {
    color: #4a90e2;
    margin-top: 0;
    font-size: 1.6em;
  }
  
  .card p {
    font-size: 0.95em;
    color: #666;
    margin-bottom: 20px;
  }
  
  .primary-button, .secondary-button {
    padding: 12px 25px;
    border: none;
    border-radius: 6px;
    font-size: 1.05em;
    cursor: pointer;
    transition: background-color 0.3s ease, transform 0.2s ease;
    font-weight: bold;
  }
  
  .primary-button {
    background-color: #4a90e2;
    color: white;
  }
  
  .primary-button:hover {
    background-color: #357bd8;
    transform: translateY(-2px);
  }
  
  .secondary-button {
    background-color: #69b3a2;
    color: white;
  }
  
  .secondary-button:hover {
    background-color: #529c8e;
    transform: translateY(-2px);
  }
  
  .app-description {
    margin-top: 40px;
    text-align: left;
    width: 100%;
  }
  
  .app-description h3 {
    color: #2c3e50;
    font-size: 1.8em;
    margin-bottom: 15px;
    border-bottom: 2px solid #eee;
    padding-bottom: 10px;
  }
  
  .app-description ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  
  .app-description li {
    background-color: #e9f2fa;
    margin-bottom: 10px;
    padding: 15px 20px;
    border-radius: 8px;
    border-left: 5px solid #4a90e2;
    font-size: 1em;
    color: #333;
  }
  </style>
  