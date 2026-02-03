<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch, computed } from "vue";
import Chart from "chart.js/auto";

const props = defineProps<{
  data: Record<string, number>;
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
let chart: Chart | null = null;

const TOP_N = 15;

const fmtCompact = new Intl.NumberFormat("pt-BR", {
  notation: "compact",
  compactDisplay: "short",
  maximumFractionDigits: 1,
});

const fmtBRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 2,
});

const meta = computed(() => {
  const all = Object.entries(props.data || {})
    .map(([uf, v]) => ({ uf, v: Number(v || 0) }))
    .sort((a, b) => b.v - a.v);

  const sliced = all.slice(0, TOP_N);
  return {
    allCount: all.length,
    shownCount: sliced.length,
    labels: sliced.map((e) => e.uf),
    values: sliced.map((e) => e.v),
  };
});

function render() {
  if (!canvasRef.value) return;

  chart?.destroy();
  chart = new Chart(canvasRef.value, {
    type: "bar",
    data: {
      labels: meta.value.labels,
      datasets: [
        {
          label: "Despesas por UF",
          data: meta.value.values,
          borderWidth: 1,
          maxBarThickness: 14,
          categoryPercentage: 0.9,
          barPercentage: 0.9,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => fmtBRL.format(Number(ctx.parsed.x || 0)),
          },
        },
      },
      scales: {
        x: {
          ticks: {
            callback: (v) => fmtCompact.format(Number(v)),
          },
          grid: { color: "rgba(17,24,39,0.06)" },
        },
        y: {
          grid: { display: false },
        },
      },
    },
  });
}

watch(() => props.data, render, { deep: true });
onMounted(render);
onBeforeUnmount(() => chart?.destroy());
</script>

<template>
  <div class="card">
    <div class="cardHeader">
      <div>
        <h3 class="cardTitle">Distribuição de despesas por UF</h3>
        <p class="cardSub">
          Ordenado do maior para o menor
          <span v-if="meta.allCount > meta.shownCount">
            (mostrando Top {{ meta.shownCount }} de {{ meta.allCount }})
          </span>
        </p>
      </div>
    </div>

    <div class="cardBody" style="height: 420px;">
      <canvas ref="canvasRef"></canvas>
    </div>
  </div>
</template>
