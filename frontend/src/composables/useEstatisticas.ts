import { ref, onMounted } from "vue";
import { api } from "../api/client";
import { errorMessage } from "../api/errors";

export type Estatisticas = {
  total_despesas: number;
  media_despesas: number;
  top5_operadoras: Array<{
    cnpj?: string | null;
    razao_social?: string | null;
    total_despesas: number;
  }>;
  despesas_por_uf: Record<string, number>;
};

export function useEstatisticas() {
  const stats = ref<Estatisticas | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchStats() {
    loading.value = true;
    error.value = null;
    try {
      const resp = await api.get("/api/estatisticas");
      stats.value = resp.data;
    } catch (err) {
      error.value = errorMessage(err);
      stats.value = null;
    } finally {
      loading.value = false;
    }
  }

  onMounted(fetchStats);

  return { stats, loading, error, fetchStats };
}
