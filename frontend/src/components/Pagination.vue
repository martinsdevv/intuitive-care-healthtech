<script setup lang="ts">
const props = defineProps<{
  page: number;
  limit: number;
  total: number;
}>();

const emit = defineEmits<{
  (e: "update:page", v: number): void;
  (e: "update:limit", v: number): void;
}>();

const totalPages = () => Math.max(1, Math.ceil(props.total / props.limit));

function prev() { if (props.page > 1) emit("update:page", props.page - 1); }
function next() { if (props.page < totalPages()) emit("update:page", props.page + 1); }
function first() { if (props.page !== 1) emit("update:page", 1); }
function last() {
  const t = totalPages();
  if (props.page !== t) emit("update:page", t);
}
</script>

<template>
  <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; margin-top:12px;">
    <div style="display:flex; gap:8px; align-items:center;">
      <button class="btn" @click="first" :disabled="page <= 1">«</button>
      <button class="btn" @click="prev" :disabled="page <= 1">Anterior</button>
    </div>

    <div class="badge">
      <span>
        Página <strong style="color:var(--text);">{{ page }}</strong> de
        <strong style="color:var(--text);">{{ totalPages() }}</strong>
      </span>
      <span style="color:var(--muted);">({{ total.toLocaleString("pt-BR") }} itens)</span>
    </div>

    <div style="display:flex; gap:8px; align-items:center;">
      <select
        class="btn"
        :value="limit"
        @change="emit('update:limit', Number(($event.target as HTMLSelectElement).value))"
      >
        <option :value="10">10</option>
        <option :value="20">20</option>
        <option :value="50">50</option>
      </select>

      <button class="btn" @click="next" :disabled="page >= totalPages()">Próxima</button>
      <button class="btn" @click="last" :disabled="page >= totalPages()">»</button>
    </div>
  </div>
</template>
