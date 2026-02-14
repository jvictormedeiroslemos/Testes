"""
Trinus Viabilidade - Simulador de DFC (Demonstração de Fluxo de Caixa).

Gera projeção mensal de fluxo de caixa e calcula indicadores de viabilidade
com base nas premissas sugeridas/editadas pelo usuário.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from modelos import ResultadoPremissas, Tipologia
from dados_mercado import CURVA_DESEMBOLSO


# ---------------------------------------------------------------------------
# Resultado da simulação
# ---------------------------------------------------------------------------
@dataclass
class ResultadoSimulacao:
    """Indicadores financeiros e fluxo de caixa projetado."""

    # === Totais ===
    vgv: float = 0.0
    receita_liquida: float = 0.0
    custo_total: float = 0.0
    despesa_total: float = 0.0
    resultado_projeto: float = 0.0

    # === Detalhamento de custos ===
    custo_terreno: float = 0.0
    custo_construcao_infra: float = 0.0
    custo_projetos_aprovacoes: float = 0.0
    custo_bdi: float = 0.0
    custo_outros: float = 0.0

    # === Detalhamento de despesas ===
    despesa_comercial: float = 0.0
    despesa_administrativa: float = 0.0
    despesa_tributaria: float = 0.0
    despesa_cartorial: float = 0.0

    # === Indicadores ===
    margem_vgv: float = 0.0       # % Resultado / VGV
    margem_custo: float = 0.0     # % Resultado / Custo Total
    tir_mensal: float = 0.0       # % IRR mensal
    tir_anual: float = 0.0        # % IRR anual
    vpl: float = 0.0              # VPL (R$)
    payback_meses: int = 0        # Meses até fluxo acumulado positivo
    exposicao_maxima: float = 0.0  # Maior saldo negativo acumulado (R$)
    lucro_sobre_investimento: float = 0.0  # Resultado / Exposição Máxima

    # === Fluxo mensal (para gráficos) ===
    total_meses: int = 0
    fluxo_mensal: list[float] = field(default_factory=list)
    fluxo_acumulado: list[float] = field(default_factory=list)
    receitas_mensais: list[float] = field(default_factory=list)
    custos_mensais: list[float] = field(default_factory=list)
    despesas_mensais: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_premissa_valor(resultado: ResultadoPremissas, nome: str, default: float = 0.0) -> float:
    """Busca o valor de uma premissa pelo nome."""
    p = resultado.get_premissa(nome)
    return p.valor if p else default


def _interpolar_curva(curva: list[tuple[float, float]], pct: float) -> float:
    """Interpola valor na curva de desembolso (pct de 0 a 1)."""
    pct = max(0.0, min(1.0, pct))
    for i in range(len(curva) - 1):
        x0, y0 = curva[i]
        x1, y1 = curva[i + 1]
        if x0 <= pct <= x1:
            if x1 == x0:
                return y0
            t = (pct - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return curva[-1][1]


def _calcular_tir(fluxos: list[float], max_iter: int = 500, tol: float = 1e-8) -> float | None:
    """Calcula TIR (IRR) usando método de Newton-Raphson com bisseção como fallback."""
    # Verificar se há fluxos positivos e negativos
    tem_positivo = any(f > 0 for f in fluxos)
    tem_negativo = any(f < 0 for f in fluxos)
    if not tem_positivo or not tem_negativo:
        return None

    # Newton-Raphson
    rate = 0.01  # chute inicial: 1% a.m.
    for _ in range(max_iter):
        npv = 0.0
        dnpv = 0.0
        for t, cf in enumerate(fluxos):
            denom = (1 + rate) ** t
            if denom == 0:
                break
            npv += cf / denom
            if t > 0:
                dnpv -= t * cf / ((1 + rate) ** (t + 1))
        if abs(npv) < tol:
            return rate
        if dnpv == 0:
            break
        rate_new = rate - npv / dnpv
        # Limitar saltos
        if rate_new < -0.5:
            rate_new = rate / 2
        if rate_new > 5.0:
            rate_new = (rate + 5.0) / 2
        rate = rate_new

    # Fallback: bisseção
    low, high = -0.5, 5.0
    for _ in range(max_iter):
        mid = (low + high) / 2
        npv = sum(cf / (1 + mid) ** t for t, cf in enumerate(fluxos) if (1 + mid) ** t != 0)
        if abs(npv) < tol:
            return mid
        if npv > 0:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _calcular_vpl(fluxos: list[float], taxa_mensal: float) -> float:
    """Calcula VPL (NPV) dada uma taxa mensal."""
    return sum(cf / (1 + taxa_mensal) ** t for t, cf in enumerate(fluxos))


# ---------------------------------------------------------------------------
# Motor de simulação
# ---------------------------------------------------------------------------
def simular(resultado: ResultadoPremissas) -> ResultadoSimulacao:
    """
    Executa simulação simplificada de DFC mês a mês.

    Usa as premissas (já com edições do usuário aplicadas) para projetar
    receitas, custos, despesas e calcular indicadores de viabilidade.
    """
    sim = ResultadoSimulacao()
    inputs = resultado.inputs
    e_loteamento = inputs.tipologia == Tipologia.LOTEAMENTO

    # ===================================================================
    # 1. Extrair premissas
    # ===================================================================
    vgv = _get_premissa_valor(resultado, "VGV estimado")
    sim.vgv = vgv
    if vgv <= 0:
        return sim

    ticket = _get_premissa_valor(resultado, "Ticket médio por unidade")
    num_unidades = inputs.num_unidades

    # Prazos
    prazo_obra = int(_get_premissa_valor(resultado, "Prazo de obra estimado", 24))
    prazo_registro = int(_get_premissa_valor(resultado, "Prazo para Registro de Incorporação/Loteamento", 6))

    # Curvas de vendas
    vendas_lancamento_pct = _get_premissa_valor(resultado, "Vendas no lançamento", 30) / 100
    vendas_obra_pct = _get_premissa_valor(resultado, "Vendas durante obra", 50) / 100
    vendas_pos_obra_pct = _get_premissa_valor(resultado, "Vendas pós-obra", 20) / 100

    # Receita
    distrato_pct = _get_premissa_valor(resultado, "Taxa de distrato estimada", 5) / 100
    inadimplencia_pct = _get_premissa_valor(resultado, "Taxa de inadimplência estimada", 5) / 100

    # Custos
    terreno_pct_vgv = _get_premissa_valor(resultado, "Custo do terreno (% VGV)") / 100
    bdi_pct = _get_premissa_valor(resultado, "Taxa de administração de obra (BDI)") / 100
    projetos_pct = _get_premissa_valor(resultado, "Custo de projetos e consultorias") / 100
    aprovacoes_pct = _get_premissa_valor(resultado, "Custo de aprovações e licenças") / 100
    iptu_pct = _get_premissa_valor(resultado, "IPTU do terreno") / 100

    if e_loteamento:
        custo_infra_m2 = _get_premissa_valor(resultado, "Custo de infraestrutura por m²")
        area_terreno = inputs.area_terreno_m2 or (num_unidades * 200)  # estimativa
        custo_construcao_base = custo_infra_m2 * area_terreno
    else:
        custo_m2 = _get_premissa_valor(resultado, "Custo de construção por m²")
        area_priv = _get_premissa_valor(resultado, "Área privativa média por unidade", 60)
        custo_construcao_base = custo_m2 * area_priv * num_unidades

    # Despesas (% do VGV)
    corretagem_pct = _get_premissa_valor(resultado, "Comissão de corretagem") / 100
    marketing_pct = _get_premissa_valor(resultado, "Marketing e publicidade") / 100
    stand_pct = _get_premissa_valor(resultado, "Stand de vendas") / 100
    coordenacao_pct = _get_premissa_valor(resultado, "Coordenação comercial") / 100
    premiacao_pct = _get_premissa_valor(resultado, "Premiação de corretores") / 100
    admin_pct = _get_premissa_valor(resultado, "Despesas administrativas") / 100
    gestao_pct = _get_premissa_valor(resultado, "Taxa de gestão do empreendimento") / 100
    seguros_pct = _get_premissa_valor(resultado, "Seguros") / 100
    preop_pct = _get_premissa_valor(resultado, "Despesas pré-operacionais") / 100
    aliquota_trib = _get_premissa_valor(resultado, "Alíquota tributária (regime sugerido)") / 100

    # Cartoriais
    ri_pct = _get_premissa_valor(resultado, "Registro de incorporação / loteamento") / 100
    escrituras_pct = _get_premissa_valor(resultado, "Custos com escrituras e registros do imóvel") / 100
    itbi_pct = _get_premissa_valor(resultado, "ITBI sobre aquisição do terreno (% valor terreno)") / 100

    # Financeiro
    tma_anual = _get_premissa_valor(resultado, "Taxa Mínima de Atratividade (TMA)", 15) / 100
    tma_mensal = (1 + tma_anual) ** (1 / 12) - 1

    # Tabela de vendas
    if e_loteamento and resultado.tabela_vendas_loteamento:
        tv = resultado.tabela_vendas_loteamento
        tv_entrada_pct = tv.entrada_pct / 100
        tv_saldo_pct = tv.saldo_parcelado_pct / 100
        tv_num_parcelas = tv.num_parcelas
        tv_num_parc_entrada = tv.num_parcelas_entrada
        tv_intermediarias_pct = tv.intermediarias_pct / 100
    elif resultado.tabela_vendas:
        tv = resultado.tabela_vendas
        tv_entrada_pct = tv.entrada_pct / 100
        tv_parcelas_obra_pct = tv.parcelas_obra_pct / 100
        tv_financiamento_pct = tv.financiamento_pct / 100
        tv_reforcos_pct = tv.reforcos_pct / 100
        tv_num_parcelas_obra = tv.num_parcelas_obra
    else:
        # Defaults
        tv_entrada_pct = 0.10
        if e_loteamento:
            tv_saldo_pct = 0.90
            tv_num_parcelas = 180
            tv_num_parc_entrada = 3
            tv_intermediarias_pct = 0
        else:
            tv_parcelas_obra_pct = 0.25
            tv_financiamento_pct = 0.55
            tv_reforcos_pct = 0.10
            tv_num_parcelas_obra = 24

    # ===================================================================
    # 2. Definir timeline
    # ===================================================================
    # Meses pós-obra para recebimentos residuais
    if e_loteamento:
        pos_obra_meses = min(tv_num_parcelas + 12, 300 - prazo_registro - prazo_obra)
    else:
        pos_obra_meses = 24  # 2 anos pós-obra para recebimentos

    total_meses = prazo_registro + prazo_obra + pos_obra_meses
    total_meses = max(total_meses, 36)
    sim.total_meses = total_meses

    # Mês de lançamento (após registro)
    mes_lancamento = prazo_registro
    # Mês de entrega/conclusão da obra
    mes_entrega = prazo_registro + prazo_obra

    # ===================================================================
    # 3. Cronograma de vendas (unidades vendidas por mês)
    # ===================================================================
    unidades_vendas = [0.0] * total_meses

    # Lançamento: primeiros 3 meses após registro
    meses_lancamento = 3
    un_lancamento = num_unidades * vendas_lancamento_pct
    for m in range(mes_lancamento, min(mes_lancamento + meses_lancamento, total_meses)):
        unidades_vendas[m] = un_lancamento / meses_lancamento

    # Obra: do mês 4 até o fim da obra
    meses_obra_venda = max(prazo_obra - meses_lancamento, 1)
    un_obra = num_unidades * vendas_obra_pct
    for m in range(mes_lancamento + meses_lancamento, min(mes_entrega, total_meses)):
        unidades_vendas[m] = un_obra / meses_obra_venda

    # Pós-obra: até 12 meses após entrega
    meses_pos_venda = 12
    un_pos = num_unidades * vendas_pos_obra_pct
    for m in range(mes_entrega, min(mes_entrega + meses_pos_venda, total_meses)):
        unidades_vendas[m] = un_pos / meses_pos_venda

    # Aplicar distrato (reduzir vendas líquidas)
    fator_liquido = 1 - distrato_pct

    # ===================================================================
    # 4. Cronograma de receitas (recebimentos mensais)
    # ===================================================================
    receitas = [0.0] * total_meses

    for m in range(total_meses):
        un = unidades_vendas[m] * fator_liquido
        if un <= 0:
            continue
        valor_venda = ticket * un

        if e_loteamento:
            # Entrada: distribuída em N parcelas
            valor_entrada = valor_venda * tv_entrada_pct
            for k in range(tv_num_parc_entrada):
                idx = m + k
                if idx < total_meses:
                    receitas[idx] += valor_entrada / tv_num_parc_entrada

            # Saldo parcelado
            valor_saldo = valor_venda * tv_saldo_pct
            inicio_saldo = m + tv_num_parc_entrada
            parcelas_efetivas = min(tv_num_parcelas, total_meses - inicio_saldo)
            if parcelas_efetivas > 0:
                parcela_mensal = valor_saldo / tv_num_parcelas
                for k in range(parcelas_efetivas):
                    receitas[inicio_saldo + k] += parcela_mensal

            # Intermediárias (anuais)
            if tv_intermediarias_pct > 0:
                valor_inter = valor_venda * tv_intermediarias_pct
                for ano in range(1, (total_meses - m) // 12 + 1):
                    idx = m + ano * 12
                    if idx < total_meses:
                        receitas[idx] += valor_inter / max(1, (total_meses - m) // 12)
        else:
            # Incorporação
            # Entrada: no ato da venda
            receitas[m] += valor_venda * tv_entrada_pct

            # Parcelas durante obra
            valor_parc = valor_venda * tv_parcelas_obra_pct
            parc_restantes = min(tv_num_parcelas_obra, max(mes_entrega - m, 1))
            if parc_restantes > 0:
                mensal = valor_parc / tv_num_parcelas_obra
                for k in range(1, tv_num_parcelas_obra + 1):
                    idx = m + k
                    if idx < total_meses:
                        receitas[idx] += mensal

            # Financiamento bancário: na entrega das chaves
            if mes_entrega < total_meses:
                receitas[mes_entrega] += valor_venda * tv_financiamento_pct

            # Reforços: a cada 6 meses até entrega
            if tv_reforcos_pct > 0:
                num_reforcos = max(1, (mes_entrega - m) // 6)
                valor_reforco = valor_venda * tv_reforcos_pct / num_reforcos
                for r in range(1, num_reforcos + 1):
                    idx = m + r * 6
                    if idx < total_meses:
                        receitas[idx] += valor_reforco

    # Aplicar inadimplência sobre receitas (redução)
    receitas = [r * (1 - inadimplencia_pct) for r in receitas]
    sim.receita_liquida = sum(receitas)

    # ===================================================================
    # 5. Cronograma de custos
    # ===================================================================
    custos = [0.0] * total_meses

    # Terreno: mês 0
    valor_terreno = vgv * terreno_pct_vgv
    sim.custo_terreno = valor_terreno
    if total_meses > 0:
        custos[0] += valor_terreno

    # ITBI sobre terreno
    itbi_valor = valor_terreno * itbi_pct
    if total_meses > 0:
        custos[0] += itbi_valor

    # Projetos: distribuído no período pré-lançamento
    valor_projetos = vgv * projetos_pct
    valor_aprovacoes = vgv * aprovacoes_pct
    sim.custo_projetos_aprovacoes = valor_projetos + valor_aprovacoes

    if prazo_registro > 0:
        mensal_proj = valor_projetos / prazo_registro
        for m in range(min(prazo_registro, total_meses)):
            custos[m] += mensal_proj
        # Aprovações: no final do registro
        idx_aprov = min(prazo_registro - 1, total_meses - 1)
        custos[idx_aprov] += valor_aprovacoes
    else:
        if total_meses > 0:
            custos[0] += valor_projetos + valor_aprovacoes

    # Construção: distribuída pela curva de desembolso durante obra
    custo_construcao_com_bdi = custo_construcao_base * (1 + bdi_pct)
    sim.custo_construcao_infra = custo_construcao_base
    sim.custo_bdi = custo_construcao_base * bdi_pct

    curva = CURVA_DESEMBOLSO.get(inputs.tipologia,
                                  CURVA_DESEMBOLSO[Tipologia.INCORPORACAO_VERTICAL])

    for m in range(prazo_obra):
        mes_real = mes_lancamento + m
        if mes_real >= total_meses:
            break
        pct_atual = (m + 1) / prazo_obra
        pct_anterior = m / prazo_obra
        desemb_atual = _interpolar_curva(curva, pct_atual) / 100
        desemb_anterior = _interpolar_curva(curva, pct_anterior) / 100
        custos[mes_real] += custo_construcao_com_bdi * (desemb_atual - desemb_anterior)

    # IPTU: mensal durante todo o projeto (até entrega)
    if valor_terreno > 0 and iptu_pct > 0:
        iptu_mensal = valor_terreno * iptu_pct / 12
        for m in range(min(mes_entrega + 1, total_meses)):
            custos[m] += iptu_mensal
        sim.custo_outros = iptu_mensal * min(mes_entrega + 1, total_meses) + itbi_valor

    sim.custo_total = sum(custos)

    # ===================================================================
    # 6. Cronograma de despesas
    # ===================================================================
    despesas = [0.0] * total_meses

    # --- Despesas pré-operacionais ---
    valor_preop = vgv * preop_pct
    if total_meses > 0:
        despesas[0] += valor_preop

    # --- RI (Registro de Incorporação) ---
    valor_ri = vgv * ri_pct
    if prazo_registro > 0 and prazo_registro < total_meses:
        despesas[prazo_registro - 1] += valor_ri
    elif total_meses > 0:
        despesas[0] += valor_ri

    # --- Comerciais: proporcionais às vendas ---
    total_comercial_pct = corretagem_pct + marketing_pct + stand_pct + coordenacao_pct + premiacao_pct

    for m in range(total_meses):
        if unidades_vendas[m] > 0:
            valor_vendido_mes = ticket * unidades_vendas[m]
            # Corretagem: sobre o valor vendido
            despesas[m] += valor_vendido_mes * corretagem_pct
            # Premiação: sobre o valor vendido
            despesas[m] += valor_vendido_mes * premiacao_pct

    # Marketing e stand: distribuídos ao longo do período de vendas
    periodo_vendas_inicio = mes_lancamento
    periodo_vendas_fim = min(mes_entrega + 12, total_meses)
    meses_vendas = max(periodo_vendas_fim - periodo_vendas_inicio, 1)

    valor_marketing = vgv * marketing_pct
    valor_stand = vgv * stand_pct
    valor_coord = vgv * coordenacao_pct

    for m in range(periodo_vendas_inicio, min(periodo_vendas_fim, total_meses)):
        despesas[m] += valor_marketing / meses_vendas
        despesas[m] += valor_coord / meses_vendas

    # Stand: concentrado no lançamento
    if mes_lancamento < total_meses:
        despesas[mes_lancamento] += valor_stand

    # --- Administrativas + Gestão: mensal ao longo do projeto ---
    meses_projeto = max(mes_entrega + 6, 12)  # até 6 meses pós-entrega
    admin_mensal = vgv * admin_pct / meses_projeto
    gestao_mensal = vgv * gestao_pct / meses_projeto
    for m in range(min(meses_projeto, total_meses)):
        despesas[m] += admin_mensal + gestao_mensal

    # --- Seguros: anual ---
    valor_seguros = vgv * seguros_pct
    anos_projeto = max(1, meses_projeto // 12)
    for ano in range(anos_projeto):
        idx = ano * 12
        if idx < total_meses:
            despesas[idx] += valor_seguros / anos_projeto

    # --- Escrituras e registros: na entrega ---
    valor_escrituras = vgv * escrituras_pct
    if mes_entrega < total_meses:
        despesas[mes_entrega] += valor_escrituras

    # --- Tributária: proporcional à receita recebida ---
    for m in range(total_meses):
        despesas[m] += receitas[m] * aliquota_trib

    # Totalizar despesas por tipo
    sim.despesa_comercial = vgv * total_comercial_pct
    sim.despesa_administrativa = vgv * (admin_pct + gestao_pct + seguros_pct + preop_pct)
    sim.despesa_tributaria = sim.receita_liquida * aliquota_trib
    sim.despesa_cartorial = vgv * (ri_pct + escrituras_pct) + valor_terreno * itbi_pct
    sim.despesa_total = sum(despesas)

    # ===================================================================
    # 7. Fluxo de caixa e indicadores
    # ===================================================================
    fluxo_mensal = [receitas[m] - custos[m] - despesas[m] for m in range(total_meses)]

    # Fluxo acumulado
    fluxo_acumulado = []
    acum = 0.0
    for f in fluxo_mensal:
        acum += f
        fluxo_acumulado.append(acum)

    sim.fluxo_mensal = fluxo_mensal
    sim.fluxo_acumulado = fluxo_acumulado
    sim.receitas_mensais = receitas
    sim.custos_mensais = custos
    sim.despesas_mensais = despesas

    # Resultado
    sim.resultado_projeto = sim.receita_liquida - sim.custo_total - sim.despesa_total

    # Margens
    if vgv > 0:
        sim.margem_vgv = (sim.resultado_projeto / vgv) * 100
    if sim.custo_total > 0:
        sim.margem_custo = (sim.resultado_projeto / sim.custo_total) * 100

    # Exposição máxima
    sim.exposicao_maxima = min(fluxo_acumulado) if fluxo_acumulado else 0.0

    # Payback
    sim.payback_meses = 0
    for m, acum_val in enumerate(fluxo_acumulado):
        if acum_val > 0:
            sim.payback_meses = m
            break
    else:
        sim.payback_meses = total_meses  # nunca atingiu

    # TIR
    # Remover zeros à direita para melhorar convergência
    fluxo_tir = list(fluxo_mensal)
    while len(fluxo_tir) > 2 and abs(fluxo_tir[-1]) < 0.01:
        fluxo_tir.pop()

    tir = _calcular_tir(fluxo_tir)
    if tir is not None:
        sim.tir_mensal = tir * 100
        sim.tir_anual = ((1 + tir) ** 12 - 1) * 100
    else:
        sim.tir_mensal = 0.0
        sim.tir_anual = 0.0

    # VPL
    sim.vpl = _calcular_vpl(fluxo_mensal, tma_mensal)

    # Lucro sobre investimento (Exposição Máxima)
    if sim.exposicao_maxima < 0:
        sim.lucro_sobre_investimento = (sim.resultado_projeto / abs(sim.exposicao_maxima)) * 100

    return sim
