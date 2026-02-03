<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useOperadoras } from "../composables/useOperadoras";
import { useEstatisticas } from "../composables/useEstatisticas";
import Pagination from "../components/Pagination.vue";
import StateBlock from "../components/StateBlock.vue";
import UfChart from "../components/UfChart.vue";

const router = useRouter();
const op = useOperadoras();
const st = useEstatisticas();

const hasData = computed(() => op.data.value.length > 0);

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

function digitsOnly(v?: string | null) {
  return String(v || "").replace(/\D/g, "");
}

function fmtCNPJ(v?: string | null) {
  const s = digitsOnly(v);
  if (s.length !== 14) return v || "—";
  return `${s.slice(0, 2)}.${s.slice(2, 5)}.${s.slice(5, 8)}/${s.slice(8, 12)}-${s.slice(12)}`;
}

function goToDetalhes(cnpj?: string | null) {
  const d = digitsOnly(cnpj);
  if (!d) return;
  router.push(`/operadoras/${d}`);
}
</script>

<template>
  <div class="container">
    <header style="display:flex; align-items:flex-end; justify-content:space-between; gap:12px;">
      <div>
        <h1 class="h1">Operadoras</h1>
        <p class="muted" style="margin:6px 0 0;">
          Busca por razão social ou CNPJ + paginação server-side.
        </p>
      </div>

      <div class="badge" v-if="op.total.value >= 0">
        <strong style="color:var(--text);">{{ op.total.value.toLocaleString("pt-BR") }}</strong>
        <span>registros</span>
      </div>
    </header>

    <section style="display:grid; grid-template-columns: 1.65fr 1fr; gap:14px; margin-top:14px;">
      <!-- LISTA -->
      <div class="card">
        <div class="cardHeader">
          <div>
            <h2 class="cardTitle">Listagem</h2>
            <p class="cardSub">Digite para filtrar. </p>
          </div>
        </div>

        <div class="cardBody">
          <div style="display:flex; gap:10px; align-items:center; margin-bottom:12px;">
            <input
              class="input"
              :value="op.q.value"
              placeholder="Buscar (ex.: saúde, 04487255...)"
              @input="op.setQuery(($event.target as HTMLInputElement).value)"
            />
          </div>

          <div v-if="op.loading.value">
            <StateBlock kind="loading" title="Carregando operadoras..." />
          </div>

          <div v-else-if="op.error.value">
            <StateBlock kind="error" title="Falha ao carregar operadoras" :description="op.error.value" />
          </div>

          <div v-else-if="!hasData">
            <StateBlock kind="empty" title="Nenhuma operadora encontrada" description="Tente ajustar o filtro de busca." />
          </div>

          <div v-else>
            <div class="tableWrap">
              <table class="table table--roomy">
                <thead>
                  <tr>
                    <th style="width:64%;">Operadora</th>
                    <th style="width:22%;">CNPJ</th>
                    <th style="width:8%;">UF</th>
                    <th class="actionsCell"></th>
                  </tr>
                </thead>

                <tbody>
                  <tr
                    v-for="row in op.data.value"
                    :key="row.registro_ans"
                    class="rowLink"
                    @click="goToDetalhes(row.cnpj)"
                    title="Abrir detalhes"
                  >
                    <!-- Operadora: Razão + sublinhas (REG + Modalidade) -->
                    <td>
                      <div class="truncate" :title="row.razao_social || ''" style="font-weight:900;">
                        {{ row.razao_social || "—" }}
                      </div>

                      <div class="muted rowMeta">
                        <span>Registro ANS:</span>
                        <span class="mono">{{ row.registro_ans }}</span>

                        <span class="dot">•</span>

                        <span>Modalidade:</span>
                        <span class="truncate" style="max-width: 320px;" :title="row.modalidade || ''">
                          {{ row.modalidade || "—" }}
                        </span>
                      </div>
                    </td>

                    <!-- CNPJ -->
                    <td class="cnpjCell mono">
                      {{ fmtCNPJ(row.cnpj) }}
                    </td>

                    <!-- UF -->
                    <td>
                      <span class="pill">{{ row.uf || "—" }}</span>
                    </td>

                    <!-- Ação discreta -->
                    <td class="actionsCell" @click.stop>
                      <a
                        v-if="digitsOnly(row.cnpj)"
                        class="muted"
                        style="font-size:13px; font-weight:900; cursor:pointer;"
                        @click.prevent="goToDetalhes(row.cnpj)"
                      >
                        Ver →
                      </a>
                      <span v-else class="muted">—</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <Pagination
              :page="op.page.value"
              :limit="op.limit.value"
              :total="op.total.value"
              @update:page="(v) => (op.page.value = v)"
              @update:limit="(v) => (op.limit.value = v)"
            />
          </div>
        </div>
      </div>

      <!-- SIDEBAR -->
      <div style="display:flex; flex-direction:column; gap:14px;">
        <div v-if="st.loading.value">
          <StateBlock kind="loading" title="Carregando estatísticas..." />
        </div>

        <div v-else-if="st.error.value">
          <StateBlock kind="error" title="Falha ao carregar estatísticas" :description="st.error.value" />
        </div>

        <template v-else-if="st.stats.value">
          <UfChart :data="st.stats.value.despesas_por_uf" />

          <div class="card">
            <div class="cardHeader">
              <div>
                <h3 class="cardTitle">Resumo</h3>
                <p class="cardSub">Agregado global do dataset</p>
              </div>
            </div>

            <div class="cardBody">
              <div class="kv">
                <span>Total</span>
                <strong>{{ fmtMoney(st.stats.value.total_despesas) }}</strong>

                <span>Média</span>
                <strong>{{ fmtMoney(st.stats.value.media_despesas) }}</strong>
              </div>

              <div class="hr"></div>

              <div>
                <div style="font-weight:900; font-size:13px; margin-bottom:8px;">Top 5 operadoras</div>

                <ol style="margin:0; padding-left:18px; color:var(--muted); font-size:13px;">
                  <li
                    v-for="(it, idx) in st.stats.value.top5_operadoras || []"
                    :key="idx"
                    style="margin-bottom:10px;"
                  >
                    <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px;">
                      <span
                        style="color:var(--text); font-weight:900;"
                        class="truncate"
                        :title="it.razao_social || ''"
                      >
                        {{ it.razao_social || "—" }}
                      </span>

                      <span style="font-weight:900; color:var(--text); white-space:nowrap;">
                        {{ fmtMoney(it.total_despesas) }}
                      </span>
                    </div>

                    <div class="muted" style="font-size:12px; margin-top:6px;">
                      <a
                        v-if="digitsOnly(it.cnpj)"
                        style="font-weight:900; cursor:pointer;"
                        @click.prevent="goToDetalhes(it.cnpj)"
                      >
                        Ver detalhes →
                      </a>
                    </div>
                  </li>
                </ol>
              </div>
            </div>
          </div>
        </template>

        <div v-else>
          <StateBlock kind="empty" title="Sem estatísticas" />
        </div>
      </div>
    </section>

    <div style="height: 18px;"></div>
  </div>
</template>
