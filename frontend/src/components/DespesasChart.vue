<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Chart from "chart.js/auto";

type Item = { ano: number; trimestre: number; valor: number };
const props = defineProps<{ items: Item[] }>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
let chart: Chart | null = null;

const ordered = computed(() =>
  [...(props.items || [])].sort((a, b) => a.ano - b.ano || a.trimestre - b.trimestre)
);

const fmtBRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 2,
});

const fmtCompact = new Intl.NumberFormat("pt-BR", {
  notation: "compact",
  compactDisplay: "short",
  maximumFractionDigits: 1,
});

function render() {
  if (!canvasRef.value) return;

  const labels = ordered.value.map((i) => `${i.ano} T${i.trimestre}`);
  const values = ordered.value.map((i) => Number(i.valor || 0));

  chart?.destroy();
  chart = new Chart(canvasRef.value, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Despesa trimestral",
          data: values,
          tension: 0.25,
          pointRadius: 3,
          pointHoverRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => fmtBRL.format(Number(ctx.parsed.y || 0)),
          },
        },
      },
      scales: {
        y: {
          ticks: {
            callback: (v) => fmtCompact.format(Number(v)),
          },
          grid: { color: "rgba(17,24,39,0.06)" },
        },
        x: {
          grid: { display: false },
        },
      },
    },
  });
}

watch(() => props.items, render, { deep: true });
onMounted(render);
onBeforeUnmount(() => chart?.destroy());
</script>

<template>
  <div class="card">
    <div class="cardHeader">
      <div>
        <h3 class="cardTitle">Histórico de despesas</h3>
        <p class="cardSub">Linha trimestral por período</p>
      </div>
    </div>

    <div class="cardBody" style="height: 320px;">
      <canvas ref="canvasRef"></canvas>
    </div>
  </div>
</template>
