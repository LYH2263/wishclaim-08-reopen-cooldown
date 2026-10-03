<template>
  <div class="wall">
    <h1 class="serif">{{ w.title }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>
    <p v-if="w.in_cooldown" class="tag cooldown">
      冷却中 · 截止 {{ fmt(w.cooldown_until) }} · 剩余 {{ w.cooldown_remaining_seconds }} 秒
    </p>
    <p v-if="err" class="err">{{ err }}</p>
    <input v-model="claimer" placeholder="你的名字" />
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button @click="claim">认领锁定</button>
      <button class="ghost" @click="release">释放</button>
      <button class="ghost" @click="fulfill">核销完成</button>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const err = ref('')
const fmt = (s) => (s ? new Date(s).toLocaleString() : '')
const FRIENDLY = { cooldown: '冷却中，暂不可认领', locked: '已被他人锁定', already_fulfilled: '已核销完成' }
async function load() { w.value = await api('/wishes/' + props.id) }
async function act(path, body) {
  err.value = ''
  try { await api('/wishes/' + props.id + path, { method: 'POST', body: JSON.stringify(body) }); await load() }
  catch (e) { err.value = FRIENDLY[e.message] || e.message }
}
const claim = () => act('/claim', { claimer: claimer.value })
const release = () => act('/release', {})
const fulfill = () => act('/fulfill', {})
onMounted(load)
</script>
