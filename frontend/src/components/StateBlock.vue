<script setup lang="ts">
const props = defineProps<{
  title: string;
  description?: string;
  kind: "loading" | "error" | "empty";
}>();

const meta = {
  loading: { label: "Carregando", bg: "#ecfeff", bd: "rgba(14,165,164,.22)", fg: "#0b6d6d" },
  error: { label: "Erro", bg: "#fef2f2", bd: "rgba(220,38,38,.20)", fg: "#b91c1c" },
  empty: { label: "Vazio", bg: "rgba(15,23,42,0.03)", bd: "rgba(15,23,42,0.08)", fg: "#334155" },
} as const;
</script>

<template>
  <div class="card" style="box-shadow:none;">
    <div class="cardBody">
      <div
        class="badge"
        :style="{ background: meta[kind].bg, borderColor: meta[kind].bd, color: meta[kind].fg }"
      >
        <strong style="color:inherit;">{{ meta[kind].label }}</strong>
      </div>

      <h3 class="cardTitle" style="margin-top:10px; font-size:13px;">{{ title }}</h3>

      <p v-if="description" class="muted" style="margin:8px 0 0;">
        {{ description }}
      </p>
    </div>
  </div>
</template>
