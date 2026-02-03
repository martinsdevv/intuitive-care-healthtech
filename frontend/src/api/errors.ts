import type { AxiosError } from "axios";

export function errorMessage(err: unknown): string {
  const e = err as AxiosError<any>;

  // Erro de rede / timeout
  if (!e.response) {
    if (e.code === "ECONNABORTED")
      return "Tempo de resposta excedido. Tente novamente.";
    return "Servidor indisponível ou sem conexão. Tente novamente.";
  }

  const status = e.response.status;
  const detail = (e.response.data &&
    (e.response.data.detail || e.response.data.message)) as string | undefined;

  // Mensagens específicas quando o usuário pode agir
  if (status === 422)
    return (
      detail || "Entrada inválida. Verifique os parâmetros e tente novamente."
    );
  if (status === 404) return detail || "Recurso não encontrado.";

  // Genérico para 500+ (não vazar detalhes)
  if (status >= 500) return "Erro interno. Tente novamente em instantes.";

  // Fallback
  return detail || "Falha na requisição. Tente novamente.";
}
