"""
Trinus Viabilidade - Dados de referência de mercado.

Tabelas hardcoded com benchmarks do mercado imobiliário brasileiro.
Fontes: CUB/SINAPI, SECOVI, CBIC, Abrainc, FipeZap (referências 2024/2025).

Estrutura: Dicionários indexados por (Região, Padrão) ou (Tipologia, Padrão).
Cada entrada contém: valor médio, mínimo, máximo.
"""

from modelos import Regiao, Padrao, Tipologia, TipoNegociacao

# ==========================================================================
# CUB - Custo Unitário Básico da Construção (R$/m²)
# Referência: SINDUSCON regionais, base 2024/2025
# ==========================================================================
CUB_POR_REGIAO: dict[Regiao, dict[Padrao, dict]] = {
    Regiao.NORTE: {
        Padrao.ECONOMICO:  {"medio": 1_850, "min": 1_600, "max": 2_100},
        Padrao.STANDARD:   {"medio": 2_100, "min": 1_850, "max": 2_350},
        Padrao.MEDIO:      {"medio": 2_400, "min": 2_100, "max": 2_700},
        Padrao.MEDIO_ALTO: {"medio": 2_750, "min": 2_400, "max": 3_100},
        Padrao.ALTO:       {"medio": 3_200, "min": 2_800, "max": 3_600},
        Padrao.LUXO:       {"medio": 3_800, "min": 3_300, "max": 4_500},
    },
    Regiao.NORDESTE: {
        Padrao.ECONOMICO:  {"medio": 1_800, "min": 1_550, "max": 2_050},
        Padrao.STANDARD:   {"medio": 2_050, "min": 1_800, "max": 2_300},
        Padrao.MEDIO:      {"medio": 2_350, "min": 2_050, "max": 2_650},
        Padrao.MEDIO_ALTO: {"medio": 2_700, "min": 2_350, "max": 3_050},
        Padrao.ALTO:       {"medio": 3_100, "min": 2_700, "max": 3_500},
        Padrao.LUXO:       {"medio": 3_700, "min": 3_200, "max": 4_400},
    },
    Regiao.CENTRO_OESTE: {
        Padrao.ECONOMICO:  {"medio": 2_000, "min": 1_750, "max": 2_250},
        Padrao.STANDARD:   {"medio": 2_250, "min": 2_000, "max": 2_500},
        Padrao.MEDIO:      {"medio": 2_600, "min": 2_250, "max": 2_950},
        Padrao.MEDIO_ALTO: {"medio": 3_000, "min": 2_600, "max": 3_400},
        Padrao.ALTO:       {"medio": 3_500, "min": 3_000, "max": 4_000},
        Padrao.LUXO:       {"medio": 4_200, "min": 3_600, "max": 5_000},
    },
    Regiao.SUDESTE: {
        Padrao.ECONOMICO:  {"medio": 2_200, "min": 1_900, "max": 2_500},
        Padrao.STANDARD:   {"medio": 2_500, "min": 2_200, "max": 2_800},
        Padrao.MEDIO:      {"medio": 2_900, "min": 2_500, "max": 3_300},
        Padrao.MEDIO_ALTO: {"medio": 3_400, "min": 2_900, "max": 3_900},
        Padrao.ALTO:       {"medio": 4_000, "min": 3_400, "max": 4_600},
        Padrao.LUXO:       {"medio": 5_000, "min": 4_200, "max": 6_000},
    },
    Regiao.SUL: {
        Padrao.ECONOMICO:  {"medio": 2_100, "min": 1_850, "max": 2_350},
        Padrao.STANDARD:   {"medio": 2_400, "min": 2_100, "max": 2_700},
        Padrao.MEDIO:      {"medio": 2_750, "min": 2_400, "max": 3_100},
        Padrao.MEDIO_ALTO: {"medio": 3_200, "min": 2_750, "max": 3_650},
        Padrao.ALTO:       {"medio": 3_800, "min": 3_200, "max": 4_400},
        Padrao.LUXO:       {"medio": 4_600, "min": 3_900, "max": 5_500},
    },
}


# ==========================================================================
# Preço médio de venda por m² (R$/m² de área privativa)
# Referência: FipeZap, DataZap, pesquisas regionais 2024/2025
# ==========================================================================
PRECO_VENDA_M2: dict[Regiao, dict[Padrao, dict]] = {
    Regiao.NORTE: {
        Padrao.ECONOMICO:  {"medio": 3_500, "min": 2_800, "max": 4_200},
        Padrao.STANDARD:   {"medio": 4_500, "min": 3_800, "max": 5_500},
        Padrao.MEDIO:      {"medio": 6_000, "min": 5_000, "max": 7_500},
        Padrao.MEDIO_ALTO: {"medio": 8_000, "min": 6_500, "max": 10_000},
        Padrao.ALTO:       {"medio": 11_000, "min": 8_500, "max": 14_000},
        Padrao.LUXO:       {"medio": 16_000, "min": 12_000, "max": 22_000},
    },
    Regiao.NORDESTE: {
        Padrao.ECONOMICO:  {"medio": 3_800, "min": 3_000, "max": 4_500},
        Padrao.STANDARD:   {"medio": 5_000, "min": 4_000, "max": 6_000},
        Padrao.MEDIO:      {"medio": 6_500, "min": 5_500, "max": 8_000},
        Padrao.MEDIO_ALTO: {"medio": 9_000, "min": 7_000, "max": 11_500},
        Padrao.ALTO:       {"medio": 13_000, "min": 10_000, "max": 17_000},
        Padrao.LUXO:       {"medio": 20_000, "min": 15_000, "max": 28_000},
    },
    Regiao.CENTRO_OESTE: {
        Padrao.ECONOMICO:  {"medio": 3_800, "min": 3_200, "max": 4_500},
        Padrao.STANDARD:   {"medio": 5_200, "min": 4_200, "max": 6_500},
        Padrao.MEDIO:      {"medio": 7_000, "min": 5_800, "max": 8_500},
        Padrao.MEDIO_ALTO: {"medio": 9_500, "min": 7_500, "max": 12_000},
        Padrao.ALTO:       {"medio": 13_500, "min": 10_500, "max": 17_000},
        Padrao.LUXO:       {"medio": 20_000, "min": 15_000, "max": 28_000},
    },
    Regiao.SUDESTE: {
        Padrao.ECONOMICO:  {"medio": 4_500, "min": 3_500, "max": 5_500},
        Padrao.STANDARD:   {"medio": 6_000, "min": 5_000, "max": 7_500},
        Padrao.MEDIO:      {"medio": 8_500, "min": 7_000, "max": 10_500},
        Padrao.MEDIO_ALTO: {"medio": 12_000, "min": 9_500, "max": 15_000},
        Padrao.ALTO:       {"medio": 17_000, "min": 13_000, "max": 22_000},
        Padrao.LUXO:       {"medio": 28_000, "min": 20_000, "max": 45_000},
    },
    Regiao.SUL: {
        Padrao.ECONOMICO:  {"medio": 4_200, "min": 3_500, "max": 5_000},
        Padrao.STANDARD:   {"medio": 5_500, "min": 4_500, "max": 7_000},
        Padrao.MEDIO:      {"medio": 7_500, "min": 6_000, "max": 9_500},
        Padrao.MEDIO_ALTO: {"medio": 10_500, "min": 8_500, "max": 13_000},
        Padrao.ALTO:       {"medio": 15_000, "min": 11_500, "max": 19_000},
        Padrao.LUXO:       {"medio": 24_000, "min": 18_000, "max": 35_000},
    },
}

# ==========================================================================
# Preço médio de venda por m² para LOTEAMENTOS (R$/m² de terreno)
# Referência: Pesquisas de mercado, Abrainc, SECOVI 2024/2025
# ==========================================================================
PRECO_LOTE_M2: dict[Regiao, dict[Padrao, dict]] = {
    Regiao.NORTE: {
        Padrao.ECONOMICO:  {"medio": 350, "min": 200, "max": 500},
        Padrao.STANDARD:   {"medio": 550, "min": 350, "max": 750},
        Padrao.MEDIO:      {"medio": 800, "min": 550, "max": 1_100},
        Padrao.MEDIO_ALTO: {"medio": 1_200, "min": 850, "max": 1_600},
        Padrao.ALTO:       {"medio": 1_800, "min": 1_200, "max": 2_500},
        Padrao.LUXO:       {"medio": 2_800, "min": 1_800, "max": 4_000},
    },
    Regiao.NORDESTE: {
        Padrao.ECONOMICO:  {"medio": 400, "min": 250, "max": 600},
        Padrao.STANDARD:   {"medio": 650, "min": 400, "max": 900},
        Padrao.MEDIO:      {"medio": 950, "min": 650, "max": 1_300},
        Padrao.MEDIO_ALTO: {"medio": 1_400, "min": 1_000, "max": 1_900},
        Padrao.ALTO:       {"medio": 2_200, "min": 1_500, "max": 3_000},
        Padrao.LUXO:       {"medio": 3_500, "min": 2_500, "max": 5_000},
    },
    Regiao.CENTRO_OESTE: {
        Padrao.ECONOMICO:  {"medio": 450, "min": 300, "max": 650},
        Padrao.STANDARD:   {"medio": 700, "min": 450, "max": 1_000},
        Padrao.MEDIO:      {"medio": 1_050, "min": 700, "max": 1_400},
        Padrao.MEDIO_ALTO: {"medio": 1_500, "min": 1_050, "max": 2_000},
        Padrao.ALTO:       {"medio": 2_500, "min": 1_700, "max": 3_500},
        Padrao.LUXO:       {"medio": 4_000, "min": 2_800, "max": 5_500},
    },
    Regiao.SUDESTE: {
        Padrao.ECONOMICO:  {"medio": 550, "min": 350, "max": 800},
        Padrao.STANDARD:   {"medio": 850, "min": 550, "max": 1_200},
        Padrao.MEDIO:      {"medio": 1_300, "min": 850, "max": 1_800},
        Padrao.MEDIO_ALTO: {"medio": 2_000, "min": 1_400, "max": 2_800},
        Padrao.ALTO:       {"medio": 3_200, "min": 2_200, "max": 4_500},
        Padrao.LUXO:       {"medio": 5_500, "min": 3_500, "max": 8_000},
    },
    Regiao.SUL: {
        Padrao.ECONOMICO:  {"medio": 500, "min": 300, "max": 700},
        Padrao.STANDARD:   {"medio": 780, "min": 500, "max": 1_100},
        Padrao.MEDIO:      {"medio": 1_150, "min": 780, "max": 1_600},
        Padrao.MEDIO_ALTO: {"medio": 1_750, "min": 1_200, "max": 2_400},
        Padrao.ALTO:       {"medio": 2_800, "min": 1_900, "max": 3_800},
        Padrao.LUXO:       {"medio": 4_500, "min": 3_000, "max": 6_500},
    },
}


# ==========================================================================
# Velocidade de vendas (% do estoque vendido por mês)
# Referência: SECOVI, Abrainc, CBIC 2024
# ==========================================================================
VELOCIDADE_VENDAS: dict[Tipologia, dict[Padrao, dict]] = {
    Tipologia.LOTEAMENTO: {
        Padrao.ECONOMICO:  {"medio": 6.0, "min": 4.0, "max": 10.0},
        Padrao.STANDARD:   {"medio": 5.0, "min": 3.0, "max": 8.0},
        Padrao.MEDIO:      {"medio": 4.0, "min": 2.5, "max": 6.5},
        Padrao.MEDIO_ALTO: {"medio": 3.5, "min": 2.0, "max": 5.5},
        Padrao.ALTO:       {"medio": 3.0, "min": 1.5, "max": 5.0},
        Padrao.LUXO:       {"medio": 2.0, "min": 1.0, "max": 3.5},
    },
    Tipologia.INCORPORACAO_VERTICAL: {
        Padrao.ECONOMICO:  {"medio": 5.0, "min": 3.5, "max": 8.0},
        Padrao.STANDARD:   {"medio": 4.0, "min": 2.5, "max": 6.0},
        Padrao.MEDIO:      {"medio": 3.0, "min": 2.0, "max": 5.0},
        Padrao.MEDIO_ALTO: {"medio": 2.5, "min": 1.5, "max": 4.0},
        Padrao.ALTO:       {"medio": 2.0, "min": 1.0, "max": 3.5},
        Padrao.LUXO:       {"medio": 1.5, "min": 0.8, "max": 2.5},
    },
    Tipologia.INCORPORACAO_HORIZONTAL: {
        Padrao.ECONOMICO:  {"medio": 5.5, "min": 3.5, "max": 8.5},
        Padrao.STANDARD:   {"medio": 4.5, "min": 3.0, "max": 7.0},
        Padrao.MEDIO:      {"medio": 3.5, "min": 2.0, "max": 5.5},
        Padrao.MEDIO_ALTO: {"medio": 3.0, "min": 1.5, "max": 4.5},
        Padrao.ALTO:       {"medio": 2.5, "min": 1.0, "max": 4.0},
        Padrao.LUXO:       {"medio": 1.5, "min": 0.8, "max": 3.0},
    },
    Tipologia.MULTIPROPRIEDADE: {
        Padrao.ECONOMICO:  {"medio": 8.0, "min": 5.0, "max": 12.0},
        Padrao.STANDARD:   {"medio": 7.0, "min": 4.0, "max": 10.0},
        Padrao.MEDIO:      {"medio": 6.0, "min": 3.5, "max": 9.0},
        Padrao.MEDIO_ALTO: {"medio": 5.0, "min": 3.0, "max": 8.0},
        Padrao.ALTO:       {"medio": 4.0, "min": 2.5, "max": 6.5},
        Padrao.LUXO:       {"medio": 3.0, "min": 1.5, "max": 5.0},
    },
    Tipologia.MIXED_USE: {
        Padrao.ECONOMICO:  {"medio": 4.0, "min": 2.5, "max": 6.0},
        Padrao.STANDARD:   {"medio": 3.5, "min": 2.0, "max": 5.0},
        Padrao.MEDIO:      {"medio": 3.0, "min": 1.5, "max": 4.5},
        Padrao.MEDIO_ALTO: {"medio": 2.5, "min": 1.5, "max": 4.0},
        Padrao.ALTO:       {"medio": 2.0, "min": 1.0, "max": 3.0},
        Padrao.LUXO:       {"medio": 1.5, "min": 0.8, "max": 2.5},
    },
}


# ==========================================================================
# Tabela de vendas típica (condições de pagamento)
# Referência: Práticas de mercado por tipologia e padrão
# ==========================================================================
TABELA_VENDAS: dict[Tipologia, dict[Padrao, dict]] = {
    Tipologia.LOTEAMENTO: {
        Padrao.ECONOMICO:  {"entrada": 10, "parcelas_obra": 60, "financiamento": 30, "reforcos": 0, "num_parcelas": 120},
        Padrao.STANDARD:   {"entrada": 10, "parcelas_obra": 55, "financiamento": 30, "reforcos": 5, "num_parcelas": 100},
        Padrao.MEDIO:      {"entrada": 15, "parcelas_obra": 50, "financiamento": 30, "reforcos": 5, "num_parcelas": 80},
        Padrao.MEDIO_ALTO: {"entrada": 20, "parcelas_obra": 45, "financiamento": 30, "reforcos": 5, "num_parcelas": 60},
        Padrao.ALTO:       {"entrada": 20, "parcelas_obra": 40, "financiamento": 30, "reforcos": 10, "num_parcelas": 48},
        Padrao.LUXO:       {"entrada": 30, "parcelas_obra": 35, "financiamento": 25, "reforcos": 10, "num_parcelas": 36},
    },
    Tipologia.INCORPORACAO_VERTICAL: {
        Padrao.ECONOMICO:  {"entrada": 10, "parcelas_obra": 20, "financiamento": 70, "reforcos": 0, "num_parcelas": 30},
        Padrao.STANDARD:   {"entrada": 15, "parcelas_obra": 20, "financiamento": 60, "reforcos": 5, "num_parcelas": 30},
        Padrao.MEDIO:      {"entrada": 20, "parcelas_obra": 20, "financiamento": 50, "reforcos": 10, "num_parcelas": 30},
        Padrao.MEDIO_ALTO: {"entrada": 20, "parcelas_obra": 25, "financiamento": 45, "reforcos": 10, "num_parcelas": 36},
        Padrao.ALTO:       {"entrada": 25, "parcelas_obra": 30, "financiamento": 35, "reforcos": 10, "num_parcelas": 36},
        Padrao.LUXO:       {"entrada": 30, "parcelas_obra": 35, "financiamento": 25, "reforcos": 10, "num_parcelas": 36},
    },
    Tipologia.INCORPORACAO_HORIZONTAL: {
        Padrao.ECONOMICO:  {"entrada": 10, "parcelas_obra": 20, "financiamento": 70, "reforcos": 0, "num_parcelas": 24},
        Padrao.STANDARD:   {"entrada": 15, "parcelas_obra": 20, "financiamento": 60, "reforcos": 5, "num_parcelas": 24},
        Padrao.MEDIO:      {"entrada": 20, "parcelas_obra": 25, "financiamento": 50, "reforcos": 5, "num_parcelas": 24},
        Padrao.MEDIO_ALTO: {"entrada": 20, "parcelas_obra": 25, "financiamento": 45, "reforcos": 10, "num_parcelas": 30},
        Padrao.ALTO:       {"entrada": 25, "parcelas_obra": 30, "financiamento": 35, "reforcos": 10, "num_parcelas": 30},
        Padrao.LUXO:       {"entrada": 30, "parcelas_obra": 35, "financiamento": 25, "reforcos": 10, "num_parcelas": 30},
    },
    Tipologia.MULTIPROPRIEDADE: {
        Padrao.ECONOMICO:  {"entrada": 10, "parcelas_obra": 50, "financiamento": 40, "reforcos": 0, "num_parcelas": 48},
        Padrao.STANDARD:   {"entrada": 15, "parcelas_obra": 45, "financiamento": 35, "reforcos": 5, "num_parcelas": 48},
        Padrao.MEDIO:      {"entrada": 15, "parcelas_obra": 45, "financiamento": 35, "reforcos": 5, "num_parcelas": 60},
        Padrao.MEDIO_ALTO: {"entrada": 20, "parcelas_obra": 40, "financiamento": 30, "reforcos": 10, "num_parcelas": 60},
        Padrao.ALTO:       {"entrada": 25, "parcelas_obra": 35, "financiamento": 30, "reforcos": 10, "num_parcelas": 48},
        Padrao.LUXO:       {"entrada": 30, "parcelas_obra": 30, "financiamento": 25, "reforcos": 15, "num_parcelas": 36},
    },
    Tipologia.MIXED_USE: {
        Padrao.ECONOMICO:  {"entrada": 10, "parcelas_obra": 25, "financiamento": 65, "reforcos": 0, "num_parcelas": 30},
        Padrao.STANDARD:   {"entrada": 15, "parcelas_obra": 25, "financiamento": 55, "reforcos": 5, "num_parcelas": 30},
        Padrao.MEDIO:      {"entrada": 20, "parcelas_obra": 25, "financiamento": 45, "reforcos": 10, "num_parcelas": 30},
        Padrao.MEDIO_ALTO: {"entrada": 20, "parcelas_obra": 25, "financiamento": 45, "reforcos": 10, "num_parcelas": 36},
        Padrao.ALTO:       {"entrada": 25, "parcelas_obra": 30, "financiamento": 35, "reforcos": 10, "num_parcelas": 36},
        Padrao.LUXO:       {"entrada": 30, "parcelas_obra": 30, "financiamento": 25, "reforcos": 15, "num_parcelas": 36},
    },
}


# ==========================================================================
# Prazo de obra estimado (meses)
# Referência: CBIC, práticas de mercado
# ==========================================================================
PRAZO_OBRA: dict[Tipologia, dict[Padrao, dict]] = {
    Tipologia.LOTEAMENTO: {
        Padrao.ECONOMICO:  {"medio": 18, "min": 12, "max": 24},
        Padrao.STANDARD:   {"medio": 20, "min": 15, "max": 28},
        Padrao.MEDIO:      {"medio": 24, "min": 18, "max": 30},
        Padrao.MEDIO_ALTO: {"medio": 24, "min": 18, "max": 32},
        Padrao.ALTO:       {"medio": 28, "min": 20, "max": 36},
        Padrao.LUXO:       {"medio": 30, "min": 24, "max": 40},
    },
    Tipologia.INCORPORACAO_VERTICAL: {
        Padrao.ECONOMICO:  {"medio": 24, "min": 18, "max": 30},
        Padrao.STANDARD:   {"medio": 28, "min": 22, "max": 34},
        Padrao.MEDIO:      {"medio": 30, "min": 24, "max": 38},
        Padrao.MEDIO_ALTO: {"medio": 34, "min": 28, "max": 42},
        Padrao.ALTO:       {"medio": 38, "min": 30, "max": 48},
        Padrao.LUXO:       {"medio": 42, "min": 34, "max": 54},
    },
    Tipologia.INCORPORACAO_HORIZONTAL: {
        Padrao.ECONOMICO:  {"medio": 18, "min": 14, "max": 24},
        Padrao.STANDARD:   {"medio": 22, "min": 16, "max": 28},
        Padrao.MEDIO:      {"medio": 24, "min": 18, "max": 32},
        Padrao.MEDIO_ALTO: {"medio": 28, "min": 22, "max": 36},
        Padrao.ALTO:       {"medio": 32, "min": 24, "max": 40},
        Padrao.LUXO:       {"medio": 36, "min": 28, "max": 48},
    },
    Tipologia.MULTIPROPRIEDADE: {
        Padrao.ECONOMICO:  {"medio": 24, "min": 18, "max": 30},
        Padrao.STANDARD:   {"medio": 28, "min": 22, "max": 36},
        Padrao.MEDIO:      {"medio": 30, "min": 24, "max": 38},
        Padrao.MEDIO_ALTO: {"medio": 34, "min": 28, "max": 42},
        Padrao.ALTO:       {"medio": 38, "min": 30, "max": 48},
        Padrao.LUXO:       {"medio": 42, "min": 34, "max": 54},
    },
    Tipologia.MIXED_USE: {
        Padrao.ECONOMICO:  {"medio": 28, "min": 22, "max": 34},
        Padrao.STANDARD:   {"medio": 30, "min": 24, "max": 38},
        Padrao.MEDIO:      {"medio": 34, "min": 28, "max": 42},
        Padrao.MEDIO_ALTO: {"medio": 38, "min": 30, "max": 46},
        Padrao.ALTO:       {"medio": 42, "min": 34, "max": 52},
        Padrao.LUXO:       {"medio": 48, "min": 38, "max": 60},
    },
}


# ==========================================================================
# Custo de infraestrutura para loteamentos (R$/m² de área total)
# Referência: AELO, SECOVI, experiência de mercado
# ==========================================================================
CUSTO_INFRAESTRUTURA_LOTE: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 80,  "min": 55,  "max": 110},
    Padrao.STANDARD:   {"medio": 110, "min": 80,  "max": 150},
    Padrao.MEDIO:      {"medio": 150, "min": 110, "max": 200},
    Padrao.MEDIO_ALTO: {"medio": 200, "min": 150, "max": 270},
    Padrao.ALTO:       {"medio": 280, "min": 200, "max": 380},
    Padrao.LUXO:       {"medio": 400, "min": 300, "max": 550},
}


# ==========================================================================
# Custo do terreno como % do VGV (referência por tipo de negociação)
# Referência: Práticas de mercado
# ==========================================================================
CUSTO_TERRENO_PCT_VGV: dict[TipoNegociacao, dict[Padrao, dict]] = {
    TipoNegociacao.AQUISICAO: {
        Padrao.ECONOMICO:  {"medio": 10, "min": 7,  "max": 14},
        Padrao.STANDARD:   {"medio": 12, "min": 8,  "max": 16},
        Padrao.MEDIO:      {"medio": 14, "min": 10, "max": 18},
        Padrao.MEDIO_ALTO: {"medio": 16, "min": 12, "max": 22},
        Padrao.ALTO:       {"medio": 18, "min": 14, "max": 25},
        Padrao.LUXO:       {"medio": 22, "min": 16, "max": 30},
    },
    TipoNegociacao.PERMUTA_FISICA: {
        Padrao.ECONOMICO:  {"medio": 12, "min": 8,  "max": 16},
        Padrao.STANDARD:   {"medio": 14, "min": 10, "max": 18},
        Padrao.MEDIO:      {"medio": 16, "min": 12, "max": 22},
        Padrao.MEDIO_ALTO: {"medio": 18, "min": 14, "max": 25},
        Padrao.ALTO:       {"medio": 22, "min": 16, "max": 28},
        Padrao.LUXO:       {"medio": 25, "min": 18, "max": 32},
    },
    TipoNegociacao.PERMUTA_FINANCEIRA: {
        Padrao.ECONOMICO:  {"medio": 11, "min": 7,  "max": 15},
        Padrao.STANDARD:   {"medio": 13, "min": 9,  "max": 17},
        Padrao.MEDIO:      {"medio": 15, "min": 11, "max": 20},
        Padrao.MEDIO_ALTO: {"medio": 17, "min": 13, "max": 23},
        Padrao.ALTO:       {"medio": 20, "min": 15, "max": 26},
        Padrao.LUXO:       {"medio": 23, "min": 17, "max": 30},
    },
    TipoNegociacao.PERMUTA_RESULTADO: {
        Padrao.ECONOMICO:  {"medio": 13, "min": 9,  "max": 17},
        Padrao.STANDARD:   {"medio": 15, "min": 10, "max": 20},
        Padrao.MEDIO:      {"medio": 17, "min": 12, "max": 23},
        Padrao.MEDIO_ALTO: {"medio": 20, "min": 15, "max": 26},
        Padrao.ALTO:       {"medio": 23, "min": 17, "max": 30},
        Padrao.LUXO:       {"medio": 27, "min": 20, "max": 35},
    },
}


# ==========================================================================
# Despesas comerciais (% do VGV)
# Referência: Práticas de mercado, SECOVI
# ==========================================================================
DESPESAS_COMERCIAIS: dict[str, dict[Padrao, dict]] = {
    "corretagem": {
        Padrao.ECONOMICO:  {"medio": 4.0, "min": 3.0, "max": 5.0},
        Padrao.STANDARD:   {"medio": 4.5, "min": 3.5, "max": 5.5},
        Padrao.MEDIO:      {"medio": 5.0, "min": 4.0, "max": 6.0},
        Padrao.MEDIO_ALTO: {"medio": 5.0, "min": 4.0, "max": 6.0},
        Padrao.ALTO:       {"medio": 5.5, "min": 4.0, "max": 6.5},
        Padrao.LUXO:       {"medio": 6.0, "min": 4.5, "max": 7.0},
    },
    "marketing": {
        Padrao.ECONOMICO:  {"medio": 2.0, "min": 1.0, "max": 3.0},
        Padrao.STANDARD:   {"medio": 2.5, "min": 1.5, "max": 3.5},
        Padrao.MEDIO:      {"medio": 3.0, "min": 2.0, "max": 4.0},
        Padrao.MEDIO_ALTO: {"medio": 3.5, "min": 2.0, "max": 4.5},
        Padrao.ALTO:       {"medio": 3.5, "min": 2.5, "max": 5.0},
        Padrao.LUXO:       {"medio": 4.0, "min": 2.5, "max": 5.5},
    },
    "stand_vendas": {
        Padrao.ECONOMICO:  {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.STANDARD:   {"medio": 0.8, "min": 0.5, "max": 1.2},
        Padrao.MEDIO:      {"medio": 1.0, "min": 0.5, "max": 1.5},
        Padrao.MEDIO_ALTO: {"medio": 1.2, "min": 0.7, "max": 1.8},
        Padrao.ALTO:       {"medio": 1.5, "min": 0.8, "max": 2.0},
        Padrao.LUXO:       {"medio": 2.0, "min": 1.0, "max": 3.0},
    },
}


# ==========================================================================
# Despesas administrativas (% do VGV)
# ==========================================================================
DESPESAS_ADMINISTRATIVAS: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 2.0, "min": 1.5, "max": 3.0},
    Padrao.STANDARD:   {"medio": 2.5, "min": 1.5, "max": 3.5},
    Padrao.MEDIO:      {"medio": 3.0, "min": 2.0, "max": 4.0},
    Padrao.MEDIO_ALTO: {"medio": 3.0, "min": 2.0, "max": 4.5},
    Padrao.ALTO:       {"medio": 3.5, "min": 2.5, "max": 5.0},
    Padrao.LUXO:       {"medio": 4.0, "min": 2.5, "max": 5.5},
}


# ==========================================================================
# Despesas tributárias - Alíquotas por regime
# Referência: RFB, legislação vigente 2024/2025
# ==========================================================================
ALIQUOTAS_TRIBUTARIAS: dict[str, dict] = {
    "RET": {
        "aliquota": 4.0,
        "descricao": "Regime Especial de Tributação - alíquota única sobre receita bruta",
        "fonte": "Lei 10.931/2004, alterada pela Lei 12.024/2009",
    },
    "RET_MCMV": {
        "aliquota": 1.0,
        "descricao": "RET para empreendimentos MCMV faixa 1",
        "fonte": "Lei 12.024/2009",
    },
    "LUCRO_PRESUMIDO": {
        "aliquota": 6.73,
        "descricao": "Lucro Presumido (PIS 0.65% + COFINS 3% + IRPJ 1.2% + CSLL 1.08% + adicional IRPJ 0.8%)",
        "fonte": "Legislação federal - estimativa para incorporação",
    },
    "SPE_RET": {
        "aliquota": 4.0,
        "descricao": "SPE com adesão ao RET - alíquota única",
        "fonte": "Lei 10.931/2004",
    },
}

# Regime sugerido por padrão
REGIME_SUGERIDO: dict[Padrao, str] = {
    Padrao.ECONOMICO:  "RET_MCMV",
    Padrao.STANDARD:   "RET",
    Padrao.MEDIO:      "RET",
    Padrao.MEDIO_ALTO: "RET",
    Padrao.ALTO:       "LUCRO_PRESUMIDO",
    Padrao.LUXO:       "LUCRO_PRESUMIDO",
}


# ==========================================================================
# Taxas de inadimplência e distrato (% estimado)
# Referência: Abrainc, SECOVI 2024
# ==========================================================================
INADIMPLENCIA: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 8.0,  "min": 5.0,  "max": 12.0},
    Padrao.STANDARD:   {"medio": 6.0,  "min": 4.0,  "max": 9.0},
    Padrao.MEDIO:      {"medio": 5.0,  "min": 3.0,  "max": 7.0},
    Padrao.MEDIO_ALTO: {"medio": 4.0,  "min": 2.0,  "max": 6.0},
    Padrao.ALTO:       {"medio": 3.0,  "min": 1.5,  "max": 5.0},
    Padrao.LUXO:       {"medio": 2.5,  "min": 1.0,  "max": 4.0},
}

DISTRATO: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 15.0, "min": 10.0, "max": 22.0},
    Padrao.STANDARD:   {"medio": 12.0, "min": 8.0,  "max": 18.0},
    Padrao.MEDIO:      {"medio": 10.0, "min": 6.0,  "max": 15.0},
    Padrao.MEDIO_ALTO: {"medio": 8.0,  "min": 5.0,  "max": 12.0},
    Padrao.ALTO:       {"medio": 6.0,  "min": 3.0,  "max": 10.0},
    Padrao.LUXO:       {"medio": 5.0,  "min": 2.0,  "max": 8.0},
}


# ==========================================================================
# Premissas financeiras
# Referência: Mercado financeiro brasileiro 2024/2025
# ==========================================================================
PREMISSAS_FINANCEIRAS: dict[str, dict] = {
    "tma": {
        "medio": 12.0, "min": 9.0, "max": 18.0,
        "unidade": "% a.a.",
        "descricao": "Taxa Mínima de Atratividade",
        "fonte": "Prática de mercado imobiliário brasileiro",
    },
    "incc": {
        "medio": 6.5, "min": 4.0, "max": 10.0,
        "unidade": "% a.a.",
        "descricao": "Índice Nacional de Custo da Construção",
        "fonte": "FGV/IBRE - média últimos 12 meses",
    },
    "ipca": {
        "medio": 4.5, "min": 3.0, "max": 7.0,
        "unidade": "% a.a.",
        "descricao": "Índice de Preços ao Consumidor Amplo",
        "fonte": "IBGE - meta/expectativa BCB",
    },
    "igpm": {
        "medio": 5.0, "min": 3.0, "max": 8.0,
        "unidade": "% a.a.",
        "descricao": "Índice Geral de Preços do Mercado",
        "fonte": "FGV - média últimos 12 meses",
    },
    "financiamento_producao_taxa": {
        "medio": 12.5, "min": 10.0, "max": 15.0,
        "unidade": "% a.a.",
        "descricao": "Taxa de juros do financiamento à produção",
        "fonte": "Prática bancária - grandes bancos",
    },
    "financiamento_producao_carencia": {
        "medio": 6, "min": 3, "max": 12,
        "unidade": "meses",
        "descricao": "Carência do financiamento à produção",
        "fonte": "Prática bancária",
    },
    "financiamento_producao_prazo": {
        "medio": 36, "min": 24, "max": 48,
        "unidade": "meses",
        "descricao": "Prazo total do financiamento à produção",
        "fonte": "Prática bancária",
    },
    "financiamento_producao_pct_custo": {
        "medio": 70, "min": 50, "max": 80,
        "unidade": "% custo obra",
        "descricao": "Percentual do custo de obra financiado",
        "fonte": "Prática bancária",
    },
}


# ==========================================================================
# Área privativa média por tipologia e padrão (m²)
# Referência: Pesquisas de mercado, lançamentos recentes
# ==========================================================================
AREA_PRIVATIVA_MEDIA: dict[Tipologia, dict[Padrao, dict]] = {
    Tipologia.LOTEAMENTO: {
        Padrao.ECONOMICO:  {"medio": 160, "min": 125, "max": 200},
        Padrao.STANDARD:   {"medio": 200, "min": 160, "max": 250},
        Padrao.MEDIO:      {"medio": 250, "min": 200, "max": 350},
        Padrao.MEDIO_ALTO: {"medio": 350, "min": 250, "max": 500},
        Padrao.ALTO:       {"medio": 500, "min": 350, "max": 800},
        Padrao.LUXO:       {"medio": 800, "min": 500, "max": 1_500},
    },
    Tipologia.INCORPORACAO_VERTICAL: {
        Padrao.ECONOMICO:  {"medio": 42, "min": 35, "max": 50},
        Padrao.STANDARD:   {"medio": 55, "min": 45, "max": 70},
        Padrao.MEDIO:      {"medio": 75, "min": 60, "max": 95},
        Padrao.MEDIO_ALTO: {"medio": 110, "min": 85, "max": 140},
        Padrao.ALTO:       {"medio": 160, "min": 120, "max": 220},
        Padrao.LUXO:       {"medio": 250, "min": 180, "max": 400},
    },
    Tipologia.INCORPORACAO_HORIZONTAL: {
        Padrao.ECONOMICO:  {"medio": 55, "min": 42, "max": 70},
        Padrao.STANDARD:   {"medio": 80, "min": 60, "max": 100},
        Padrao.MEDIO:      {"medio": 120, "min": 90, "max": 160},
        Padrao.MEDIO_ALTO: {"medio": 170, "min": 130, "max": 220},
        Padrao.ALTO:       {"medio": 250, "min": 180, "max": 350},
        Padrao.LUXO:       {"medio": 400, "min": 280, "max": 600},
    },
    Tipologia.MULTIPROPRIEDADE: {
        Padrao.ECONOMICO:  {"medio": 30, "min": 20, "max": 40},
        Padrao.STANDARD:   {"medio": 35, "min": 25, "max": 45},
        Padrao.MEDIO:      {"medio": 45, "min": 35, "max": 60},
        Padrao.MEDIO_ALTO: {"medio": 60, "min": 45, "max": 80},
        Padrao.ALTO:       {"medio": 80, "min": 60, "max": 110},
        Padrao.LUXO:       {"medio": 120, "min": 80, "max": 180},
    },
    Tipologia.MIXED_USE: {
        Padrao.ECONOMICO:  {"medio": 38, "min": 30, "max": 48},
        Padrao.STANDARD:   {"medio": 50, "min": 38, "max": 65},
        Padrao.MEDIO:      {"medio": 70, "min": 55, "max": 90},
        Padrao.MEDIO_ALTO: {"medio": 100, "min": 75, "max": 130},
        Padrao.ALTO:       {"medio": 140, "min": 100, "max": 200},
        Padrao.LUXO:       {"medio": 220, "min": 150, "max": 350},
    },
}


# ==========================================================================
# Taxas e registros cartorários (% do VGV estimado)
# ==========================================================================
TAXAS_CARTORARIAS: dict[str, dict] = {
    "registro_incorporacao": {
        "medio": 0.3, "min": 0.1, "max": 0.5,
        "descricao": "Registro de incorporação / loteamento",
    },
    "escrituras_imovel": {
        "medio": 0.5, "min": 0.3, "max": 0.8,
        "descricao": "Custos com escrituras e registros do imóvel",
    },
    "itbi_terreno": {
        "medio": 2.5, "min": 2.0, "max": 3.0,
        "descricao": "ITBI sobre aquisição do terreno (% valor terreno)",
    },
}


# ==========================================================================
# Curva de desembolso típica da obra (% acumulado por período)
# Formato: lista de (% do prazo, % acumulado do custo)
# Referência: Curva S típica de construção civil
# ==========================================================================
CURVA_DESEMBOLSO: dict[Tipologia, list[tuple[float, float]]] = {
    Tipologia.LOTEAMENTO: [
        (0.0, 0.0), (0.1, 8.0), (0.2, 20.0), (0.3, 35.0),
        (0.4, 50.0), (0.5, 63.0), (0.6, 74.0), (0.7, 83.0),
        (0.8, 90.0), (0.9, 96.0), (1.0, 100.0),
    ],
    Tipologia.INCORPORACAO_VERTICAL: [
        (0.0, 0.0), (0.1, 5.0), (0.2, 12.0), (0.3, 22.0),
        (0.4, 35.0), (0.5, 50.0), (0.6, 65.0), (0.7, 78.0),
        (0.8, 88.0), (0.9, 95.0), (1.0, 100.0),
    ],
    Tipologia.INCORPORACAO_HORIZONTAL: [
        (0.0, 0.0), (0.1, 6.0), (0.2, 15.0), (0.3, 28.0),
        (0.4, 42.0), (0.5, 55.0), (0.6, 68.0), (0.7, 80.0),
        (0.8, 89.0), (0.9, 96.0), (1.0, 100.0),
    ],
    Tipologia.MULTIPROPRIEDADE: [
        (0.0, 0.0), (0.1, 5.0), (0.2, 12.0), (0.3, 22.0),
        (0.4, 35.0), (0.5, 50.0), (0.6, 65.0), (0.7, 78.0),
        (0.8, 88.0), (0.9, 95.0), (1.0, 100.0),
    ],
    Tipologia.MIXED_USE: [
        (0.0, 0.0), (0.1, 4.0), (0.2, 10.0), (0.3, 20.0),
        (0.4, 33.0), (0.5, 48.0), (0.6, 63.0), (0.7, 77.0),
        (0.8, 88.0), (0.9, 95.0), (1.0, 100.0),
    ],
}


# ==========================================================================
# Coordenação comercial (% do VGV)
# Referência: Checklist Viabilidade Trinus, práticas de mercado
# ==========================================================================
COORDENACAO_COMERCIAL: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 0.5, "min": 0.3, "max": 1.0},
    Padrao.STANDARD:   {"medio": 0.8, "min": 0.5, "max": 1.2},
    Padrao.MEDIO:      {"medio": 1.0, "min": 0.5, "max": 1.5},
    Padrao.MEDIO_ALTO: {"medio": 1.0, "min": 0.5, "max": 1.5},
    Padrao.ALTO:       {"medio": 1.2, "min": 0.8, "max": 1.5},
    Padrao.LUXO:       {"medio": 1.5, "min": 1.0, "max": 2.0},
}


# ==========================================================================
# Premiação de corretores (% do VGV)
# Referência: Checklist Viabilidade Trinus
# ==========================================================================
PREMIACAO_CORRETORES: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 0.3, "min": 0.0, "max": 0.5},
    Padrao.STANDARD:   {"medio": 0.5, "min": 0.3, "max": 0.8},
    Padrao.MEDIO:      {"medio": 0.5, "min": 0.3, "max": 1.0},
    Padrao.MEDIO_ALTO: {"medio": 0.5, "min": 0.3, "max": 1.0},
    Padrao.ALTO:       {"medio": 0.8, "min": 0.5, "max": 1.2},
    Padrao.LUXO:       {"medio": 1.0, "min": 0.5, "max": 1.5},
}


# ==========================================================================
# Custo de projetos e consultorias (% do VGV)
# Referência: Checklist Viabilidade Trinus
# Incorporação: ~R$10/m² de área construída ou 1% a 1.5% VGV
# Urbanismo: 1% a 1.5% do VGV
# ==========================================================================
CUSTO_PROJETOS: dict[Tipologia, dict[Padrao, dict]] = {
    Tipologia.LOTEAMENTO: {
        Padrao.ECONOMICO:  {"medio": 1.0, "min": 0.7, "max": 1.5},
        Padrao.STANDARD:   {"medio": 1.0, "min": 0.7, "max": 1.5},
        Padrao.MEDIO:      {"medio": 1.2, "min": 0.8, "max": 1.5},
        Padrao.MEDIO_ALTO: {"medio": 1.2, "min": 0.8, "max": 1.8},
        Padrao.ALTO:       {"medio": 1.5, "min": 1.0, "max": 2.0},
        Padrao.LUXO:       {"medio": 1.5, "min": 1.0, "max": 2.5},
    },
    Tipologia.INCORPORACAO_VERTICAL: {
        Padrao.ECONOMICO:  {"medio": 1.0, "min": 0.5, "max": 1.5},
        Padrao.STANDARD:   {"medio": 1.2, "min": 0.8, "max": 1.5},
        Padrao.MEDIO:      {"medio": 1.2, "min": 0.8, "max": 1.8},
        Padrao.MEDIO_ALTO: {"medio": 1.5, "min": 1.0, "max": 2.0},
        Padrao.ALTO:       {"medio": 1.5, "min": 1.0, "max": 2.5},
        Padrao.LUXO:       {"medio": 2.0, "min": 1.5, "max": 3.0},
    },
    Tipologia.INCORPORACAO_HORIZONTAL: {
        Padrao.ECONOMICO:  {"medio": 1.0, "min": 0.5, "max": 1.5},
        Padrao.STANDARD:   {"medio": 1.2, "min": 0.8, "max": 1.5},
        Padrao.MEDIO:      {"medio": 1.2, "min": 0.8, "max": 1.8},
        Padrao.MEDIO_ALTO: {"medio": 1.5, "min": 1.0, "max": 2.0},
        Padrao.ALTO:       {"medio": 1.5, "min": 1.0, "max": 2.5},
        Padrao.LUXO:       {"medio": 2.0, "min": 1.5, "max": 3.0},
    },
    Tipologia.MULTIPROPRIEDADE: {
        Padrao.ECONOMICO:  {"medio": 1.2, "min": 0.8, "max": 1.5},
        Padrao.STANDARD:   {"medio": 1.2, "min": 0.8, "max": 1.8},
        Padrao.MEDIO:      {"medio": 1.5, "min": 1.0, "max": 2.0},
        Padrao.MEDIO_ALTO: {"medio": 1.5, "min": 1.0, "max": 2.5},
        Padrao.ALTO:       {"medio": 2.0, "min": 1.5, "max": 3.0},
        Padrao.LUXO:       {"medio": 2.5, "min": 1.5, "max": 3.5},
    },
    Tipologia.MIXED_USE: {
        Padrao.ECONOMICO:  {"medio": 1.2, "min": 0.8, "max": 1.5},
        Padrao.STANDARD:   {"medio": 1.2, "min": 0.8, "max": 1.8},
        Padrao.MEDIO:      {"medio": 1.5, "min": 1.0, "max": 2.0},
        Padrao.MEDIO_ALTO: {"medio": 1.5, "min": 1.0, "max": 2.5},
        Padrao.ALTO:       {"medio": 2.0, "min": 1.5, "max": 3.0},
        Padrao.LUXO:       {"medio": 2.5, "min": 1.5, "max": 3.5},
    },
}


# ==========================================================================
# Custo de aprovações e licenças (% do VGV)
# Referência: Checklist Viabilidade Trinus
# Urbanismo: 0.5% (sem considerar contrapartidas financeiras)
# ==========================================================================
CUSTO_APROVACOES: dict[Tipologia, dict[Padrao, dict]] = {
    Tipologia.LOTEAMENTO: {
        Padrao.ECONOMICO:  {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.STANDARD:   {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.MEDIO:      {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.MEDIO_ALTO: {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.ALTO:       {"medio": 0.8, "min": 0.5, "max": 1.2},
        Padrao.LUXO:       {"medio": 1.0, "min": 0.5, "max": 1.5},
    },
    Tipologia.INCORPORACAO_VERTICAL: {
        Padrao.ECONOMICO:  {"medio": 0.3, "min": 0.2, "max": 0.8},
        Padrao.STANDARD:   {"medio": 0.5, "min": 0.3, "max": 0.8},
        Padrao.MEDIO:      {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.MEDIO_ALTO: {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.ALTO:       {"medio": 0.8, "min": 0.5, "max": 1.2},
        Padrao.LUXO:       {"medio": 1.0, "min": 0.5, "max": 1.5},
    },
    Tipologia.INCORPORACAO_HORIZONTAL: {
        Padrao.ECONOMICO:  {"medio": 0.3, "min": 0.2, "max": 0.8},
        Padrao.STANDARD:   {"medio": 0.5, "min": 0.3, "max": 0.8},
        Padrao.MEDIO:      {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.MEDIO_ALTO: {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.ALTO:       {"medio": 0.8, "min": 0.5, "max": 1.2},
        Padrao.LUXO:       {"medio": 1.0, "min": 0.5, "max": 1.5},
    },
    Tipologia.MULTIPROPRIEDADE: {
        Padrao.ECONOMICO:  {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.STANDARD:   {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.MEDIO:      {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.MEDIO_ALTO: {"medio": 0.8, "min": 0.5, "max": 1.2},
        Padrao.ALTO:       {"medio": 0.8, "min": 0.5, "max": 1.5},
        Padrao.LUXO:       {"medio": 1.0, "min": 0.5, "max": 1.5},
    },
    Tipologia.MIXED_USE: {
        Padrao.ECONOMICO:  {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.STANDARD:   {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.MEDIO:      {"medio": 0.5, "min": 0.3, "max": 1.0},
        Padrao.MEDIO_ALTO: {"medio": 0.8, "min": 0.5, "max": 1.2},
        Padrao.ALTO:       {"medio": 0.8, "min": 0.5, "max": 1.5},
        Padrao.LUXO:       {"medio": 1.0, "min": 0.5, "max": 1.5},
    },
}


# ==========================================================================
# Curva de vendas por fase (% do total vendido)
# Referência: Checklist Viabilidade Trinus
# Incorporação pessimista: 20% lançamento, 60% obra, 20% pós-obra
# Urbanismo pessimista: 30% lançamento, 50% obra, 20% pós-obra
# ==========================================================================
CURVA_VENDAS_FASES: dict[Tipologia, dict[str, dict]] = {
    Tipologia.LOTEAMENTO: {
        "pessimista":     {"lancamento": 30, "obra": 50, "pos_obra": 20},
        "moderada":       {"lancamento": 40, "obra": 45, "pos_obra": 15},
        "otimista":       {"lancamento": 50, "obra": 40, "pos_obra": 10},
    },
    Tipologia.INCORPORACAO_VERTICAL: {
        "pessimista":     {"lancamento": 20, "obra": 60, "pos_obra": 20},
        "moderada":       {"lancamento": 30, "obra": 55, "pos_obra": 15},
        "otimista":       {"lancamento": 40, "obra": 50, "pos_obra": 10},
    },
    Tipologia.INCORPORACAO_HORIZONTAL: {
        "pessimista":     {"lancamento": 20, "obra": 60, "pos_obra": 20},
        "moderada":       {"lancamento": 30, "obra": 55, "pos_obra": 15},
        "otimista":       {"lancamento": 40, "obra": 50, "pos_obra": 10},
    },
    Tipologia.MULTIPROPRIEDADE: {
        "pessimista":     {"lancamento": 25, "obra": 55, "pos_obra": 20},
        "moderada":       {"lancamento": 35, "obra": 50, "pos_obra": 15},
        "otimista":       {"lancamento": 50, "obra": 40, "pos_obra": 10},
    },
    Tipologia.MIXED_USE: {
        "pessimista":     {"lancamento": 20, "obra": 60, "pos_obra": 20},
        "moderada":       {"lancamento": 30, "obra": 55, "pos_obra": 15},
        "otimista":       {"lancamento": 40, "obra": 50, "pos_obra": 10},
    },
}


# ==========================================================================
# Prazo para Registro de Incorporação/Loteamento (meses)
# Referência: Checklist Viabilidade Trinus
# Incorporação: ~2 meses, Urbanismo: ~4 meses
# ==========================================================================
PRAZO_REGISTRO: dict[Tipologia, dict] = {
    Tipologia.LOTEAMENTO:              {"medio": 4, "min": 3, "max": 6},
    Tipologia.INCORPORACAO_VERTICAL:   {"medio": 2, "min": 1, "max": 4},
    Tipologia.INCORPORACAO_HORIZONTAL: {"medio": 2, "min": 1, "max": 4},
    Tipologia.MULTIPROPRIEDADE:        {"medio": 3, "min": 2, "max": 5},
    Tipologia.MIXED_USE:               {"medio": 3, "min": 2, "max": 5},
}


# ==========================================================================
# Taxa de administração de obra / BDI (% sobre custo raso)
# Referência: Checklist Viabilidade Trinus, DFC real
# ==========================================================================
BDI_ADMINISTRACAO_OBRA: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 10.0, "min": 8.0, "max": 15.0},
    Padrao.STANDARD:   {"medio": 12.0, "min": 8.0, "max": 15.0},
    Padrao.MEDIO:      {"medio": 12.0, "min": 10.0, "max": 18.0},
    Padrao.MEDIO_ALTO: {"medio": 15.0, "min": 10.0, "max": 20.0},
    Padrao.ALTO:       {"medio": 15.0, "min": 12.0, "max": 20.0},
    Padrao.LUXO:       {"medio": 18.0, "min": 12.0, "max": 22.0},
}


# ==========================================================================
# Seguros (% do VGV)
# Referência: Checklist Viabilidade Trinus
# ==========================================================================
SEGUROS: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 0.3, "min": 0.1, "max": 0.5},
    Padrao.STANDARD:   {"medio": 0.3, "min": 0.2, "max": 0.5},
    Padrao.MEDIO:      {"medio": 0.4, "min": 0.2, "max": 0.6},
    Padrao.MEDIO_ALTO: {"medio": 0.4, "min": 0.2, "max": 0.7},
    Padrao.ALTO:       {"medio": 0.5, "min": 0.3, "max": 0.8},
    Padrao.LUXO:       {"medio": 0.5, "min": 0.3, "max": 1.0},
}


# ==========================================================================
# Despesas pré-operacionais / Constituição SPE (% do VGV)
# Referência: Checklist Viabilidade Trinus
# ==========================================================================
DESPESAS_PRE_OPERACIONAIS: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 0.3, "min": 0.1, "max": 0.5},
    Padrao.STANDARD:   {"medio": 0.3, "min": 0.2, "max": 0.5},
    Padrao.MEDIO:      {"medio": 0.4, "min": 0.2, "max": 0.6},
    Padrao.MEDIO_ALTO: {"medio": 0.4, "min": 0.2, "max": 0.7},
    Padrao.ALTO:       {"medio": 0.5, "min": 0.3, "max": 0.8},
    Padrao.LUXO:       {"medio": 0.5, "min": 0.3, "max": 1.0},
}


# ==========================================================================
# CRI (Certificado de Recebíveis Imobiliários)
# Referência: Checklist Viabilidade Trinus
# ==========================================================================
PREMISSAS_CRI: dict[str, dict] = {
    "taxa_cdi_spread": {
        "medio": 5.0, "min": 4.0, "max": 6.0,
        "unidade": "% a.a. (CDI+)",
        "descricao": "Spread sobre CDI para CRI",
        "fonte": "Checklist Viabilidade Trinus",
    },
    "taxa_ipca_spread": {
        "medio": 14.0, "min": 13.0, "max": 15.0,
        "unidade": "% a.a. (IPCA+)",
        "descricao": "Spread sobre IPCA para CRI",
        "fonte": "Checklist Viabilidade Trinus",
    },
    "prazo_operacao": {
        "medio": 60, "min": 36, "max": 120,
        "unidade": "meses",
        "descricao": "Prazo da operação de CRI",
        "fonte": "Práticas de mercado",
    },
    "custo_emissao": {
        "medio": 2.0, "min": 1.5, "max": 3.5,
        "unidade": "% do volume",
        "descricao": "Custos de emissão do CRI (estruturação, rating, distribuição)",
        "fonte": "Práticas de mercado",
    },
}


# ==========================================================================
# IPTU do terreno (% do valor do terreno por ano)
# Referência: Checklist Viabilidade Trinus (0.5% a 1.5%)
# ==========================================================================
IPTU_TERRENO: dict = {
    "medio": 1.0, "min": 0.5, "max": 1.5,
}


# ==========================================================================
# Meses de recuperação de inadimplência
# Referência: Checklist Viabilidade Trinus
# ==========================================================================
MESES_RECUPERACAO_INADIMPLENCIA: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 0, "min": 0, "max": 3},
    Padrao.STANDARD:   {"medio": 0, "min": 0, "max": 3},
    Padrao.MEDIO:      {"medio": 0, "min": 0, "max": 3},
    Padrao.MEDIO_ALTO: {"medio": 0, "min": 0, "max": 3},
    Padrao.ALTO:       {"medio": 0, "min": 0, "max": 3},
    Padrao.LUXO:       {"medio": 0, "min": 0, "max": 3},
}


# ==========================================================================
# Inadimplência por tipologia (específica para urbanismo)
# Referência: Checklist Viabilidade Trinus (Urbanismo)
# Loteamento aberto: 25% a 30%, Condomínio fechado: 10% a 15%
# ==========================================================================
INADIMPLENCIA_POR_TIPOLOGIA: dict[Tipologia, dict[Padrao, dict]] = {
    Tipologia.LOTEAMENTO: {
        Padrao.ECONOMICO:  {"medio": 28.0, "min": 22.0, "max": 35.0},
        Padrao.STANDARD:   {"medio": 25.0, "min": 20.0, "max": 30.0},
        Padrao.MEDIO:      {"medio": 20.0, "min": 15.0, "max": 28.0},
        Padrao.MEDIO_ALTO: {"medio": 15.0, "min": 10.0, "max": 22.0},
        Padrao.ALTO:       {"medio": 12.0, "min": 8.0,  "max": 18.0},
        Padrao.LUXO:       {"medio": 10.0, "min": 5.0,  "max": 15.0},
    },
    Tipologia.INCORPORACAO_VERTICAL: {
        Padrao.ECONOMICO:  {"medio": 8.0,  "min": 5.0,  "max": 12.0},
        Padrao.STANDARD:   {"medio": 6.0,  "min": 4.0,  "max": 9.0},
        Padrao.MEDIO:      {"medio": 5.0,  "min": 3.0,  "max": 7.0},
        Padrao.MEDIO_ALTO: {"medio": 4.0,  "min": 2.0,  "max": 6.0},
        Padrao.ALTO:       {"medio": 3.0,  "min": 1.5,  "max": 5.0},
        Padrao.LUXO:       {"medio": 2.5,  "min": 1.0,  "max": 4.0},
    },
    Tipologia.INCORPORACAO_HORIZONTAL: {
        Padrao.ECONOMICO:  {"medio": 10.0, "min": 6.0,  "max": 15.0},
        Padrao.STANDARD:   {"medio": 8.0,  "min": 5.0,  "max": 12.0},
        Padrao.MEDIO:      {"medio": 6.0,  "min": 4.0,  "max": 9.0},
        Padrao.MEDIO_ALTO: {"medio": 5.0,  "min": 3.0,  "max": 7.0},
        Padrao.ALTO:       {"medio": 4.0,  "min": 2.0,  "max": 6.0},
        Padrao.LUXO:       {"medio": 3.0,  "min": 1.5,  "max": 5.0},
    },
    Tipologia.MULTIPROPRIEDADE: {
        Padrao.ECONOMICO:  {"medio": 10.0, "min": 6.0,  "max": 15.0},
        Padrao.STANDARD:   {"medio": 8.0,  "min": 5.0,  "max": 12.0},
        Padrao.MEDIO:      {"medio": 6.0,  "min": 4.0,  "max": 9.0},
        Padrao.MEDIO_ALTO: {"medio": 5.0,  "min": 3.0,  "max": 8.0},
        Padrao.ALTO:       {"medio": 4.0,  "min": 2.0,  "max": 6.0},
        Padrao.LUXO:       {"medio": 3.0,  "min": 1.5,  "max": 5.0},
    },
    Tipologia.MIXED_USE: {
        Padrao.ECONOMICO:  {"medio": 8.0,  "min": 5.0,  "max": 12.0},
        Padrao.STANDARD:   {"medio": 6.0,  "min": 4.0,  "max": 9.0},
        Padrao.MEDIO:      {"medio": 5.0,  "min": 3.0,  "max": 7.0},
        Padrao.MEDIO_ALTO: {"medio": 4.0,  "min": 2.0,  "max": 6.0},
        Padrao.ALTO:       {"medio": 3.0,  "min": 1.5,  "max": 5.0},
        Padrao.LUXO:       {"medio": 2.5,  "min": 1.0,  "max": 4.0},
    },
}


# ==========================================================================
# Indexadores de correção por fase
# Referência: Checklist Viabilidade Trinus
# Incorporação: Pré-chaves: INCC, Pós-chaves: IGP-M
# Urbanismo: IPCA
# ==========================================================================
INDEXADORES_POR_TIPOLOGIA: dict[Tipologia, dict[str, str]] = {
    Tipologia.LOTEAMENTO:              {"pre_chaves": "IPCA", "pos_chaves": "IPCA"},
    Tipologia.INCORPORACAO_VERTICAL:   {"pre_chaves": "INCC", "pos_chaves": "IGPM"},
    Tipologia.INCORPORACAO_HORIZONTAL: {"pre_chaves": "INCC", "pos_chaves": "IGPM"},
    Tipologia.MULTIPROPRIEDADE:        {"pre_chaves": "INCC", "pos_chaves": "IGPM"},
    Tipologia.MIXED_USE:               {"pre_chaves": "INCC", "pos_chaves": "IGPM"},
}


# ==========================================================================
# Despesas de gestão do empreendimento / Gerenciamento (% do VGV)
# Referência: DFC real, Checklist Viabilidade Trinus
# ==========================================================================
TAXA_GESTAO: dict[Padrao, dict] = {
    Padrao.ECONOMICO:  {"medio": 1.0, "min": 0.5, "max": 1.5},
    Padrao.STANDARD:   {"medio": 1.0, "min": 0.5, "max": 2.0},
    Padrao.MEDIO:      {"medio": 1.5, "min": 1.0, "max": 2.5},
    Padrao.MEDIO_ALTO: {"medio": 1.5, "min": 1.0, "max": 2.5},
    Padrao.ALTO:       {"medio": 2.0, "min": 1.0, "max": 3.0},
    Padrao.LUXO:       {"medio": 2.5, "min": 1.5, "max": 3.5},
}
