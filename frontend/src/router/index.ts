import { createRouter, createWebHistory } from "vue-router";
import OperadorasView from "../views/OperadorasView.vue";
import OperadoraDetalheView from "../views/OperadoraDetalheView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "operadoras", component: OperadorasView },
    {
      path: "/operadoras/:cnpj",
      name: "operadora",
      component: OperadoraDetalheView,
      props: true,
    },
  ],
});

export default router;
