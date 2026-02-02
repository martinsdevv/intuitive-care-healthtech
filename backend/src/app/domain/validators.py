import re
from decimal import Decimal, InvalidOperation
from typing import Optional


def limpar_digitos(valor: str) -> str:
    return re.sub(r"\D+", "", valor or "")


def parse_decimal(valor: str) -> Optional[Decimal]:
    v = (valor or "").strip()
    if not v:
        return None

    # lida com formatos pt-br e inteiros
    v = v.replace(" ", "")
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v and "." not in v:
        v = v.replace(",", ".")

    try:
        return Decimal(v)
    except (InvalidOperation, ValueError):
        return None


def validar_cnpj(cnpj: str) -> bool:
    cnpj = limpar_digitos(cnpj)

    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False

    def calc_dv(base12: str) -> str:
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        soma = 0
        for i, p in enumerate(pesos1):
            soma += int(base12[i]) * p
        resto = soma % 11
        dv1 = "0" if resto < 2 else str(11 - resto)

        base13 = base12 + dv1
        soma = 0
        for i, p in enumerate(pesos2):
            soma += int(base13[i]) * p
        resto = soma % 11
        dv2 = "0" if resto < 2 else str(11 - resto)

        return dv1 + dv2

    base = cnpj[:12]
    dv = cnpj[12:]
    return calc_dv(base) == dv
