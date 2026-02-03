import { ref, watch } from "vue";
import { api } from "../api/client";
import { errorMessage } from "../api/errors";

export type Operadora = {
  registro_ans: number;
  cnpj?: string | null;
  razao_social?: string | null;
  modalidade?: string | null;
  uf?: string | null;
};

export function useOperadoras() {
  const data = ref<Operadora[]>([]);
  const total = ref(0);

  const page = ref(1);
  const limit = ref(10);
  const q = ref("");

  const loading = ref(false);
  const error = ref<string | null>(null);

  let debounceTimer: number | undefined;

  async function fetchOperadoras() {
    loading.value = true;
    error.value = null;
    try {
      const resp = await api.get("/api/operadoras", {
        params: {
          page: page.value,
          limit: limit.value,
          q: q.value || undefined,
        },
      });
      data.value = resp.data.data;
      total.value = resp.data.total;
    } catch (err) {
      error.value = errorMessage(err);
      data.value = [];
      total.value = 0;
    } finally {
      loading.value = false;
    }
  }

  function setQuery(next: string) {
    q.value = next;
    page.value = 1;

    // debounce (UX melhor / reduz spam no backend)
    if (debounceTimer) window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => fetchOperadoras(), 300);
  }

  watch([page, limit], () => fetchOperadoras(), { immediate: true });

  return {
    data,
    total,
    page,
    limit,
    q,
    loading,
    error,
    fetchOperadoras,
    setQuery,
  };
}
