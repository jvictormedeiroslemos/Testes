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
    TabelaVendasIncorporacao,
    TabelaVendasLoteamento,
    Tipologia,
    TipoNegociacao,
)
from dados_mercado import (
    ALIQUOTAS_TRIBUTARIAS,
    AREA_PRIVATIVA_MEDIA,
    BDI_ADMINISTRACAO_OBRA,
    COORDENACAO_COMERCIAL,
    CUB_POR_REGIAO,
    CUSTO_APROVACOES,
    CUSTO_INFRAESTRUTURA_LOTE,
    CUSTO_PROJETOS,
    CUSTO_TERRENO_PCT_VGV,
    CURVA_DESEMBOLSO,
    CURVA_VENDAS_FASES,
    DESPESAS_ADMINISTRATIVAS,
    DESPESAS_COMERCIAIS,
    DESPESAS_PRE_OPERACIONAIS,
    DISTRATO,
    INADIMPLENCIA_POR_TIPOLOGIA,
    INDEXADORES_POR_TIPOLOGIA,
    IPTU_TERRENO,
    MESES_RECUPERACAO_INADIMPLENCIA,
    PRAZO_OBRA,
    PRAZO_REGISTRO,
    PRECO_LOTE_M2,
    PRECO_VENDA_M2,
    PREMIACAO_CORRETORES,
    PREMISSAS_CRI,
    PREMISSAS_FINANCEIRAS,
    REGIME_SUGERIDO_POR_TIPOLOGIA,
    SEGUROS,
    TABELA_VENDAS,
    TABELA_VENDAS_LOTEAMENTO,
    TAXA_GESTAO,
    TAXAS_CARTORARIAS,
    VELOCIDADE_VENDAS,
)

# Tipologias que usam o modelo de Incorporação (CRI, financiamento à produção, etc.)
_TIPOLOGIAS_INCORPORACAO = {
    Tipologia.INCORPORACAO_VERTICAL,
    Tipologia.INCORPORACAO_HORIZONTAL,
    Tipologia.MULTIPROPRIEDADE,
    Tipologia.MIXED_USE,
}


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

    # Inadimplência (por tipologia - diferenciada para loteamentos)
    ref_inad = INADIMPLENCIA_POR_TIPOLOGIA[inputs.tipologia][inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Taxa de inadimplência estimada",
        valor=ref_inad["medio"],
        unidade="%",
        valor_min=ref_inad["min"],
        valor_max=ref_inad["max"],
        fonte="Abrainc, SECOVI 2024, Checklist Viabilidade Trinus",
        categoria="Receita",
        subcategoria="Vendas",
        descricao="Percentual estimado de inadimplência sobre recebíveis",
    ))

    # Meses de recuperação de inadimplência
    ref_recup = MESES_RECUPERACAO_INADIMPLENCIA[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Meses de recuperação de inadimplência",
        valor=ref_recup["medio"],
        unidade="meses",
        valor_min=ref_recup["min"],
        valor_max=ref_recup["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Receita",
        subcategoria="Vendas",
        descricao="Prazo estimado para recuperação de créditos inadimplentes",
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

    # Curva de vendas por fase
    ref_curva = CURVA_VENDAS_FASES[inputs.tipologia]["moderada"]
    resultado.premissas.append(Premissa(
        nome="Vendas no lançamento",
        valor=ref_curva["lancamento"],
        unidade="% do total",
        valor_min=CURVA_VENDAS_FASES[inputs.tipologia]["pessimista"]["lancamento"],
        valor_max=CURVA_VENDAS_FASES[inputs.tipologia]["otimista"]["lancamento"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Receita",
        subcategoria="Curva de Vendas",
        descricao="Percentual das vendas realizadas na fase de lançamento",
    ))
    resultado.premissas.append(Premissa(
        nome="Vendas durante obra",
        valor=ref_curva["obra"],
        unidade="% do total",
        valor_min=CURVA_VENDAS_FASES[inputs.tipologia]["otimista"]["obra"],
        valor_max=CURVA_VENDAS_FASES[inputs.tipologia]["pessimista"]["obra"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Receita",
        subcategoria="Curva de Vendas",
        descricao="Percentual das vendas realizadas durante a fase de obra",
    ))
    resultado.premissas.append(Premissa(
        nome="Vendas pós-obra",
        valor=ref_curva["pos_obra"],
        unidade="% do total",
        valor_min=CURVA_VENDAS_FASES[inputs.tipologia]["otimista"]["pos_obra"],
        valor_max=CURVA_VENDAS_FASES[inputs.tipologia]["pessimista"]["pos_obra"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Receita",
        subcategoria="Curva de Vendas",
        descricao="Percentual das vendas realizadas após conclusão da obra",
    ))

    # Indexadores de correção
    idx = INDEXADORES_POR_TIPOLOGIA[inputs.tipologia]
    resultado.premissas.append(Premissa(
        nome="Indexador pré-chaves",
        valor=0,
        unidade=idx["pre_chaves"],
        valor_min=0,
        valor_max=0,
        fonte="Checklist Viabilidade Trinus",
        categoria="Receita",
        subcategoria="Indexadores",
        descricao=f"Índice de correção das parcelas pré-chaves: {idx['pre_chaves']}",
        editavel=False,
    ))
    resultado.premissas.append(Premissa(
        nome="Indexador pós-chaves",
        valor=0,
        unidade=idx["pos_chaves"],
        valor_min=0,
        valor_max=0,
        fonte="Checklist Viabilidade Trinus",
        categoria="Receita",
        subcategoria="Indexadores",
        descricao=f"Índice de correção das parcelas pós-chaves: {idx['pos_chaves']}",
        editavel=False,
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

    # BDI / Taxa de administração de obra
    ref_bdi = BDI_ADMINISTRACAO_OBRA[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Taxa de administração de obra (BDI)",
        valor=ref_bdi["medio"],
        unidade="% sobre custo raso",
        valor_min=ref_bdi["min"],
        valor_max=ref_bdi["max"],
        fonte="Checklist Viabilidade Trinus, DFC real",
        categoria="Custo",
        subcategoria="Construção",
        descricao="Taxa de administração / BDI sobre o custo raso de obra",
    ))

    # Custo de projetos e consultorias
    ref_proj = CUSTO_PROJETOS[inputs.tipologia][inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Custo de projetos e consultorias",
        valor=ref_proj["medio"],
        unidade="% do VGV",
        valor_min=ref_proj["min"],
        valor_max=ref_proj["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Custo",
        subcategoria="Projetos e Aprovações",
        descricao="Custo de projetos (arquitetônico, estrutural, instalações, etc.)",
    ))

    # Custo de aprovações e licenças
    ref_aprov = CUSTO_APROVACOES[inputs.tipologia][inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Custo de aprovações e licenças",
        valor=ref_aprov["medio"],
        unidade="% do VGV",
        valor_min=ref_aprov["min"],
        valor_max=ref_aprov["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Custo",
        subcategoria="Projetos e Aprovações",
        descricao="Taxas municipais, estaduais e licenças para aprovação do empreendimento",
    ))

    # IPTU do terreno
    resultado.premissas.append(Premissa(
        nome="IPTU do terreno",
        valor=IPTU_TERRENO["medio"],
        unidade="% do valor do terreno/ano",
        valor_min=IPTU_TERRENO["min"],
        valor_max=IPTU_TERRENO["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Custo",
        subcategoria="Terreno",
        descricao="IPTU anual incidente sobre o terreno",
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

    # Prazo para Registro de Incorporação / Loteamento
    ref_ri = PRAZO_REGISTRO[inputs.tipologia]
    resultado.premissas.append(Premissa(
        nome="Prazo para Registro de Incorporação/Loteamento",
        valor=ref_ri["medio"],
        unidade="meses",
        valor_min=ref_ri["min"],
        valor_max=ref_ri["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Custo",
        subcategoria="Cronograma",
        descricao="Prazo estimado para obtenção do RI",
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

    # Coordenação comercial
    ref_coord = COORDENACAO_COMERCIAL[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Coordenação comercial",
        valor=ref_coord["medio"],
        unidade="% do VGV",
        valor_min=ref_coord["min"],
        valor_max=ref_coord["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Despesa",
        subcategoria="Comercial",
        descricao="Coordenação comercial como percentual do VGV",
    ))

    # Premiação de corretores
    ref_prem = PREMIACAO_CORRETORES[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Premiação de corretores",
        valor=ref_prem["medio"],
        unidade="% do VGV",
        valor_min=ref_prem["min"],
        valor_max=ref_prem["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Despesa",
        subcategoria="Comercial",
        descricao="Premiação sobre performance de vendas",
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
        descricao="Despesas administrativas gerais como percentual do VGV (3.5% a 5.5%)",
    ))

    # Taxa de gestão / Gerenciamento
    ref_gestao = TAXA_GESTAO[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Taxa de gestão do empreendimento",
        valor=ref_gestao["medio"],
        unidade="% do VGV",
        valor_min=ref_gestao["min"],
        valor_max=ref_gestao["max"],
        fonte="Checklist Viabilidade Trinus, DFC real",
        categoria="Despesa",
        subcategoria="Administrativa",
        descricao="Taxa de gerenciamento/gestão do empreendimento",
    ))

    # Seguros
    ref_seg = SEGUROS[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Seguros",
        valor=ref_seg["medio"],
        unidade="% do VGV",
        valor_min=ref_seg["min"],
        valor_max=ref_seg["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Despesa",
        subcategoria="Administrativa",
        descricao="Seguros (obra, responsabilidade civil, garantia de entrega)",
    ))

    # Despesas pré-operacionais
    ref_preop = DESPESAS_PRE_OPERACIONAIS[inputs.padrao]
    resultado.premissas.append(Premissa(
        nome="Despesas pré-operacionais",
        valor=ref_preop["medio"],
        unidade="% do VGV",
        valor_min=ref_preop["min"],
        valor_max=ref_preop["max"],
        fonte="Checklist Viabilidade Trinus",
        categoria="Despesa",
        subcategoria="Administrativa",
        descricao="Constituição da SPE, registros iniciais e despesas pré-operacionais",
    ))

    # Despesas tributárias (por tipologia)
    regime_key = REGIME_SUGERIDO_POR_TIPOLOGIA[inputs.tipologia][inputs.padrao]
    regime_info = ALIQUOTAS_TRIBUTARIAS[regime_key]
    e_loteamento = inputs.tipologia == Tipologia.LOTEAMENTO

    if e_loteamento:
        descricao_trib = (
            f"{regime_info['descricao']} — Loteamentos utilizam "
            f"predominantemente Lucro Presumido"
        )
        valor_min_trib = 5.93
        valor_max_trib = 6.73
    else:
        descricao_trib = regime_info["descricao"]
        valor_min_trib = 1.0
        valor_max_trib = 6.73

    resultado.premissas.append(Premissa(
        nome="Alíquota tributária (regime sugerido)",
        valor=regime_info["aliquota"],
        unidade="% sobre receita",
        valor_min=valor_min_trib,
        valor_max=valor_max_trib,
        fonte=regime_info["fonte"],
        categoria="Despesa",
        subcategoria="Tributária",
        descricao=descricao_trib,
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
    """Gera premissas da categoria Financeiro, condicionais por tipologia."""
    inputs = resultado.inputs
    e_incorporacao = inputs.tipologia in _TIPOLOGIAS_INCORPORACAO
    e_loteamento = inputs.tipologia == Tipologia.LOTEAMENTO

    # --- Premissas comuns a todas as tipologias ---
    premissas_comuns = {
        "tma": ("Taxa Mínima de Atratividade (TMA)", "Taxa de Desconto"),
        "ipca": ("IPCA (projeção anual)", "Índices"),
        "igpm": ("IGP-M (projeção anual)", "Índices"),
    }

    for chave, (nome, subcat) in premissas_comuns.items():
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

    # --- INCC: relevante para Incorporação (indexador pré-chaves) ---
    if e_incorporacao:
        ref_incc = PREMISSAS_FINANCEIRAS["incc"]
        resultado.premissas.append(Premissa(
            nome="INCC (projeção anual)",
            valor=ref_incc["medio"],
            unidade=ref_incc["unidade"],
            valor_min=ref_incc["min"],
            valor_max=ref_incc["max"],
            fonte=ref_incc["fonte"],
            categoria="Financeiro",
            subcategoria="Índices",
            descricao=f"{ref_incc['descricao']} — Indexador pré-chaves para incorporação",
        ))

    # --- Financiamento à produção: apenas Incorporação ---
    if e_incorporacao:
        premissas_fin_prod = {
            "financiamento_producao_taxa": (
                "Financiamento à produção - Taxa", "Financiamento à Produção"
            ),
            "financiamento_producao_carencia": (
                "Financiamento à produção - Carência", "Financiamento à Produção"
            ),
            "financiamento_producao_prazo": (
                "Financiamento à produção - Prazo", "Financiamento à Produção"
            ),
            "financiamento_producao_pct_custo": (
                "Financiamento à produção - % Custo financiado", "Financiamento à Produção"
            ),
        }
        for chave, (nome, subcat) in premissas_fin_prod.items():
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

    # --- CRI: apenas Incorporação (securitização de recebíveis) ---
    if e_incorporacao:
        mapeamento_cri = {
            "taxa_cdi_spread": ("CRI - Spread sobre CDI", "CRI"),
            "taxa_ipca_spread": ("CRI - Spread sobre IPCA", "CRI"),
            "prazo_operacao": ("CRI - Prazo da operação", "CRI"),
            "custo_emissao": ("CRI - Custos de emissão", "CRI"),
        }
        for chave, (nome, subcat) in mapeamento_cri.items():
            ref = PREMISSAS_CRI[chave]
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

    # --- Loteamento: Juros sobre carteira de recebíveis ---
    if e_loteamento:
        ref_tv = TABELA_VENDAS_LOTEAMENTO[inputs.padrao]
        resultado.premissas.append(Premissa(
            nome="Juros sobre carteira de recebíveis",
            valor=ref_tv["juros_am"],
            unidade="% a.m.",
            valor_min=0.50,
            valor_max=1.00,
            fonte="AELO, práticas de mercado de loteamentos",
            categoria="Financeiro",
            subcategoria="Carteira de Recebíveis",
            descricao="Taxa de juros mensal embutida nas parcelas do loteamento (Price/Gradiente)",
        ))
        resultado.premissas.append(Premissa(
            nome="Juros sobre carteira (equivalente anual)",
            valor=round(((1 + ref_tv["juros_am"] / 100) ** 12 - 1) * 100, 2),
            unidade="% a.a.",
            valor_min=round(((1 + 0.50 / 100) ** 12 - 1) * 100, 2),
            valor_max=round(((1 + 1.00 / 100) ** 12 - 1) * 100, 2),
            fonte="Calculado: (1 + juros_mensal)^12 - 1",
            categoria="Financeiro",
            subcategoria="Carteira de Recebíveis",
            descricao="Equivalente anual da taxa de juros sobre as parcelas",
            editavel=False,
        ))


def _gerar_tabela_vendas(
    resultado: ResultadoPremissas,
    inputs: InputsUsuario,
):
    """Gera a tabela de condições de vendas, diferenciada por tipologia."""
    if inputs.tipologia == Tipologia.LOTEAMENTO:
        # Tabela de Loteamento: Entrada + Parcelamento longo (Price/Gradiente)
        ref = TABELA_VENDAS_LOTEAMENTO[inputs.padrao]
        resultado.tabela_vendas_loteamento = TabelaVendasLoteamento(
            entrada_pct=ref["entrada_pct"],
            saldo_parcelado_pct=ref["saldo_parcelado_pct"],
            num_parcelas=ref["num_parcelas"],
            sistema_amortizacao=ref["sistema_amortizacao"],
            juros_am=ref["juros_am"],
            indexador=ref["indexador"],
            intermediarias_pct=ref["intermediarias_pct"],
            num_parcelas_entrada=ref["num_parcelas_entrada"],
        )
    else:
        # Tabela de Incorporação: Entrada + Obra + Financiamento na entrega
        ref = TABELA_VENDAS[inputs.tipologia][inputs.padrao]
        resultado.tabela_vendas = TabelaVendasIncorporacao(
            entrada_pct=ref["entrada"],
            parcelas_obra_pct=ref["parcelas_obra"],
            financiamento_pct=ref["financiamento"],
            reforcos_pct=ref["reforcos"],
            num_parcelas_obra=ref["num_parcelas"],
        )
