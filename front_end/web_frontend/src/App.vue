<template>
  <div id="app">
    <router-view></router-view>
  </div>
</template>

<script>
export default {
  name: 'App'
};
</script>

<style>
/* CSS toàn cục */
body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  margin: 0;
  padding: 0;
  background-color: #eef2f8;
  color: #333;
  line-height: 1.6;
}

#app {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  /* Để các component không bị giãn ra toàn bộ chiều cao */
  min-height: 100vh;
  /* padding: 20px; */
  box-sizing: border-box;
}

/* Các style chung cho card, button... có thể đặt ở đây hoặc trong từng component */
</style>