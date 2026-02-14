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
    # Parâmetros de negociação do terreno
    permuta_percentual: Optional[float] = None
    permuta_referencia: Optional[str] = None  # "VGV" ou "Receita"
    valor_aquisicao: Optional[float] = None

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
class CurvaVendas:
    """Distribuição das vendas por fase do empreendimento."""
    lancamento_pct: float  # % vendidas no lançamento
    obra_pct: float  # % vendidas durante obra
    pos_obra_pct: float  # % vendidas pós-obra


@dataclass
class TabelaVendasIncorporacao:
    """Tabela de vendas para Incorporação (Vertical, Horizontal, Multi, Mixed Use).

    Modelo: Entrada + Parcelas durante obra + Financiamento bancário na entrega
    Indexação pré-chaves: INCC | Pós-chaves: IGP-M
    """
    entrada_pct: float  # % do valor na entrada (ato + sinal)
    parcelas_obra_pct: float  # % em mensais durante a obra
    financiamento_pct: float  # % financiado na entrega das chaves (repasse bancário)
    reforcos_pct: float  # % em reforços (anuais/semestrais)
    num_parcelas_obra: int  # Quantidade de parcelas mensais durante obra
    indexador_pre_chaves: str = "INCC"  # Correção antes da entrega
    indexador_pos_chaves: str = "IGPM"  # Correção após entrega


@dataclass
class TabelaVendasLoteamento:
    """Tabela de vendas para Loteamento / Urbanismo.

    Modelo: Entrada (sinal) + Parcelamento longo (Gradiente, Price ou SAC)
    Parcelas: tipicamente 120x a 240x
    Juros embutidos: 0,5% a 1,0% a.m. (tabela Price) ou decrescente (Gradiente)
    Indexação: IPCA ou IGP-M
    Não há financiamento bancário na entrega (o próprio loteador financia).
    """
    entrada_pct: float  # % do valor na entrada (sinal, em 1 a 6 parcelas)
    saldo_parcelado_pct: float  # % restante parcelado (normalmente 100 - entrada)
    num_parcelas: int  # Total de parcelas (120, 150, 180, 200, 220, 240)
    sistema_amortizacao: str  # "Price", "Gradiente" ou "SAC"
    juros_am: float  # Taxa de juros ao mês (% a.m.) - ex: 0.75
    indexador: str  # Indexador de correção monetária: "IPCA" ou "IGPM"
    intermediarias_pct: float = 0.0  # % em parcelas intermediárias (semestrais/anuais)
    num_parcelas_entrada: int = 3  # Qtd de parcelas para pagar a entrada


# Alias para compatibilidade
TabelaVendas = TabelaVendasIncorporacao


@dataclass
class ResultadoPremissas:
    """Resultado completo com todas as premissas sugeridas."""
    inputs: InputsUsuario
    premissas: list[Premissa] = field(default_factory=list)
    tabela_vendas: Optional[TabelaVendasIncorporacao] = None
    tabela_vendas_loteamento: Optional[TabelaVendasLoteamento] = None
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

    @property
    def e_loteamento(self) -> bool:
        return self.inputs.tipologia == Tipologia.LOTEAMENTO

    def _tabela_vendas_dict(self) -> dict | None:
        if self.tabela_vendas_loteamento:
            tv = self.tabela_vendas_loteamento
            return {
                "tipo": "Loteamento",
                "entrada_pct": tv.entrada_pct,
                "num_parcelas_entrada": tv.num_parcelas_entrada,
                "saldo_parcelado_pct": tv.saldo_parcelado_pct,
                "num_parcelas": tv.num_parcelas,
                "sistema_amortizacao": tv.sistema_amortizacao,
                "juros_am": tv.juros_am,
                "indexador": tv.indexador,
                "intermediarias_pct": tv.intermediarias_pct,
            }
        if self.tabela_vendas:
            tv = self.tabela_vendas
            return {
                "tipo": "Incorporação",
                "entrada_pct": tv.entrada_pct,
                "parcelas_obra_pct": tv.parcelas_obra_pct,
                "financiamento_pct": tv.financiamento_pct,
                "num_parcelas_obra": tv.num_parcelas_obra,
                "reforcos_pct": tv.reforcos_pct,
                "indexador_pre_chaves": tv.indexador_pre_chaves,
                "indexador_pos_chaves": tv.indexador_pos_chaves,
            }
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
                "permuta_percentual": self.inputs.permuta_percentual,
                "permuta_referencia": self.inputs.permuta_referencia,
                "valor_aquisicao": self.inputs.valor_aquisicao,
            },
            "tabela_vendas": self._tabela_vendas_dict(),
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
                for cat in sorted({p.categoria for p in self.premissas})
            },
        }
