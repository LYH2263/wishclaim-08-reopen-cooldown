<template>
  <div class="wall">
    <h1 class="serif">愿望墙</h1>
    <p class="tag">无顶栏 · 瀑布流 · 点卡片认领</p>
    <div class="masonry">
      <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
        <h3>{{ w.title || '（无标题）' }}</h3>
        <p>{{ w.note }}</p>
        <span class="tag">{{ w.status }} · {{ w.data_quality }}</span>
        <p v-if="w.cooldown_active" class="tag">冷却至 {{ fmt(w.cooldown_until) }}</p>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
const fmt = (s) => new Date(s).toLocaleString()
onMounted(async () => { rows.value = await api('/wishes') })
</script>
