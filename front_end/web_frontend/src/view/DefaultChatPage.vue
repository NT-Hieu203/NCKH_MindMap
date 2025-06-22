<!-- view/DefaultChatPage.vue -->
<template>
    <div class="chat-page-container">
      <div class="header">
        <button @click="goToHome" class="back-button">
          &larr; Trang chủ
        </button>
        <h1 class="page-title">Trò chuyện với Mindmap mặc định</h1>
        <button @click="clearChat" class="clear-chat-button">
          Xóa lịch sử
        </button>
      </div>
  
      <div class="chat-area">
        <div class="messages" ref="messagesContainer">
          <div v-if="chatHistory.length === 0" class="no-messages">
            Chào mừng! Hãy hỏi tôi bất cứ điều gì về kiến thức chung.
          </div>
          <div v-for="(msg, index) in chatHistory" :key="index" :class="['message-bubble', msg.sender]">
            <div v-if="msg.sender === 'user'">
              <p>{{ msg.text }}</p>
            </div>
            <div v-else v-html="renderMarkdown(msg.text)"></div>
          </div>
          <div v-if="isLoading" class="message-bubble bot loading">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
  
        <div class="chat-input-area">
          <input
            type="text"
            v-model="userMessage"
            @keyup.enter="sendMessage"
            placeholder="Nhập câu hỏi của bạn..."
            :disabled="isLoading"
            class="chat-input"
          />
          <button @click="sendMessage" :disabled="!userMessage.trim() || isLoading" class="send-button">
            Gửi
          </button>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import MindmapService from '../service/mindmap.service.js'; // Import service mới
  import { marked } from 'marked';
  export default {
    name: 'DefaultChatPage',
    data() {
      return {
        userMessage: '',
        chatHistory: [],
        isLoading: false,
      };
    },
    async created() {
      // Khi component được tạo, cố gắng tải lịch sử chat
      await this.fetchChatHistory();
    },
    updated() {
      this.scrollToBottom();
    },
    methods: {
      async fetchChatHistory() {
        this.isLoading = true;
        try {
          const responseData = await MindmapService.getChatHistory();
          if (responseData && responseData.chat_history) {
            this.chatHistory = responseData.chat_history;
          }
        } catch (error) {
          console.error('Lỗi khi lấy lịch sử chat:', error);
          // Có thể hiển thị thông báo lỗi cho người dùng
        } finally {
          this.isLoading = false;
        }
      },
      renderMarkdown(text) {
        return marked.parse(text);
      },
      async sendMessage() {
        if (!this.userMessage.trim() || this.isLoading) return;
  
        const message = this.userMessage;
        this.chatHistory.push({ sender: 'user', text: message });
        this.userMessage = '';
        this.isLoading = true;
        this.scrollToBottom();
  
        try {
          // Gọi service để chat với ontology mặc định
          const responseData = await MindmapService.chatWithDefaultOntology(message);
          if (responseData && responseData.response) {
            this.chatHistory.push({ sender: 'bot', text: responseData.response });
          } else {
            this.chatHistory.push({ sender: 'bot', text: 'Xin lỗi, tôi không thể trả lời lúc này.' });
          }
        } catch (error) {
          console.error('Lỗi khi gửi tin nhắn đến Mindmap mặc định:', error);
           if (error.response && error.response.data && error.response.data.error) {
             this.chatHistory.push({ sender: 'bot', text: `Lỗi: ${error.response.data.error}` });
          } else {
             this.chatHistory.push({ sender: 'bot', text: 'Đã xảy ra lỗi khi trò chuyện với Mindmap mặc định. Vui lòng thử lại.' });
          }
        } finally {
          this.isLoading = false;
          this.scrollToBottom();
        }
      },
      async clearChat() {
        if (confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử chat?')) {
          try {
            this.isLoading = true;
            await MindmapService.clearChatHistory(); // Gọi service để xóa lịch sử chat
            this.chatHistory = [];
            this.isLoading = false;
            alert('Lịch sử chat đã được xóa!');
          } catch (error) {
            console.error('Lỗi khi xóa lịch sử chat:', error);
            alert('Không thể xóa lịch sử chat. Vui lòng thử lại.');
            this.isLoading = false;
          }
        }
      },
      scrollToBottom() {
        this.$nextTick(() => {
          const messagesContainer = this.$refs.messagesContainer;
          if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
          }
        });
      },
      goToHome() {
        this.$router.push('/');
      }
    }
  };
  </script>
  
  <style scoped>
  /* Có thể tái sử dụng gần như toàn bộ CSS từ MindMapChatPage.vue */
  .chat-page-container {
    display: flex;
    flex-direction: column;
    width: 900px;
    max-width: 900px;
    height: 85vh; /* Chiều cao cố định cho trang chat */
    margin: 40px auto;
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    background-color: #69b3a2; /* Màu khác cho phân biệt */
    color: white;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
  }
  
  .header .page-title {
    margin: 0;
    font-size: 1.6em;
    font-weight: bold;
    text-align: center;
    flex-grow: 1;
  }
  
  .back-button, .clear-chat-button {
    background: none;
    border: 1px solid rgba(255, 255, 255, 0.6);
    color: white;
    padding: 10px;
    margin: 10px;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.3s ease, border-color 0.3s ease;
    font-size: 0.9em;
  }
  
  .back-button:hover, .clear-chat-button:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.8);
  }
  
  .chat-area {
    display: flex;
    flex-direction: column;
    flex-grow: 1;
    padding: 20px;
    overflow: hidden;
  }
  
  .messages {
    flex-grow: 1;
    overflow-y: auto;
    padding-right: 10px;
    margin-bottom: 20px;
  }
  
  .no-messages {
    text-align: center;
    color: #999;
    font-style: italic;
    padding: 20px;
  }
  
  .message-bubble {
    max-width: fit-content;
    padding: 12px 18px;
    border-radius: 20px;
    margin-bottom: 15px;
    line-height: 1.5;
    word-wrap: break-word;
    word-break: break-word;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.08);
  }
  
  .message-bubble.user {
    background-color: #e0f2fe;
    color: #333;
    align-self: flex-end;
    margin-left: auto;
    border-bottom-right-radius: 5px;
    text-align: right;
  }
  
  .message-bubble.bot {
    background-color:#f1f8e9;
    color: #333;
    align-self: flex-start;
    margin-right: auto;
    border-bottom-left-radius: 5px;
  }
  
  .chat-input-area {
    display: flex;
    padding-top: 15px;
    border-top: 1px solid #eee;
    background-color: #ffffff;
    padding-bottom: 5px;
  }
  
  .chat-input {
    flex-grow: 1;
    padding: 12px 18px;
    border: 1px solid #ddd;
    border-radius: 25px;
    font-size: 1.0em;
    outline: none;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
  }
  
  .chat-input:focus {
    border-color: #69b3a2; /* Màu khác cho focus */
    box-shadow: 0 0 0 3px rgba(105, 179, 162, 0.2);
  }
  
  .send-button {
    background-color: #69b3a2; /* Màu khác cho nút gửi */
    color: white;
    border: none;
    border-radius: 25px;
    padding: 12px 25px;
    margin-left: 10px;
    font-size: 1.0em;
    cursor: pointer;
    transition: background-color 0.3s ease, transform 0.2s ease;
    font-weight: bold;
  }
  
  .send-button:hover:not(:disabled) {
    background-color: #529c8e;
    transform: translateY(-1px);
  }
  
  .send-button:disabled {
    background-color: #a2d2cb; /* Màu khác cho disabled */
    cursor: not-allowed;
  }
  
  /* Typing indicator */
  .typing-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 20px;
  }
  
  .typing-indicator span {
    height: 8px;
    width: 8px;
    background-color: #888;
    border-radius: 50%;
    margin: 0 3px;
    animation: typing-bounce 0.6s infinite ease-in-out;
  }
  
  .typing-indicator span:nth-child(2) {
    animation-delay: 0.2s;
  }
  
  .typing-indicator span:nth-child(3) {
    animation-delay: 0.4s;
  }
  
  @keyframes typing-bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-5px); }
  }
  </style>
  