// main.js
import { createApp } from 'vue';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';

// Import các trang View
import HomePage from './view/HomePage.vue';
import UploadPage from './view/UploadPage.vue';
import MindMapChatPage from './view/MindMapChatPage.vue';
import DefaultChatPage from './view/DefaultChatPage.vue';

// Định nghĩa các Routes
const routes = [
    { path: '/', component: HomePage },
    { path: '/upload', component: UploadPage },
    { path: '/chat_with_mindmap', component: MindMapChatPage },
    { path: '/default_chat', component: DefaultChatPage },
];

// Tạo Router instance
const router = createRouter({
    history: createWebHistory(),
    routes,
});

const app = createApp(App);
app.use(router); // Sử dụng router trong ứng dụng Vue
app.mount('#app');

// Thêm logic để reset session khi người dùng điều hướng bằng cách khác (ví dụ: gõ URL)
// hoặc khi quay về trang chủ từ các trang con (nếu muốn reset hoàn toàn)
// Tuy nhiên, việc reset session theo yêu cầu "khi trở lại trang chủ và bấm lại thì phải tạo lại"
// đã được xử lý trong HomePage.vue bằng cách gọi chatService.removeSession()
// trước khi navigate. Điều này tốt hơn là reset toàn bộ ở đây.