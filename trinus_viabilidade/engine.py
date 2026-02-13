"""
Trinus Viabilidade - Motor de sugestão de premissas.

Recebe os inputs do usuário e retorna premissas sugeridas com base
nas tabelas de referência de mercado.
"""

from __future__ import annotations

from modelos import (
    InputsUsuario,
    Padrao,
    Premissa,
    ResultadoPremissas,
    TabelaVendas,
    Tipologia,
    TipoNegociacao,
)
from dados_mercado import (
    ALIQUOTAS_TRIBUTARIAS,
    AREA_PRIVATIVA_MEDIA,
    CUB_POR_REGIAO,
    CUSTO_INFRAESTRUTURA_LOTE,
    CUSTO_TERRENO_PCT_VGV,
    CURVA_DESEMBOLSO,
    DESPESAS_ADMINISTRATIVAS,
    DESPESAS_COMERCIAIS,
    DISTRATO,
    INADIMPLENCIA,
    PRAZO_OBRA,
    PRECO_LOTE_M2,
    PRECO_VENDA_M2,
    PREMISSAS_FINANCEIRAS,
    REGIME_SUGERIDO,
    TABELA_VENDAS,
    TAXAS_CARTORARIAS,
    VELOCIDADE_VENDAS,
)


def gerar_premissas(inputs: InputsUsuario) -> ResultadoPremissas:
    """
    Gera todas as premissas sugeridas com base nos inputs do usuário.

    Retorna um ResultadoPremissas com premissas organizadas por categoria.
    """
    resultado = ResultadoPremissas(inputs=inputs)
    regiao = inputs.regiao

    # --- Área privativa média ---
    area_priv = inputs.area_privativa_media_m2
    if area_priv is None:
        ref = AREA_PRIVATIVA_MEDIA[inputs.tipologia][inputs.padrao]
        area_priv = ref["medio"]
        resultado.premissas.append(Premissa(
            nome="Área privativa média por unidade",
            valor=ref["medio"],
            unidade="m²",
            valor_min=ref["min"],
            valor_max=ref["max"],
            fonte="Pesquisas de mercado, lançamentos recentes",
            categoria="Receita",
            subcategoria="Dimensionamento",
            descricao="Área privativa média estimada por unidade",
        ))

    # ===================================================================
    # PREMISSAS DE RECEITA
    # ===================================================================
    _gerar_premissas_receita(resultado, inputs, regiao, area_priv)

    # ===================================================================
    # PREMISSAS DE CUSTO
    # ===================================================================
    _gerar_premissas_custo(resultado, inputs, regiao, area_priv)

    # ===================================================================
    # PREMISSAS DE DESPESA
    # ===================================================================
    _gerar_premissas_despesa(resultado, inputs)

    # ===================================================================
    # PREMISSAS FINANCEIRAS
    # ===================================================================
    _gerar_premissas_financeiras(resultado)

    # ===================================================================
    # TABELA DE VENDAS
    # ===================================================================
    _gerar_tabela_vendas(resultado, inputs)

    return resultado


def _gerar_premissas_receita(
    resultado: ResultadoPremissas,
    inputs: InputsUsuario,
    regiao,
    area_priv: float,
):
    """Gera premissas da categoria Receita."""
    e_loteamento = inputs.tipologia == Tipologia.LOTEAMENTO

    # Preço por m²
    if e_loteamento:
        ref_preco = PRECO_LOTE_M2[regiao][inputs.padrao]
        label_preco = "Preço médio por m² (lote)"
        desc_preco = "Preço médio de venda por m² de lote"
    else:
        ref_preco = PRECO_VENDA_M2[regiao][inputs.padrao]
        label_preco = "Preço médio por m² (área privativa)"
        desc_preco = "Preço médio de venda por m² de área privativa"

    resultado.premissas.append(Premissa(
        nome=label_preco,
        valor=ref_preco["medio"],
        unidade="R$/m²",
        valor_min=ref_preco["min"],
        valor_max=ref_preco["max"],
        fonte="FipeZap, DataZap, pesquisas regionais 2024/2025",
        categoria="Receita",
        subcategoria="Preço de Venda",
        descricao=desc_preco,
    ))

    # VGV estimado
    if inputs.vgv_estimado:
        vgv = inputs.vgv_estimado
    else:
        preco_m2 = ref_preco["medio"]
        vgv = preco_m2 * area_priv * inputs.num_unidades

    vgv_min = ref_preco["min"] * area_priv * inputs.num_unidades
    vgv_max = ref_preco["max"] * area_priv * inputs.num_unidades

    resultado.premissas.append(Premissa(
        nome="VGV estimado",
        valor=vgv,
        unidade="R$",
        valor_min=vgv_min,
        valor_max=vgv_max,
        fonte="Calculado: preço/m² x área x unidades"
        if not inputs.vgv_estimado
        else "Informado pelo usuário",
        categoria="Receita",
        subcategoria="VGV",
        descricao="Valor Geral de Vendas total do empreendimento",
        editavel=not bool(inputs.vgv_estimado),
    ))

    # Ticket médio
    ticket = vgv / inputs.num_unidades if inputs.num_unidades > 0 else 0
    resultado.premissas.append(Premissa(
        nome="Ticket médio por unidade",
        valor=ticket,
        unidade="R$",
        valor_min=vgv_min / inputs.num_unidades if inputs.num_unidades > 0 else 0,
        valor_max=vgv_max / inputs.num_unidades if inputs.num_unidades > 0 else 0,
        fonte="Calculado: VGV / número de unidades",
        categoria="Receita",
        subcategoria="VGV",
        descricao="Valor médio por unidade vendida",
    ))

    # Velocidade de vendas
    ref_vel = VELOCIDADE_VENDAS[inputs.tipologia][inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Velocidade de vendas",
        valor=ref_vel["medio"],
        unidade="% estoque/mês",
        valor_min=ref_vel["min"],
        valor_max=ref_vel["max"],
        fonte="SECOVI, Abrainc, CBIC 2024",
        categoria="Receita",
        subcategoria="Vendas",
        descricao="Percentual do estoque vendido por mês (VSO mensal)",
    ))

    # Inadimplência
    ref_inad = INADIMPLENCIA[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Taxa de inadimplência estimada",
        valor=ref_inad["medio"],
        unidade="%",
        valor_min=ref_inad["min"],
        valor_max=ref_inad["max"],
        fonte="Abrainc, SECOVI 2024",
        categoria="Receita",
        subcategoria="Vendas",
        descricao="Percentual estimado de inadimplência sobre recebíveis",
    ))

    # Distrato
    ref_dist = DISTRATO[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Taxa de distrato estimada",
        valor=ref_dist["medio"],
        unidade="%",
        valor_min=ref_dist["min"],
        valor_max=ref_dist["max"],
        fonte="Abrainc, SECOVI 2024",
        categoria="Receita",
        subcategoria="Vendas",
        descricao="Percentual estimado de distratos sobre vendas totais",
    ))


def _gerar_premissas_custo(
    resultado: ResultadoPremissas,
    inputs: InputsUsuario,
    regiao,
    area_priv: float,
):
    """Gera premissas da categoria Custo."""
    e_loteamento = inputs.tipologia == Tipologia.LOTEAMENTO

    # Custo de construção / CUB
    if not e_loteamento:
        ref_cub = CUB_POR_REGIAO[regiao][inputs.padrao]
        resultado.premissas.append(Premissa(
            nome="Custo de construção por m²",
            valor=ref_cub["medio"],
            unidade="R$/m²",
            valor_min=ref_cub["min"],
            valor_max=ref_cub["max"],
            fonte="CUB/SINDUSCON regional 2024/2025",
            categoria="Custo",
            subcategoria="Construção",
            descricao="Custo unitário básico de construção por m² de área privativa",
        ))

        # Custo total de construção
        custo_total = ref_cub["medio"] * area_priv * inputs.num_unidades
        resultado.premissas.append(Premissa(
            nome="Custo total de construção estimado",
            valor=custo_total,
            unidade="R$",
            valor_min=ref_cub["min"] * area_priv * inputs.num_unidades,
            valor_max=ref_cub["max"] * area_priv * inputs.num_unidades,
            fonte="Calculado: CUB x área privativa x unidades",
            categoria="Custo",
            subcategoria="Construção",
            descricao="Custo total estimado de construção do empreendimento",
        ))

    # Custo de infraestrutura (loteamentos)
    if e_loteamento:
        ref_infra = CUSTO_INFRAESTRUTURA_LOTE[inputs.padrao]
        resultado.premissas.append(Premissa(
            nome="Custo de infraestrutura por m²",
            valor=ref_infra["medio"],
            unidade="R$/m²",
            valor_min=ref_infra["min"],
            valor_max=ref_infra["max"],
            fonte="AELO, SECOVI, práticas de mercado",
            categoria="Custo",
            subcategoria="Infraestrutura",
            descricao="Custo de infraestrutura por m² de área total do loteamento",
        ))

        if inputs.area_terreno_m2:
            custo_infra_total = ref_infra["medio"] * inputs.area_terreno_m2
            resultado.premissas.append(Premissa(
                nome="Custo total de infraestrutura estimado",
                valor=custo_infra_total,
                unidade="R$",
                valor_min=ref_infra["min"] * inputs.area_terreno_m2,
                valor_max=ref_infra["max"] * inputs.area_terreno_m2,
                fonte="Calculado: custo/m² x área total terreno",
                categoria="Custo",
                subcategoria="Infraestrutura",
                descricao="Custo total estimado de infraestrutura",
            ))

    # Custo do terreno (% VGV)
    ref_terreno = CUSTO_TERRENO_PCT_VGV[inputs.tipo_negociacao][inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Custo do terreno (% VGV)",
        valor=ref_terreno["medio"],
        unidade="% do VGV",
        valor_min=ref_terreno["min"],
        valor_max=ref_terreno["max"],
        fonte="Práticas de mercado por tipo de negociação",
        categoria="Custo",
        subcategoria="Terreno",
        descricao=f"Custo do terreno como percentual do VGV ({inputs.tipo_negociacao.value})",
    ))

    # Prazo de obra
    ref_prazo = PRAZO_OBRA[inputs.tipologia][inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Prazo de obra estimado",
        valor=ref_prazo["medio"],
        unidade="meses",
        valor_min=ref_prazo["min"],
        valor_max=ref_prazo["max"],
        fonte="CBIC, práticas de mercado",
        categoria="Custo",
        subcategoria="Cronograma",
        descricao="Prazo estimado para conclusão da obra",
    ))


def _gerar_premissas_despesa(
    resultado: ResultadoPremissas,
    inputs: InputsUsuario,
):
    """Gera premissas da categoria Despesa."""

    # Despesas comerciais
    for tipo_desp, label in [
        ("corretagem", "Comissão de corretagem"),
        ("marketing", "Marketing e publicidade"),
        ("stand_vendas", "Stand de vendas"),
    ]:
        ref = DESPESAS_COMERCIAIS[tipo_desp][inputs.padrao]
        resultado.premissas.append(Premissa(
            nome=label,
            valor=ref["medio"],
            unidade="% do VGV",
            valor_min=ref["min"],
            valor_max=ref["max"],
            fonte="SECOVI, práticas de mercado",
            categoria="Despesa",
            subcategoria="Comercial",
            descricao=f"{label} como percentual do VGV",
        ))

    # Despesas administrativas
    ref_adm = DESPESAS_ADMINISTRATIVAS[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Despesas administrativas",
        valor=ref_adm["medio"],
        unidade="% do VGV",
        valor_min=ref_adm["min"],
        valor_max=ref_adm["max"],
        fonte="Práticas de mercado",
        categoria="Despesa",
        subcategoria="Administrativa",
        descricao="Despesas administrativas gerais como percentual do VGV",
    ))

    # Despesas tributárias
    regime_key = REGIME_SUGERIDO[inputs.padrao]
    regime_info = ALIQUOTAS_TRIBUTARIAS[regime_key]
    resultado.premissas.append(Premissa(
        nome="Alíquota tributária (regime sugerido)",
        valor=regime_info["aliquota"],
        unidade="% sobre receita",
        valor_min=1.0,
        valor_max=6.73,
        fonte=regime_info["fonte"],
        categoria="Despesa",
        subcategoria="Tributária",
        descricao=f"{regime_info['descricao']}",
    ))

    # Taxas cartoriais
    for tipo_taxa, info in TAXAS_CARTORARIAS.items():
        unidade = "% do VGV" if tipo_taxa != "itbi_terreno" else "% valor terreno"
        resultado.premissas.append(Premissa(
            nome=info["descricao"],
            valor=info["medio"],
            unidade=unidade,
            valor_min=info["min"],
            valor_max=info["max"],
            fonte="Tabela de custas cartorários regional",
            categoria="Despesa",
            subcategoria="Cartorária/Registros",
            descricao=info["descricao"],
        ))


def _gerar_premissas_financeiras(resultado: ResultadoPremissas):
    """Gera premissas da categoria Financeiro."""
    mapeamento = {
        "tma": ("Taxa Mínima de Atratividade (TMA)", "Taxa de Desconto"),
        "incc": ("INCC (projeção anual)", "Índices"),
        "ipca": ("IPCA (projeção anual)", "Índices"),
        "igpm": ("IGP-M (projeção anual)", "Índices"),
        "financiamento_producao_taxa": (
            "Financiamento à produção - Taxa", "Financiamento"
        ),
        "financiamento_producao_carencia": (
            "Financiamento à produção - Carência", "Financiamento"
        ),
        "financiamento_producao_prazo": (
            "Financiamento à produção - Prazo", "Financiamento"
        ),
        "financiamento_producao_pct_custo": (
            "Financiamento à produção - % Custo financiado", "Financiamento"
        ),
    }

    for chave, (nome, subcat) in mapeamento.items():
        ref = PREMISSAS_FINANCEIRAS[chave]
        resultado.premissas.append(Premissa(
            nome=nome,
            valor=ref["medio"],
            unidade=ref["unidade"],
            valor_min=ref["min"],
            valor_max=ref["max"],
            fonte=ref["fonte"],
            categoria="Financeiro",
            subcategoria=subcat,
            descricao=ref["descricao"],
        ))


def _gerar_tabela_vendas(
    resultado: ResultadoPremissas,
    inputs: InputsUsuario,
):
    """Gera a tabela de condições de vendas."""
    ref = TABELA_VENDAS[inputs.tipologia][inputs.padrao]
    resultado.tabela_vendas = TabelaVendas(
        entrada_pct=ref["entrada"],
        parcelas_obra_pct=ref["parcelas_obra"],
        financiamento_pct=ref["financiamento"],
        reforcos_pct=ref["reforcos"],
        num_parcelas_obra=ref["num_parcelas"],
    )
