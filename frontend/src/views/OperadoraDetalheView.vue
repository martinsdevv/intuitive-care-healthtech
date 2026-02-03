<script setup lang="ts">
import { onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useOperadoraDetalhe } from "../composables/useOperadoraDetalhe";
import StateBlock from "../components/StateBlock.vue";
import DespesasChart from "../components/DespesasChart.vue";

const route = useRoute();
const router = useRouter();
const cnpj = String(route.params.cnpj || "");

const model = useOperadoraDetalhe();
const hasDespesas = computed(() => model.despesas.value.length > 0);

const fmtBRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 2,
});

function fmtMoney(v: unknown) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return fmtBRL.format(n);
}

function safeNumber(v: unknown) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function fmtCNPJ(v?: string | null) {
  const s = (v || "").replace(/\D/g, "");
  if (s.length !== 14) return v || "—";
  return `${s.slice(0, 2)}.${s.slice(2, 5)}.${s.slice(5, 8)}/${s.slice(8, 12)}-${s.slice(12)}`;
}

const totalOperadora = computed(() =>
  model.despesas.value.reduce((acc, it) => acc + safeNumber(it.valor), 0)
);

const mediaOperadora = computed(() => {
  if (!model.despesas.value.length) return 0;
  return totalOperadora.value / model.despesas.value.length;
});

onMounted(() => model.fetchAll(cnpj));
</script>

<template>
  <div class="container">
    <header style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
      <div style="display:flex; align-items:center; gap:10px;">
        <button class="btn" @click="router.push('/')">← Voltar</button>
        <div>
          <h1 class="h1">Detalhes da Operadora</h1>
          <p class="muted" style="margin:6px 0 0;">
            CNPJ: <span class="mono">{{ fmtCNPJ(cnpj) }}</span>
          </p>
        </div>
      </div>

      <div class="badge" v-if="model.operadora.value?.registro_ans">
        Registro ANS:
        <strong style="color:var(--text);" class="mono">{{ model.operadora.value.registro_ans }}</strong>
      </div>
    </header>

    <div style="margin-top:14px;">
      <div v-if="model.loading.value">
        <StateBlock kind="loading" title="Carregando detalhes..." />
      </div>

      <div v-else-if="model.error.value">
        <StateBlock kind="error" title="Falha ao carregar detalhes" :description="model.error.value" />
      </div>

      <div v-else-if="!model.operadora.value">
        <StateBlock kind="empty" title="Operadora não encontrada" />
      </div>

      <div v-else style="display:grid; grid-template-columns: 1fr 1.6fr; gap:14px;">
        <!-- CADASTRO -->
        <div class="card">
          <div class="cardHeader">
            <div>
              <h3 class="cardTitle">Cadastro</h3>
              <p class="cardSub">Dados cadastrais (CADOP)</p>
            </div>
            <span class="pill">{{ model.operadora.value.uf || "—" }}</span>
          </div>

          <div class="cardBody">
            <div class="kv" style="grid-template-columns: 1fr;">
              <span>Razão social</span>
              <strong>{{ model.operadora.value.razao_social || "—" }}</strong>

              <span>Nome fantasia</span>
              <strong>{{ model.operadora.value.nome_fantasia || "—" }}</strong>

              <span>Modalidade</span>
              <strong>{{ model.operadora.value.modalidade || "—" }}</strong>

              <span>Cidade</span>
              <strong>{{ model.operadora.value.cidade || "—" }}</strong>

              <span>Endereço</span>
              <strong>
                {{ model.operadora.value.logradouro || "—" }}
                <span v-if="model.operadora.value.numero">, {{ model.operadora.value.numero }}</span>
              </strong>
            </div>

            <div class="hr"></div>

            <div class="kv">
              <span>Total no período</span>
              <strong>{{ fmtMoney(totalOperadora) }}</strong>

              <span>Média trimestral</span>
              <strong>{{ fmtMoney(mediaOperadora) }}</strong>
            </div>
          </div>
        </div>

        <!-- DESPESAS -->
        <div style="display:flex; flex-direction:column; gap:14px;">
          <div v-if="!hasDespesas">
            <StateBlock kind="empty" title="Sem despesas registradas" description="Não há histórico para esta operadora." />
          </div>

          <template v-else>
            <DespesasChart :items="model.despesas.value" />

            <div class="card">
              <div class="cardHeader">
                <div>
                  <h3 class="cardTitle">Histórico (tabela)</h3>
                  <p class="cardSub">Ordenado por ano/trimestre</p>
                </div>
              </div>

              <div class="cardBody" style="padding-top:10px;">
                <div class="tableWrap">
                  <table class="table">
                    <thead>
                      <tr>
                        <th style="width:20%;">Ano</th>
                        <th style="width:20%;">Trimestre</th>
                        <th style="width:60%; text-align:right;">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="it in model.despesas.value" :key="`${it.ano}-${it.trimestre}`">
                        <td>{{ it.ano }}</td>
                        <td><span class="pill">T{{ it.trimestre }}</span></td>
                        <td style="text-align:right; font-weight:900;">
                          {{ fmtMoney(it.valor) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <div style="height: 18px;"></div>
  </div>
</template>

<style scoped>
@media (max-width: 980px) {
  div[style*="grid-template-columns"] {
    grid-template-columns: 1fr !important;
  }
}
</style>
