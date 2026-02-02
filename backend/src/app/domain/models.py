from dataclasses import dataclass


@dataclass(frozen=True)
class CadopRegistro:
    registroAns: str
    cnpj: str
    razaoSocial: str
    modalidade: str
    uf: str
