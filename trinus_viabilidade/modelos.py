"""
Trinus Viabilidade - Modelos de dados.

Enums para tipologias, padrões, regiões e dataclasses para inputs/premissas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Tipologia(str, Enum):
    LOTEAMENTO = "Loteamento"
    INCORPORACAO_VERTICAL = "Incorporação Vertical"
    INCORPORACAO_HORIZONTAL = "Incorporação Horizontal"
    MULTIPROPRIEDADE = "Multipropriedade"
    MIXED_USE = "Mixed Use"


class Padrao(str, Enum):
    ECONOMICO = "Econômico (MCMV)"
    STANDARD = "Standard"
    MEDIO = "Médio"
    MEDIO_ALTO = "Médio-Alto"
    ALTO = "Alto Padrão"
    LUXO = "Luxo"


class TipoNegociacao(str, Enum):
    PERMUTA_FISICA = "Permuta Física"
    PERMUTA_FINANCEIRA = "Permuta Financeira"
    PERMUTA_RESULTADO = "Permuta por Resultado"
    AQUISICAO = "Aquisição"


class Regiao(str, Enum):
    NORTE = "Norte"
    NORDESTE = "Nordeste"
    CENTRO_OESTE = "Centro-Oeste"
    SUDESTE = "Sudeste"
    SUL = "Sul"


class RegimeTributario(str, Enum):
    RET = "RET (Regime Especial de Tributação)"
    RET_MCMV = "RET - MCMV (1%)"
    LUCRO_PRESUMIDO = "Lucro Presumido"
    SPE_RET = "SPE com RET"


class IndiceCorrecao(str, Enum):
    INCC = "INCC"
    IPCA = "IPCA"
    IGPM = "IGP-M"


# ---------------------------------------------------------------------------
# Mapeamento de estados para regiões
# ---------------------------------------------------------------------------
ESTADO_PARA_REGIAO: dict[str, Regiao] = {
    # Norte
    "AC": Regiao.NORTE, "AM": Regiao.NORTE, "AP": Regiao.NORTE,
    "PA": Regiao.NORTE, "RO": Regiao.NORTE, "RR": Regiao.NORTE,
    "TO": Regiao.NORTE,
    # Nordeste
    "AL": Regiao.NORDESTE, "BA": Regiao.NORDESTE, "CE": Regiao.NORDESTE,
    "MA": Regiao.NORDESTE, "PB": Regiao.NORDESTE, "PE": Regiao.NORDESTE,
    "PI": Regiao.NORDESTE, "RN": Regiao.NORDESTE, "SE": Regiao.NORDESTE,
    # Centro-Oeste
    "DF": Regiao.CENTRO_OESTE, "GO": Regiao.CENTRO_OESTE,
    "MS": Regiao.CENTRO_OESTE, "MT": Regiao.CENTRO_OESTE,
    # Sudeste
    "ES": Regiao.SUDESTE, "MG": Regiao.SUDESTE,
    "RJ": Regiao.SUDESTE, "SP": Regiao.SUDESTE,
    # Sul
    "PR": Regiao.SUL, "RS": Regiao.SUL, "SC": Regiao.SUL,
}

ESTADOS_BRASIL: list[str] = sorted(ESTADO_PARA_REGIAO.keys())


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class InputsUsuario:
    """Dados mínimos informados pelo usuário."""
    tipologia: Tipologia
    estado: str
    cidade: str
    padrao: Padrao
    num_unidades: int
    tipo_negociacao: TipoNegociacao
    area_terreno_m2: Optional[float] = None
    vgv_estimado: Optional[float] = None
    area_privativa_media_m2: Optional[float] = None

    @property
    def regiao(self) -> Regiao:
        return ESTADO_PARA_REGIAO.get(self.estado, Regiao.SUDESTE)


@dataclass
class Premissa:
    """Uma premissa sugerida pelo sistema."""
    nome: str
    valor: float
    unidade: str  # Ex: "R$/m²", "%", "meses", "R$"
    valor_min: float
    valor_max: float
    fonte: str
    categoria: str  # Receita, Custo, Despesa, Financeiro
    subcategoria: str  # Ex: "Preço de Venda", "Construção", "Comercial"
    editavel: bool = True
    descricao: str = ""


@dataclass
class TabelaVendas:
    """Estrutura da tabela de vendas (condições de pagamento)."""
    entrada_pct: float  # % do valor na entrada
    parcelas_obra_pct: float  # % em parcelas durante a obra
    financiamento_pct: float  # % financiado na entrega das chaves
    num_parcelas_obra: int  # Quantidade de parcelas durante obra
    reforcos_pct: float = 0.0  # % em reforços (anuais/semestrais)


@dataclass
class ResultadoPremissas:
    """Resultado completo com todas as premissas sugeridas."""
    inputs: InputsUsuario
    premissas: list[Premissa] = field(default_factory=list)
    tabela_vendas: Optional[TabelaVendas] = None
    versao: str = "v1"

    def por_categoria(self, categoria: str) -> list[Premissa]:
        return [p for p in self.premissas if p.categoria == categoria]

    def por_subcategoria(self, subcategoria: str) -> list[Premissa]:
        return [p for p in self.premissas if p.subcategoria == subcategoria]

    def get_premissa(self, nome: str) -> Optional[Premissa]:
        for p in self.premissas:
            if p.nome == nome:
                return p
        return None

    def to_dict(self) -> dict:
        """Converte para dicionário para exportação."""
        return {
            "versao": self.versao,
            "inputs": {
                "tipologia": self.inputs.tipologia.value,
                "estado": self.inputs.estado,
                "cidade": self.inputs.cidade,
                "regiao": self.inputs.regiao.value,
                "padrao": self.inputs.padrao.value,
                "num_unidades": self.inputs.num_unidades,
                "tipo_negociacao": self.inputs.tipo_negociacao.value,
                "area_terreno_m2": self.inputs.area_terreno_m2,
                "vgv_estimado": self.inputs.vgv_estimado,
                "area_privativa_media_m2": self.inputs.area_privativa_media_m2,
            },
            "tabela_vendas": {
                "entrada_pct": self.tabela_vendas.entrada_pct,
                "parcelas_obra_pct": self.tabela_vendas.parcelas_obra_pct,
                "financiamento_pct": self.tabela_vendas.financiamento_pct,
                "num_parcelas_obra": self.tabela_vendas.num_parcelas_obra,
                "reforcos_pct": self.tabela_vendas.reforcos_pct,
            } if self.tabela_vendas else None,
            "premissas": {
                cat: [
                    {
                        "nome": p.nome,
                        "valor": p.valor,
                        "unidade": p.unidade,
                        "valor_min": p.valor_min,
                        "valor_max": p.valor_max,
                        "fonte": p.fonte,
                        "subcategoria": p.subcategoria,
                        "descricao": p.descricao,
                    }
                    for p in self.por_categoria(cat)
                ]
                for cat in ["Receita", "Custo", "Despesa", "Financeiro"]
            },
        }
