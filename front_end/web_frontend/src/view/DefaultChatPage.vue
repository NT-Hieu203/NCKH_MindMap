<template>
  <div class="default-chat-page-container">
    <MindMapViewer :data="mindmapData" class="fullscreen-mindmap"></MindMapViewer>

    <button @click="goToHome" class="go-back-btn" title="Quay lại Trang chủ">
      <svg class="back-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6"></polyline>
      </svg>
    </button>

    <button @click="toggleChatBox" class="chat-toggle-button" :title="showChatBox ? 'Đóng hộp chat' : 'Mở hộp chat'">
      <svg v-if="!showChatBox" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="chat-icon">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="chat-icon">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>

    <transition name="chat-slide">
      <div v-if="showChatBox" class="chat-box-overlay">
        <div class="chat-box-header">
          <h2 class="chat-box-title">Trò chuyện với Mindmap mặc định</h2>
          <button @click="toggleChatBox" class="close-chat-button" title="Đóng chat">&times;</button>
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
        <div class="chat-box-footer">
          <button @click="clearChat" class="clear-chat-button">
            Xóa lịch sử chat
          </button>
          <button @click="goToHome" class="back-to-home-button">
            Quay lại Trang chủ
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import MindmapService from '../service/mindmap.service.js';
import MindMapViewer from '../components/MindMapViewer.vue';
import { marked } from 'marked';

export default {
  name: 'DefaultChatPage',
  components: {
    MindMapViewer
  },
  data() {
    return {
      userMessage: '',
      chatHistory: [],
      isLoading: false,
      mindmapData: null,
      showChatBox: false,
      sessionId: '',
      chatMode: 'available'
    };
  },
  async created() {
    await this.fetchChatHistory();
    await this.fetchMindmapData();
    await this.initializeSessionAndSocket(); 
  },
  updated() {
    this.scrollToBottom();
  },
  methods: {
    renderMarkdown(text) {
      return marked.parse(text);
    },
    toggleChatBox() {
      this.showChatBox = !this.showChatBox;
    },
    async fetchMindmapData() {
      try {
        const responseData = await MindmapService.get_available_mindmap();
        if (responseData && responseData.initial_data) {
          this.mindmapData = responseData.initial_data;
        } else {
          console.error('Không có dữ liệu Mindmap mặc định.');
        }
      } catch (error) {
        console.error('Lỗi khi lấy dữ liệu Mindmap mặc định:', error);
      }
    },
    async fetchChatHistory() {
      this.isLoading = true;
      try {
        const responseData = await MindmapService.getChatHistory();
        if (responseData && responseData.chat_history) {
          this.chatHistory = responseData.chat_history;
        }
      } catch (error) {
        console.error('Lỗi khi lấy lịch sử chat mặc định:', error);
      } finally {
        this.isLoading = false;
      }
    },

    async initializeSessionAndSocket() {
      try {
        const sess = await MindmapService.getSession();
        this.sessionId = sess.session_id;

        MindmapService.connect(this.sessionId, {
          onNewMessage: (msg) => {
            this.chatHistory.push(msg);
            this.isLoading = false;
            this.scrollToBottom();
          },
          onChatError: (data) => {
            this.chatHistory.push({ sender: 'bot', text: `Lỗi: ${data.error}` });
            this.isLoading = false;
          },
          onOntologyProgress: () => {},
          onOntologyComplete: () => {},
          onOntologyError: () => {}
        });
      } catch (error) {
        console.error('Lỗi khi khởi tạo session/socket:', error);
      }
    },

    async sendMessage() {
      const message = this.userMessage;
      if (!message.trim() || this.isLoading) return;

      this.chatHistory.push({ sender: 'user', text: message });
      this.userMessage = '';
      this.isLoading = true;

      MindmapService.sendMessage(message, this.chatMode, this.sessionId);
      this.scrollToBottom();
    },

    async clearChat() {
      if (confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử chat?')) {
        try {
          this.isLoading = true;
          await MindmapService.clearChatHistoryDefault();
          this.chatHistory = [];
          alert('Lịch sử chat đã được xóa!');
        } catch (error) {
          console.error('Lỗi khi xóa lịch sử chat mặc định:', error);
          alert('Không thể xóa lịch sử chat. Vui lòng thử lại.');
        } finally {
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
  },

  beforeUnmount() {
    MindmapService.disconnect();
  }
};
</script>


<style scoped>
.default-chat-page-container {
  position: relative;
  width: 100vw; /* Full viewport width */
  height: 100vh; /* Full viewport height */
  overflow: hidden;
  background-color: #eef2f8; /* Matches body background */
  display: flex;
  justify-content: center;
  align-items: center;
}

.fullscreen-mindmap {
  width: 100%;
  height: 100%;
}

.chat-toggle-button {
  position: absolute;
  bottom: 30px;
  right: 30px;
  background-color: #69b3a2; /* Màu xanh lá nhạt */
  color: white;
  border: none;
  border-radius: 50%;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: background-color 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease;
  z-index: 100; /* Ensure button is on top */
}

.chat-toggle-button:hover {
  background-color: #529c8e; /* Màu xanh lá đậm hơn khi hover */
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.chat-toggle-button .chat-icon {
  width: 28px;
  height: 28px;
}

.chat-box-overlay {
  position: absolute;
  bottom: 100px; /* Position above the button */
  right: 30px;
  width: 40%;
  height: 75%;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 99; /* Below the toggle button, but above mindmap */
}

/* Transition for chat box */
.chat-slide-enter-active, .chat-slide-leave-active {
  transition: all 0.4s ease-in-out;
}
.chat-slide-enter-from, .chat-slide-leave-to {
  transform: translateY(100%) translateX(50%); /* Start/end from bottom right, outside view */
  opacity: 0;
}
.chat-slide-enter-to, .chat-slide-leave-from {
  transform: translateY(0) translateX(0);
  opacity: 1;
}

.chat-box-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background-color: #69b3a2; /* Màu xanh lá nhạt */
  color: white;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
}

.chat-box-title {
  margin: 0;
  font-size: 1.2em;
  font-weight: bold;
}

.close-chat-button {
  background: none;
  border: none;
  color: white;
  font-size: 1.8em;
  cursor: pointer;
  padding: 0 5px;
  transition: color 0.2s ease;
}

.close-chat-button:hover {
  color: #f0f0f0;
}

.chat-area {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  padding: 15px;
  overflow: hidden;
}

.messages {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 8px;
  margin-bottom: 10px;
}

.no-messages {
  text-align: center;
  color: #999;
  font-style: italic;
  padding: 10px;
  font-size: 0.9em;
}

.message-bubble {
  max-width: fit-content;
  padding: 10px 15px;
  border-radius: 18px;
  margin-bottom: 10px;
  line-height: 1.4;
  word-wrap: break-word;
  word-break: break-word;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-size: 0.9em;
}

.message-bubble.user {
  max-width: 80%;
  width: fit-content;
  background-color: #e0f2fe;
  color: #333;
  align-self: flex-end;
  margin-left: auto;
  border-bottom-right-radius: 5px;
  text-align: right;
}

.message-bubble.bot {
  background-color: #f1f8e9;
  color: #333;
  align-self: flex-start;
  margin-right: auto;
  border-bottom-left-radius: 5px;
}

.chat-input-area {
  display: flex;
  padding-top: 10px;
  border-top: 1px solid #eee;
  background-color: #ffffff;
}

.chat-input {
  flex-grow: 1;
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 20px;
  font-size: 0.95em;
  outline: none;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.chat-input:focus {
  border-color: #69b3a2;
  box-shadow: 0 0 0 2px rgba(105, 179, 162, 0.2);
}

.send-button {
  background-color: #69b3a2;
  color: white;
  border: none;
  border-radius: 20px;
  padding: 10px 20px;
  margin-left: 8px;
  font-size: 0.95em;
  cursor: pointer;
  transition: background-color 0.3s ease, transform 0.2s ease;
  font-weight: bold;
}

.send-button:hover:not(:disabled) {
  background-color: #529c8e;
  transform: translateY(-1px);
}

.send-button:disabled {
  background-color: #a2d2cb;
  cursor: not-allowed;
}

.typing-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 20px;
}

.typing-indicator span {
  height: 6px;
  width: 6px;
  background-color: #888;
  border-radius: 50%;
  margin: 0 2px;
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
  50% { transform: translateY(-3px); }
}

.chat-box-footer {
  display: flex;
  justify-content: space-between;
  padding: 10px 15px;
  border-top: 1px solid #eee;
  background-color: #ffffff;
}
.go-back-btn{
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 1000;
  width: 40px;
  height: 40px;
  background-color: #ffffff;
  border: none;
  border-radius: 50%;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: background-color 0.2s ease;
}

.clear-chat-button, .back-to-home-button { /* Đổi tên back-to-upload-button thành back-to-home-button */
  background-color: #f0f0f0;
  color: #555;
  border: 1px solid #ccc;
  padding: 8px 15px;
  border-radius: 6px;
  font-size: 0.85em;
  cursor: pointer;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.clear-chat-button:hover, .back-to-home-button:hover {
  background-color: #e0e0e0;
  color: #333;
}
</style>