import { ref } from "vue";
import { api } from "../api/client";
import { errorMessage } from "../api/errors";

export type OperadoraDetalhe = {
  registro_ans: number;
  cnpj?: string | null;
  razao_social?: string | null;
  nome_fantasia?: string | null;
  modalidade?: string | null;
  uf?: string | null;
  cidade?: string | null;
};

export type DespesaItem = {
  ano: number;
  trimestre: number;
  valor: number;
};

export function useOperadoraDetalhe() {
  const operadora = ref<OperadoraDetalhe | null>(null);
  const despesas = ref<DespesaItem[]>([]);

  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchAll(cnpj: string) {
    loading.value = true;
    error.value = null;
    operadora.value = null;
    despesas.value = [];

    try {
      const [op, dep] = await Promise.all([
        api.get(`/api/operadoras/${cnpj}`),
        api.get(`/api/operadoras/${cnpj}/despesas`),
      ]);
      operadora.value = op.data;
      despesas.value = dep.data.items;
    } catch (err) {
      error.value = errorMessage(err);
    } finally {
      loading.value = false;
    }
  }

  return { operadora, despesas, loading, error, fetchAll };
}
