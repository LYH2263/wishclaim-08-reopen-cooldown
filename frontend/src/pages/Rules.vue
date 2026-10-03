<template>
  <div class="wall">
    <h1 class="serif">规则</h1>
    <ul>
      <li v-for="(v,k) in rules" :key="k"><strong>{{ label(k) }}</strong>：{{ v }}</li>
    </ul>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rules = ref({})
const LABELS = {
  mutex: '互斥认领',
  ttl: '超时释放',
  fulfill: '核销',
  cooldown: '释放冷却',
  cooldown_seconds: '现行冷却（秒）',
}
const label = (k) => LABELS[k] || k
onMounted(async () => { rules.value = await api('/rules') })
</script>
