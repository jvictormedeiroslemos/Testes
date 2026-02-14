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
    """Indicadores financeiros e fluxo de caixa projetado (estrutura DFC Trinus)."""

    # === VENDAS ===
    vgv: float = 0.0
    num_unidades_liquidas: float = 0.0   # Após distrato
    vgv_cancelado: float = 0.0           # VGV perdido por distrato

    # === RECEITA ===
    receita_bruta: float = 0.0           # Antes de inadimplência
    receita_liquida: float = 0.0         # Receita Líquida Operacional
    receita_entrada: float = 0.0         # Entrada / Sinal
    receita_parcelas: float = 0.0        # Mensais + Parcelas obra
    receita_intermediarias: float = 0.0  # Intermediárias / Reforços / Financiamento
    valor_inadimplencia: float = 0.0     # Perda por inadimplência
    valor_distrato: float = 0.0          # Perda por distratos na receita

    # === DEDUTORES DE RECEITA ===
    impostos_total: float = 0.0          # Imposto sobre receita (RET / LP)

    # === CUSTOS ===
    custo_total: float = 0.0

    # -- Custo de Obra --
    custo_obra_total: float = 0.0        # Subtotal obra
    custo_obra_raso: float = 0.0         # Custo raso de obra (construção/infra)
    custo_admin_obra: float = 0.0        # Administração de obra (BDI)
    custo_projetos: float = 0.0          # Projetos e consultorias
    custo_aprovacoes: float = 0.0        # Aprovações e licenças

    # -- Custo de Terreno --
    custo_terreno_total: float = 0.0     # Subtotal terreno
    custo_terreno_aquisicao: float = 0.0 # Aquisição do terreno
    custo_itbi: float = 0.0              # ITBI sobre aquisição do terreno
    custo_iptu: float = 0.0              # IPTU do terreno

    # Aliases mantidos para retrocompat com diagnóstico
    @property
    def custo_terreno(self) -> float:
        return self.custo_terreno_aquisicao

    @property
    def custo_construcao_infra(self) -> float:
        return self.custo_obra_raso

    @property
    def custo_bdi(self) -> float:
        return self.custo_admin_obra

    @property
    def custo_projetos_aprovacoes(self) -> float:
        return self.custo_projetos + self.custo_aprovacoes

    @property
    def custo_outros(self) -> float:
        return self.custo_itbi + self.custo_iptu

    # === DESPESAS ===
    despesa_total: float = 0.0

    # -- Despesas Comerciais --
    despesa_comercial: float = 0.0       # Subtotal comercial
    desp_comissoes: float = 0.0          # Comissões (corretagem)
    desp_premiacao: float = 0.0          # Premiação de corretores
    desp_stand: float = 0.0              # Stand de vendas / Central de vendas
    desp_coordenacao: float = 0.0        # Coordenação comercial

    # -- Despesas de Marketing --
    desp_marketing: float = 0.0

    # -- Despesas Administrativas --
    despesa_administrativa: float = 0.0  # Subtotal administrativo
    desp_admin: float = 0.0              # Despesas administrativas SPE
    desp_gestao: float = 0.0             # Taxa de gestão / Gerenciamento
    desp_seguros: float = 0.0            # Seguros
    desp_preop: float = 0.0              # Pré-operacionais / Desenvolvimento

    # -- Despesas Cartoriais --
    despesa_cartorial: float = 0.0       # Subtotal cartorial
    desp_ri: float = 0.0                 # Registro de incorporação / loteamento
    desp_escrituras: float = 0.0         # Escrituras e registros

    # -- Despesas Tributárias --
    despesa_tributaria: float = 0.0      # Impostos sobre receita

    # === RESULTADO ===
    atividades_operacionais: float = 0.0 # Receita - Dedutores - Custos - Despesas
    resultado_projeto: float = 0.0       # = Atividades operacionais

    # === INDICADORES ===
    margem_vgv: float = 0.0             # % Resultado / VGV
    margem_custo: float = 0.0           # % Resultado / Custo Total
    margem_receita_liq: float = 0.0     # % Resultado / Receita Líquida
    tir_mensal: float = 0.0             # % IRR mensal
    tir_anual: float = 0.0              # % IRR anual
    vpl: float = 0.0                    # VPL (R$)
    payback_meses: int = 0              # Meses até fluxo acumulado positivo
    exposicao_maxima: float = 0.0       # Maior saldo negativo acumulado (R$)
    lucro_sobre_investimento: float = 0.0  # Resultado / Exposição Máxima

    # === Fluxo mensal (para gráficos) ===
    total_meses: int = 0
    fluxo_mensal: list[float] = field(default_factory=list)
    fluxo_acumulado: list[float] = field(default_factory=list)
    receitas_mensais: list[float] = field(default_factory=list)
    custos_mensais: list[float] = field(default_factory=list)
    despesas_mensais: list[float] = field(default_factory=list)

    # === DFC Aberto — arrays mensais por sub-item ===
    # Vendas
    vendas_unidades_mensal: list[float] = field(default_factory=list)
    vendas_unidades_acum_mensal: list[float] = field(default_factory=list)
    vgv_vendido_mensal: list[float] = field(default_factory=list)

    # Receita (breakdown)
    rec_entrada_mensal: list[float] = field(default_factory=list)
    rec_parcelas_mensal: list[float] = field(default_factory=list)
    rec_intermediarias_mensal: list[float] = field(default_factory=list)
    inadimplencia_mensal: list[float] = field(default_factory=list)
    receita_bruta_mensal: list[float] = field(default_factory=list)

    # Dedutores de receita
    impostos_mensal: list[float] = field(default_factory=list)
    distratos_mensal: list[float] = field(default_factory=list)

    # Custos (breakdown)
    custo_terreno_aquisicao_mensal: list[float] = field(default_factory=list)
    custo_itbi_mensal: list[float] = field(default_factory=list)
    custo_iptu_mensal: list[float] = field(default_factory=list)
    custo_obra_raso_mensal: list[float] = field(default_factory=list)
    custo_admin_obra_mensal: list[float] = field(default_factory=list)
    custo_projetos_mensal: list[float] = field(default_factory=list)
    custo_aprovacoes_mensal: list[float] = field(default_factory=list)

    # Despesas (breakdown)
    desp_comissoes_mensal: list[float] = field(default_factory=list)
    desp_premiacao_mensal: list[float] = field(default_factory=list)
    desp_marketing_mensal: list[float] = field(default_factory=list)
    desp_stand_mensal: list[float] = field(default_factory=list)
    desp_coordenacao_mensal: list[float] = field(default_factory=list)
    desp_admin_mensal: list[float] = field(default_factory=list)
    desp_gestao_mensal: list[float] = field(default_factory=list)
    desp_seguros_mensal: list[float] = field(default_factory=list)
    desp_preop_mensal: list[float] = field(default_factory=list)
    desp_ri_mensal: list[float] = field(default_factory=list)
    desp_escrituras_mensal: list[float] = field(default_factory=list)
    desp_tributaria_mensal: list[float] = field(default_factory=list)

    # Resultado
    atividades_operacionais_mensal: list[float] = field(default_factory=list)
    saldo_caixa_mensal: list[float] = field(default_factory=list)


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
    sim.num_unidades_liquidas = num_unidades * fator_liquido
    sim.vgv_cancelado = vgv * distrato_pct

    # ===================================================================
    # 3.5. Rastrear vendas mensais para DFC Aberto
    # ===================================================================
    vendas_un_mensal = [0.0] * total_meses
    vendas_un_acum = [0.0] * total_meses
    vgv_vendido_m = [0.0] * total_meses
    acum_un = 0.0
    for m in range(total_meses):
        un_liq = unidades_vendas[m] * fator_liquido
        vendas_un_mensal[m] = un_liq
        acum_un += un_liq
        vendas_un_acum[m] = acum_un
        vgv_vendido_m[m] = ticket * un_liq
    sim.vendas_unidades_mensal = vendas_un_mensal
    sim.vendas_unidades_acum_mensal = vendas_un_acum
    sim.vgv_vendido_mensal = vgv_vendido_m

    # ===================================================================
    # 4. Cronograma de receitas (recebimentos mensais) — com breakdown
    # ===================================================================
    receitas = [0.0] * total_meses
    # Arrays por tipo de recebimento (para breakdown consistente)
    rec_entrada = [0.0] * total_meses
    rec_parcelas = [0.0] * total_meses
    rec_intermediarias = [0.0] * total_meses

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
                    v_parc = valor_entrada / tv_num_parc_entrada
                    receitas[idx] += v_parc
                    rec_entrada[idx] += v_parc

            # Saldo parcelado
            valor_saldo = valor_venda * tv_saldo_pct
            inicio_saldo = m + tv_num_parc_entrada
            parcelas_efetivas = min(tv_num_parcelas, total_meses - inicio_saldo)
            if parcelas_efetivas > 0:
                parcela_mensal = valor_saldo / tv_num_parcelas
                for k in range(parcelas_efetivas):
                    receitas[inicio_saldo + k] += parcela_mensal
                    rec_parcelas[inicio_saldo + k] += parcela_mensal

            # Intermediárias (anuais)
            if tv_intermediarias_pct > 0:
                valor_inter = valor_venda * tv_intermediarias_pct
                num_anos = max(1, (total_meses - m) // 12)
                for ano in range(1, num_anos + 1):
                    idx = m + ano * 12
                    if idx < total_meses:
                        v_inter = valor_inter / num_anos
                        receitas[idx] += v_inter
                        rec_intermediarias[idx] += v_inter
        else:
            # Incorporação
            # Entrada: no ato da venda
            v_ent = valor_venda * tv_entrada_pct
            receitas[m] += v_ent
            rec_entrada[m] += v_ent

            # Parcelas durante obra
            valor_parc = valor_venda * tv_parcelas_obra_pct
            if tv_num_parcelas_obra > 0:
                mensal = valor_parc / tv_num_parcelas_obra
                for k in range(1, tv_num_parcelas_obra + 1):
                    idx = m + k
                    if idx < total_meses:
                        receitas[idx] += mensal
                        rec_parcelas[idx] += mensal

            # Financiamento bancário: na entrega das chaves
            financ_valor = valor_venda * tv_financiamento_pct
            if mes_entrega < total_meses:
                receitas[mes_entrega] += financ_valor
                rec_intermediarias[mes_entrega] += financ_valor

            # Reforços: a cada 6 meses até entrega
            if tv_reforcos_pct > 0:
                valor_ref_total = valor_venda * tv_reforcos_pct
                num_reforcos = max(1, (mes_entrega - m) // 6)
                valor_reforco = valor_ref_total / num_reforcos
                for r in range(1, num_reforcos + 1):
                    idx = m + r * 6
                    if idx < total_meses:
                        receitas[idx] += valor_reforco
                        rec_intermediarias[idx] += valor_reforco

    # Receita bruta (antes de inadimplência) — breakdown é consistente com total
    receita_bruta_total = sum(receitas)
    sim.receita_bruta = receita_bruta_total
    sim.receita_entrada = sum(rec_entrada)
    sim.receita_parcelas = sum(rec_parcelas)
    sim.receita_intermediarias = sum(rec_intermediarias)

    # Guardar receita bruta mensal (antes de inadimplência) para DFC Aberto
    sim.receita_bruta_mensal = list(receitas)
    sim.rec_entrada_mensal = list(rec_entrada)
    sim.rec_parcelas_mensal = list(rec_parcelas)
    sim.rec_intermediarias_mensal = list(rec_intermediarias)

    # Aplicar inadimplência sobre receitas (redução)
    sim.valor_inadimplencia = receita_bruta_total * inadimplencia_pct
    sim.valor_distrato = vgv * distrato_pct  # VGV perdido por distrato
    inadimplencia_m = [r * inadimplencia_pct for r in receitas]
    sim.inadimplencia_mensal = inadimplencia_m
    receitas = [r * (1 - inadimplencia_pct) for r in receitas]
    sim.receita_liquida = sum(receitas)

    # ===================================================================
    # 5. Cronograma de custos — com breakdown individual
    # ===================================================================
    custos = [0.0] * total_meses
    # Arrays individuais por sub-item
    c_terreno_m = [0.0] * total_meses
    c_itbi_m = [0.0] * total_meses
    c_iptu_m = [0.0] * total_meses
    c_obra_raso_m = [0.0] * total_meses
    c_admin_obra_m = [0.0] * total_meses
    c_projetos_m = [0.0] * total_meses
    c_aprovacoes_m = [0.0] * total_meses

    # Terreno: mês 0
    valor_terreno = vgv * terreno_pct_vgv
    sim.custo_terreno_aquisicao = valor_terreno
    if total_meses > 0:
        custos[0] += valor_terreno
        c_terreno_m[0] += valor_terreno

    # ITBI sobre terreno
    itbi_valor = valor_terreno * itbi_pct
    sim.custo_itbi = itbi_valor
    if total_meses > 0:
        custos[0] += itbi_valor
        c_itbi_m[0] += itbi_valor

    # Projetos: distribuído no período pré-lançamento
    valor_projetos = vgv * projetos_pct
    valor_aprovacoes = vgv * aprovacoes_pct
    sim.custo_projetos = valor_projetos
    sim.custo_aprovacoes = valor_aprovacoes

    if prazo_registro > 0:
        mensal_proj = valor_projetos / prazo_registro
        for m in range(min(prazo_registro, total_meses)):
            custos[m] += mensal_proj
            c_projetos_m[m] += mensal_proj
        idx_aprov = min(prazo_registro - 1, total_meses - 1)
        custos[idx_aprov] += valor_aprovacoes
        c_aprovacoes_m[idx_aprov] += valor_aprovacoes
    else:
        if total_meses > 0:
            custos[0] += valor_projetos + valor_aprovacoes
            c_projetos_m[0] += valor_projetos
            c_aprovacoes_m[0] += valor_aprovacoes

    # Construção: distribuída pela curva de desembolso durante obra
    custo_construcao_com_bdi = custo_construcao_base * (1 + bdi_pct)
    sim.custo_obra_raso = custo_construcao_base
    sim.custo_admin_obra = custo_construcao_base * bdi_pct

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
        delta = desemb_atual - desemb_anterior
        valor_obra_mes = custo_construcao_base * delta
        valor_bdi_mes = custo_construcao_base * bdi_pct * delta
        custos[mes_real] += valor_obra_mes + valor_bdi_mes
        c_obra_raso_m[mes_real] += valor_obra_mes
        c_admin_obra_m[mes_real] += valor_bdi_mes

    # IPTU: mensal durante todo o projeto (até entrega)
    iptu_total = 0.0
    if valor_terreno > 0 and iptu_pct > 0:
        iptu_mensal = valor_terreno * iptu_pct / 12
        for m in range(min(mes_entrega + 1, total_meses)):
            custos[m] += iptu_mensal
            c_iptu_m[m] += iptu_mensal
        iptu_total = iptu_mensal * min(mes_entrega + 1, total_meses)
    sim.custo_iptu = iptu_total

    # Salvar arrays individuais
    sim.custo_terreno_aquisicao_mensal = c_terreno_m
    sim.custo_itbi_mensal = c_itbi_m
    sim.custo_iptu_mensal = c_iptu_m
    sim.custo_obra_raso_mensal = c_obra_raso_m
    sim.custo_admin_obra_mensal = c_admin_obra_m
    sim.custo_projetos_mensal = c_projetos_m
    sim.custo_aprovacoes_mensal = c_aprovacoes_m

    # Subtotais de custo
    sim.custo_obra_total = custo_construcao_base + sim.custo_admin_obra + valor_projetos + valor_aprovacoes
    sim.custo_terreno_total = valor_terreno + itbi_valor + iptu_total
    sim.custo_total = sum(custos)

    # ===================================================================
    # 6. Cronograma de despesas — com breakdown individual
    # ===================================================================
    despesas = [0.0] * total_meses
    # Arrays individuais por sub-item
    d_comissoes_m = [0.0] * total_meses
    d_premiacao_m = [0.0] * total_meses
    d_marketing_m = [0.0] * total_meses
    d_stand_m = [0.0] * total_meses
    d_coordenacao_m = [0.0] * total_meses
    d_admin_m = [0.0] * total_meses
    d_gestao_m = [0.0] * total_meses
    d_seguros_m = [0.0] * total_meses
    d_preop_m = [0.0] * total_meses
    d_ri_m = [0.0] * total_meses
    d_escrituras_m = [0.0] * total_meses
    d_tributaria_m = [0.0] * total_meses

    # --- Despesas pré-operacionais ---
    valor_preop = vgv * preop_pct
    sim.desp_preop = valor_preop
    if total_meses > 0:
        despesas[0] += valor_preop
        d_preop_m[0] += valor_preop

    # --- RI (Registro de Incorporação) ---
    valor_ri = vgv * ri_pct
    sim.desp_ri = valor_ri
    if prazo_registro > 0 and prazo_registro < total_meses:
        despesas[prazo_registro - 1] += valor_ri
        d_ri_m[prazo_registro - 1] += valor_ri
    elif total_meses > 0:
        despesas[0] += valor_ri
        d_ri_m[0] += valor_ri

    # --- Comerciais: proporcionais às vendas ---
    sim.desp_comissoes = vgv * corretagem_pct
    sim.desp_premiacao = vgv * premiacao_pct
    sim.desp_stand = vgv * stand_pct
    sim.desp_coordenacao = vgv * coordenacao_pct
    sim.desp_marketing = vgv * marketing_pct

    for m in range(total_meses):
        if unidades_vendas[m] > 0:
            valor_vendido_mes = ticket * unidades_vendas[m]
            v_com = valor_vendido_mes * corretagem_pct
            v_prem = valor_vendido_mes * premiacao_pct
            despesas[m] += v_com + v_prem
            d_comissoes_m[m] += v_com
            d_premiacao_m[m] += v_prem

    # Marketing e coordenação: distribuídos ao longo do período de vendas
    periodo_vendas_inicio = mes_lancamento
    periodo_vendas_fim = min(mes_entrega + 12, total_meses)
    meses_vendas = max(periodo_vendas_fim - periodo_vendas_inicio, 1)

    valor_marketing = vgv * marketing_pct
    valor_stand = vgv * stand_pct
    valor_coord = vgv * coordenacao_pct

    for m in range(periodo_vendas_inicio, min(periodo_vendas_fim, total_meses)):
        v_mkt = valor_marketing / meses_vendas
        v_coord = valor_coord / meses_vendas
        despesas[m] += v_mkt + v_coord
        d_marketing_m[m] += v_mkt
        d_coordenacao_m[m] += v_coord

    # Stand: concentrado no lançamento
    if mes_lancamento < total_meses:
        despesas[mes_lancamento] += valor_stand
        d_stand_m[mes_lancamento] += valor_stand

    # --- Administrativas + Gestão: mensal ao longo do projeto ---
    meses_projeto = max(mes_entrega + 6, 12)
    sim.desp_admin = vgv * admin_pct
    sim.desp_gestao = vgv * gestao_pct
    admin_mensal = vgv * admin_pct / meses_projeto
    gestao_mensal = vgv * gestao_pct / meses_projeto
    for m in range(min(meses_projeto, total_meses)):
        despesas[m] += admin_mensal + gestao_mensal
        d_admin_m[m] += admin_mensal
        d_gestao_m[m] += gestao_mensal

    # --- Seguros: anual ---
    valor_seguros = vgv * seguros_pct
    sim.desp_seguros = valor_seguros
    anos_projeto = max(1, meses_projeto // 12)
    for ano in range(anos_projeto):
        idx = ano * 12
        if idx < total_meses:
            v_seg = valor_seguros / anos_projeto
            despesas[idx] += v_seg
            d_seguros_m[idx] += v_seg

    # --- Escrituras e registros: na entrega ---
    valor_escrituras = vgv * escrituras_pct
    sim.desp_escrituras = valor_escrituras
    if mes_entrega < total_meses:
        despesas[mes_entrega] += valor_escrituras
        d_escrituras_m[mes_entrega] += valor_escrituras

    # --- Tributária: proporcional à receita recebida ---
    for m in range(total_meses):
        v_trib = receitas[m] * aliquota_trib
        despesas[m] += v_trib
        d_tributaria_m[m] += v_trib

    # Salvar arrays individuais de despesas
    sim.desp_comissoes_mensal = d_comissoes_m
    sim.desp_premiacao_mensal = d_premiacao_m
    sim.desp_marketing_mensal = d_marketing_m
    sim.desp_stand_mensal = d_stand_m
    sim.desp_coordenacao_mensal = d_coordenacao_m
    sim.desp_admin_mensal = d_admin_m
    sim.desp_gestao_mensal = d_gestao_m
    sim.desp_seguros_mensal = d_seguros_m
    sim.desp_preop_mensal = d_preop_m
    sim.desp_ri_mensal = d_ri_m
    sim.desp_escrituras_mensal = d_escrituras_m
    sim.desp_tributaria_mensal = d_tributaria_m

    # Totalizar despesas por tipo
    sim.despesa_comercial = (sim.desp_comissoes + sim.desp_premiacao +
                             sim.desp_stand + sim.desp_coordenacao)
    sim.despesa_administrativa = (sim.desp_admin + sim.desp_gestao +
                                  sim.desp_seguros + sim.desp_preop)
    sim.despesa_tributaria = sim.receita_liquida * aliquota_trib
    sim.impostos_total = sim.despesa_tributaria
    sim.despesa_cartorial = valor_ri + valor_escrituras
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

    # DFC Aberto — impostos e resultado operacional mensal
    sim.impostos_mensal = list(d_tributaria_m)
    sim.distratos_mensal = [0.0] * total_meses  # distrato já descontado nas vendas
    sim.atividades_operacionais_mensal = list(fluxo_mensal)
    sim.saldo_caixa_mensal = list(fluxo_acumulado)

    # Resultado (despesa_total já inclui tributária)
    sim.resultado_projeto = sim.receita_liquida - sim.custo_total - sim.despesa_total
    sim.atividades_operacionais = sim.resultado_projeto

    # Margens
    if vgv > 0:
        sim.margem_vgv = (sim.resultado_projeto / vgv) * 100
    if sim.custo_total > 0:
        sim.margem_custo = (sim.resultado_projeto / sim.custo_total) * 100
    if sim.receita_liquida > 0:
        sim.margem_receita_liq = (sim.resultado_projeto / sim.receita_liquida) * 100

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


# ---------------------------------------------------------------------------
# Diagnóstico e recomendações
# ---------------------------------------------------------------------------
@dataclass
class ItemDiagnostico:
    """Um item do diagnóstico com nível de severidade."""
    categoria: str        # "receita", "custo", "despesa", "financeiro", "tese"
    severidade: str       # "critico", "atencao", "positivo"
    titulo: str
    descricao: str
    premissa_atual: str   # Valor atual formatado
    benchmark: str        # Valor de referência/benchmark
    sugestao: str         # O que fazer para melhorar


def gerar_diagnostico(
    resultado: ResultadoPremissas,
    sim: ResultadoSimulacao,
) -> list[ItemDiagnostico]:
    """
    Gera diagnóstico completo comparando premissas atuais com benchmarks de mercado.

    Analisa cada premissa e identifica os principais ofensores do resultado,
    sugerindo ações concretas para viabilizar ou melhorar o projeto.
    """
    itens: list[ItemDiagnostico] = []
    inputs = resultado.inputs
    e_loteamento = inputs.tipologia == Tipologia.LOTEAMENTO
    vgv = sim.vgv

    if vgv <= 0:
        return itens

    # ===================================================================
    # 1. ANÁLISE DE RECEITA
    # ===================================================================

    # --- Distrato ---
    distrato = _get_premissa_valor(resultado, "Taxa de distrato estimada", 0)
    if e_loteamento:
        bench_distrato = 12.0
        limite_alto = 18.0
    else:
        bench_distrato = 8.0
        limite_alto = 15.0

    if distrato > limite_alto:
        itens.append(ItemDiagnostico(
            categoria="receita",
            severidade="critico",
            titulo="Distrato muito elevado",
            descricao=(
                f"A taxa de distrato de {distrato:.1f}% está muito acima do benchmark "
                f"de mercado ({bench_distrato:.0f}%). Isso significa que uma parcela "
                f"significativa das vendas é perdida, reduzindo a receita líquida."
            ),
            premissa_atual=f"{distrato:.1f}%",
            benchmark=f"{bench_distrato:.0f}%",
            sugestao=(
                "Reforçar a análise de crédito dos compradores, exigir maior "
                "percentual de entrada (sinal), implementar política de retenção "
                "com renegociação antes do distrato, e melhorar o processo de "
                "pós-venda. Considerar incluir cláusula de multa rescisória de 20-25%."
            ),
        ))
    elif distrato > bench_distrato:
        itens.append(ItemDiagnostico(
            categoria="receita",
            severidade="atencao",
            titulo="Distrato acima do padrão",
            descricao=(
                f"A taxa de distrato de {distrato:.1f}% está acima do benchmark "
                f"({bench_distrato:.0f}%). Margem para otimização."
            ),
            premissa_atual=f"{distrato:.1f}%",
            benchmark=f"{bench_distrato:.0f}%",
            sugestao=(
                "Melhorar a qualificação do comprador na venda e oferecer "
                "condições de renegociação antes de formalizar o distrato."
            ),
        ))

    # --- Inadimplência ---
    inadimplencia = _get_premissa_valor(resultado, "Taxa de inadimplência estimada", 0)
    if e_loteamento:
        bench_inadimp = 15.0
        limite_alto_inadimp = 25.0
    else:
        bench_inadimp = 5.0
        limite_alto_inadimp = 10.0

    if inadimplencia > limite_alto_inadimp:
        itens.append(ItemDiagnostico(
            categoria="receita",
            severidade="critico",
            titulo="Inadimplência muito elevada",
            descricao=(
                f"A inadimplência de {inadimplencia:.1f}% está muito acima do "
                f"benchmark ({bench_inadimp:.0f}%), causando perda significativa "
                f"de receita efetiva."
            ),
            premissa_atual=f"{inadimplencia:.1f}%",
            benchmark=f"{bench_inadimp:.0f}%",
            sugestao=(
                "Implementar cobrança ativa com régua de cobrança automatizada. "
                "Exigir maior entrada para comprometimento do comprador. "
                "Em loteamentos, considerar alienação fiduciária para facilitar "
                "retomada e revenda. Reforçar análise de crédito pré-venda."
            ),
        ))
    elif inadimplencia > bench_inadimp:
        itens.append(ItemDiagnostico(
            categoria="receita",
            severidade="atencao",
            titulo="Inadimplência acima do padrão",
            descricao=(
                f"Inadimplência de {inadimplencia:.1f}% está acima do benchmark "
                f"({bench_inadimp:.0f}%)."
            ),
            premissa_atual=f"{inadimplencia:.1f}%",
            benchmark=f"{bench_inadimp:.0f}%",
            sugestao=(
                "Reforçar cobrança e considerar ajuste na tabela de vendas "
                "com maior percentual de entrada."
            ),
        ))

    # --- Velocidade de vendas ---
    velocidade = _get_premissa_valor(resultado, "Velocidade de vendas", 0)
    bench_vel = 3.5 if e_loteamento else 3.0
    if velocidade < 2.0:
        itens.append(ItemDiagnostico(
            categoria="receita",
            severidade="critico",
            titulo="Velocidade de vendas muito baixa",
            descricao=(
                f"Velocidade de {velocidade:.1f}% do estoque/mês implica em "
                f"período de vendas muito longo, aumentando custo financeiro "
                f"e exposição do projeto."
            ),
            premissa_atual=f"{velocidade:.1f}%/mês",
            benchmark=f"{bench_vel:.1f}%/mês",
            sugestao=(
                "Reavaliar o posicionamento do produto: preço, localização, "
                "concorrência. Aumentar investimento em marketing e stand de vendas. "
                "Considerar parcerias com imobiliárias locais ou plataformas digitais. "
                "Verificar se o produto está adequado ao público da região."
            ),
        ))

    # --- Vendas no lançamento ---
    vendas_lanc = _get_premissa_valor(resultado, "Vendas no lançamento", 0)
    if vendas_lanc < 25:
        itens.append(ItemDiagnostico(
            categoria="receita",
            severidade="atencao",
            titulo="Baixa concentração de vendas no lançamento",
            descricao=(
                f"Apenas {vendas_lanc:.0f}% das vendas no lançamento. O ideal é "
                f"concentrar 30-50% para antecipar receita e reduzir exposição."
            ),
            premissa_atual=f"{vendas_lanc:.0f}%",
            benchmark="30-50%",
            sugestao=(
                "Investir em pré-lançamento e lista de espera. Oferecer condições "
                "especiais para os primeiros compradores (tabela de lançamento). "
                "Garantir stand de vendas pronto e equipe comercial treinada antes "
                "do lançamento."
            ),
        ))

    # ===================================================================
    # 2. ANÁLISE DE CUSTOS
    # ===================================================================

    # --- Terreno ---
    terreno_pct = _get_premissa_valor(resultado, "Custo do terreno (% VGV)", 0)
    bench_terreno = 15.0
    if terreno_pct > 22:
        itens.append(ItemDiagnostico(
            categoria="custo",
            severidade="critico",
            titulo="Custo do terreno excessivo",
            descricao=(
                f"O terreno representa {terreno_pct:.1f}% do VGV, muito acima do "
                f"benchmark de {bench_terreno:.0f}%. Este é tipicamente o maior "
                f"ofensor de viabilidade em projetos imobiliários."
            ),
            premissa_atual=f"{terreno_pct:.1f}% do VGV",
            benchmark=f"{bench_terreno:.0f}% do VGV",
            sugestao=(
                "Renegociar o terreno para modelo de permuta física ou permuta "
                "financeira, reduzindo desembolso inicial. Avaliar se o preço de "
                "venda (VGV) comporta o custo do terreno — se não, considerar "
                "aumentar a densidade do projeto (mais unidades) para diluir o "
                "custo. Em último caso, buscar outro terreno com melhor relação "
                "custo/VGV."
            ),
        ))
    elif terreno_pct > 18:
        itens.append(ItemDiagnostico(
            categoria="custo",
            severidade="atencao",
            titulo="Custo do terreno elevado",
            descricao=(
                f"Terreno a {terreno_pct:.1f}% do VGV está acima do ideal "
                f"({bench_terreno:.0f}%). Há espaço para otimização."
            ),
            premissa_atual=f"{terreno_pct:.1f}% do VGV",
            benchmark=f"{bench_terreno:.0f}% do VGV",
            sugestao=(
                "Negociar permuta parcial (parte em dinheiro, parte em unidades). "
                "Reavaliar o potencial construtivo para aumentar o VGV do projeto."
            ),
        ))

    # --- Custo de construção / infraestrutura ---
    custo_constr_pct = (sim.custo_construcao_infra / vgv * 100) if vgv > 0 else 0
    bench_construcao = 35.0 if e_loteamento else 40.0
    if custo_constr_pct > bench_construcao * 1.3:
        itens.append(ItemDiagnostico(
            categoria="custo",
            severidade="critico",
            titulo=f"Custo de {'infraestrutura' if e_loteamento else 'construção'} muito elevado",
            descricao=(
                f"O custo de {'infraestrutura' if e_loteamento else 'construção'} "
                f"representa {custo_constr_pct:.1f}% do VGV, acima do benchmark "
                f"de {bench_construcao:.0f}%. Este custo comprime diretamente a margem."
            ),
            premissa_atual=f"{custo_constr_pct:.1f}% do VGV",
            benchmark=f"até {bench_construcao:.0f}% do VGV",
            sugestao=(
                "Revisar o memorial descritivo para adequar o padrão construtivo "
                "ao público-alvo. Buscar fornecedores alternativos e considerar "
                "compras em escala. Reavaliar se o padrão (econômico/médio/alto) "
                "está coerente com o mercado local. Se o custo for incompressível, "
                "verificar possibilidade de aumentar o preço de venda."
            ),
        ))
    elif custo_constr_pct > bench_construcao:
        itens.append(ItemDiagnostico(
            categoria="custo",
            severidade="atencao",
            titulo=f"Custo de {'infraestrutura' if e_loteamento else 'construção'} acima do padrão",
            descricao=(
                f"{'Infraestrutura' if e_loteamento else 'Construção'} a "
                f"{custo_constr_pct:.1f}% do VGV, acima do benchmark ({bench_construcao:.0f}%)."
            ),
            premissa_atual=f"{custo_constr_pct:.1f}% do VGV",
            benchmark=f"{bench_construcao:.0f}% do VGV",
            sugestao=(
                "Buscar otimizações na engenharia de valor. Considerar "
                "construtabilidade e racionalização de projetos."
            ),
        ))

    # --- BDI ---
    bdi = _get_premissa_valor(resultado, "Taxa de administração de obra (BDI)", 0)
    bench_bdi = 15.0
    if bdi > 20:
        itens.append(ItemDiagnostico(
            categoria="custo",
            severidade="atencao",
            titulo="BDI elevado",
            descricao=(
                f"O BDI de {bdi:.1f}% está acima do benchmark de {bench_bdi:.0f}%. "
                f"Isso encarece o custo total de obra."
            ),
            premissa_atual=f"{bdi:.1f}%",
            benchmark=f"{bench_bdi:.0f}%",
            sugestao=(
                "Negociar a taxa com a construtora ou considerar construção "
                "por administração com controle mais rigoroso de custos."
            ),
        ))

    # ===================================================================
    # 3. ANÁLISE DE DESPESAS
    # ===================================================================

    # --- Despesas comerciais totais ---
    total_comercial_pct = (sim.despesa_comercial / vgv * 100) if vgv > 0 else 0
    bench_comercial = 9.0
    if total_comercial_pct > 12:
        itens.append(ItemDiagnostico(
            categoria="despesa",
            severidade="critico",
            titulo="Despesas comerciais excessivas",
            descricao=(
                f"As despesas comerciais totalizam {total_comercial_pct:.1f}% do VGV "
                f"(benchmark: até {bench_comercial:.0f}%). Corretagem, marketing, "
                f"stand e premiação estão consumindo margem excessiva."
            ),
            premissa_atual=f"{total_comercial_pct:.1f}% do VGV",
            benchmark=f"até {bench_comercial:.0f}% do VGV",
            sugestao=(
                "Renegociar taxa de corretagem (mercado pratica 4-5%). "
                "Reduzir investimento em stand optando por decorados digitais "
                "ou studios menores. Focar marketing em digital (menor custo por lead). "
                "Condicionar premiação a metas de velocidade de vendas."
            ),
        ))
    elif total_comercial_pct > bench_comercial:
        itens.append(ItemDiagnostico(
            categoria="despesa",
            severidade="atencao",
            titulo="Despesas comerciais acima do padrão",
            descricao=(
                f"Despesas comerciais em {total_comercial_pct:.1f}% do VGV. "
                f"Benchmark: {bench_comercial:.0f}%."
            ),
            premissa_atual=f"{total_comercial_pct:.1f}% do VGV",
            benchmark=f"{bench_comercial:.0f}% do VGV",
            sugestao=(
                "Rever estrutura comercial e buscar eficiências em marketing."
            ),
        ))

    # --- Alíquota tributária ---
    aliquota = _get_premissa_valor(resultado, "Alíquota tributária (regime sugerido)", 0)
    if aliquota >= 6.0:
        itens.append(ItemDiagnostico(
            categoria="despesa",
            severidade="atencao",
            titulo="Carga tributária elevada",
            descricao=(
                f"A alíquota de {aliquota:.2f}% (Lucro Presumido) é significativamente "
                f"maior que o RET (4%) ou RET-MCMV (1%). Considerar regime especial."
            ),
            premissa_atual=f"{aliquota:.2f}%",
            benchmark="4,00% (RET) ou 1,00% (RET-MCMV)",
            sugestao=(
                "Avaliar enquadramento no RET (Regime Especial de Tributação) "
                "que unifica PIS, COFINS, IRPJ e CSLL em alíquota de 4%. "
                "Para empreendimentos MCMV Faixa 1, a alíquota cai para 1%. "
                "Constituir SPE para cada empreendimento para elegibilidade ao RET."
            ),
        ))

    # --- Despesas administrativas + gestão ---
    admin_pct = _get_premissa_valor(resultado, "Despesas administrativas", 0)
    gestao_pct = _get_premissa_valor(resultado, "Taxa de gestão do empreendimento", 0)
    total_adm = admin_pct + gestao_pct
    bench_adm = 4.0
    if total_adm > 6:
        itens.append(ItemDiagnostico(
            categoria="despesa",
            severidade="atencao",
            titulo="Despesas administrativas elevadas",
            descricao=(
                f"Administrativa + Gestão = {total_adm:.1f}% do VGV "
                f"(benchmark: até {bench_adm:.0f}%)."
            ),
            premissa_atual=f"{total_adm:.1f}% do VGV",
            benchmark=f"até {bench_adm:.0f}% do VGV",
            sugestao=(
                "Otimizar estrutura administrativa da SPE. Compartilhar "
                "custos fixos entre empreendimentos da mesma incorporadora. "
                "Considerar terceirização de backoffice."
            ),
        ))

    # ===================================================================
    # 4. ANÁLISE FINANCEIRA
    # ===================================================================

    # --- TMA ---
    tma = _get_premissa_valor(resultado, "Taxa Mínima de Atratividade (TMA)", 0)
    if tma > 18 and sim.vpl < 0:
        itens.append(ItemDiagnostico(
            categoria="financeiro",
            severidade="atencao",
            titulo="TMA muito conservadora",
            descricao=(
                f"A TMA de {tma:.1f}% a.a. é bastante conservadora. "
                f"Se o VPL é negativo, pode ser que o projeto seja viável "
                f"a uma taxa menor, mais condizente com o mercado atual."
            ),
            premissa_atual=f"{tma:.1f}% a.a.",
            benchmark="12-15% a.a.",
            sugestao=(
                "Reavaliar se a TMA está compatível com o custo de oportunidade "
                "real do capital investido. Taxas de 12-15% a.a. são mais comuns "
                "para projetos imobiliários de médio risco."
            ),
        ))

    # ===================================================================
    # 5. ANÁLISE DA TESE DE NEGÓCIO
    # ===================================================================

    # --- Margem geral ---
    custo_mais_desp_pct = ((sim.custo_total + sim.despesa_total) / vgv * 100) if vgv > 0 else 0
    if sim.margem_vgv < 10:
        if custo_constr_pct > bench_construcao and terreno_pct > 18:
            itens.append(ItemDiagnostico(
                categoria="tese",
                severidade="critico",
                titulo="Relação custo/receita desfavorável",
                descricao=(
                    f"Custos + Despesas representam {custo_mais_desp_pct:.0f}% do VGV, "
                    f"deixando margem de apenas {sim.margem_vgv:.1f}%. "
                    f"Terreno ({terreno_pct:.1f}%) e Construção ({custo_constr_pct:.1f}%) "
                    f"são os dois maiores ofensores."
                ),
                premissa_atual=f"Margem {sim.margem_vgv:.1f}%",
                benchmark="Margem mínima 15-20%",
                sugestao=(
                    "A tese de negócio precisa de ajuste estrutural. Opções:\n"
                    "1. **Renegociar o terreno**: permuta financeira ou física para "
                    "reduzir de {:.0f}% para até 15% do VGV.\n"
                    "2. **Aumentar o VGV**: avaliar aumento de preço/m², aumento de "
                    "unidades ou melhoria do mix de produto.\n"
                    "3. **Reduzir custo de construção**: racionalizar memorial "
                    "descritivo e buscar engenharia de valor.\n"
                    "4. **Combinar**: pequenas melhorias em várias premissas podem "
                    "somar o ganho de margem necessário."
                ).format(terreno_pct),
            ))
        elif terreno_pct > 20:
            itens.append(ItemDiagnostico(
                categoria="tese",
                severidade="critico",
                titulo="Terreno compromete a viabilidade",
                descricao=(
                    f"O custo do terreno ({terreno_pct:.1f}% do VGV) é o principal "
                    f"ofensor. Com margem de {sim.margem_vgv:.1f}%, o projeto não "
                    f"se sustenta."
                ),
                premissa_atual=f"Terreno {terreno_pct:.1f}% do VGV",
                benchmark="até 15% do VGV",
                sugestao=(
                    "Priorize a renegociação do terreno: converter compra em permuta "
                    "física (entrega de unidades ao proprietário) ou permuta financeira "
                    "(pagamento com % da receita). Isso elimina ou reduz significativamente "
                    "o desembolso inicial e melhora TIR e Payback."
                ),
            ))
        else:
            itens.append(ItemDiagnostico(
                categoria="tese",
                severidade="atencao",
                titulo="Margem apertada",
                descricao=(
                    f"Margem de {sim.margem_vgv:.1f}% está abaixo do mínimo recomendado "
                    f"(15-20%). Custos + Despesas = {custo_mais_desp_pct:.0f}% do VGV."
                ),
                premissa_atual=f"Margem {sim.margem_vgv:.1f}%",
                benchmark="15-20%",
                sugestao=(
                    "Revisar cada linha de custo e despesa buscando pequenas "
                    "otimizações que somem ganho de margem. Considerar aumento "
                    "de preço de venda se o mercado comportar."
                ),
            ))

    # --- Payback ---
    prazo_obra = int(_get_premissa_valor(resultado, "Prazo de obra estimado", 24))
    prazo_total_ref = prazo_obra + 12  # obra + 1 ano
    if sim.payback_meses > prazo_total_ref * 1.5 and sim.payback_meses < sim.total_meses:
        itens.append(ItemDiagnostico(
            categoria="tese",
            severidade="atencao",
            titulo="Payback longo",
            descricao=(
                f"O payback de {sim.payback_meses} meses ({sim.payback_meses / 12:.1f} anos) "
                f"é longo para a tipologia. O ideal é recuperar o investimento em até "
                f"{prazo_total_ref} meses."
            ),
            premissa_atual=f"{sim.payback_meses} meses",
            benchmark=f"até {prazo_total_ref} meses",
            sugestao=(
                "Acelerar vendas no lançamento (concentrar mais % no lançamento). "
                "Aumentar percentual de entrada na tabela de vendas para antecipar "
                "receita. Avaliar financiamento à produção para desafogar caixa "
                "durante a obra."
            ),
        ))

    # --- Exposição máxima ---
    exposicao_pct_vgv = (abs(sim.exposicao_maxima) / vgv * 100) if vgv > 0 else 0
    if exposicao_pct_vgv > 50:
        itens.append(ItemDiagnostico(
            categoria="financeiro",
            severidade="critico",
            titulo="Exposição máxima muito alta",
            descricao=(
                f"A exposição máxima de R$ {abs(sim.exposicao_maxima):,.0f} "
                f"({exposicao_pct_vgv:.0f}% do VGV) significa que o incorporador "
                f"precisa de capital próprio muito elevado."
            ),
            premissa_atual=f"R$ {abs(sim.exposicao_maxima):,.0f} ({exposicao_pct_vgv:.0f}% VGV)",
            benchmark="até 35-40% do VGV",
            sugestao=(
                "Utilizar financiamento à produção (linha bancária de 50-80% "
                "do custo de obra) para reduzir capital próprio necessário. "
                "Negociar terreno em permuta para eliminar desembolso inicial. "
                "Concentrar vendas no lançamento para antecipar entradas de caixa."
            ),
        ))
    elif exposicao_pct_vgv > 35:
        itens.append(ItemDiagnostico(
            categoria="financeiro",
            severidade="atencao",
            titulo="Exposição de caixa elevada",
            descricao=(
                f"Exposição de {exposicao_pct_vgv:.0f}% do VGV. Capital próprio "
                f"necessário é significativo."
            ),
            premissa_atual=f"{exposicao_pct_vgv:.0f}% do VGV",
            benchmark="até 30-35% do VGV",
            sugestao=(
                "Considerar financiamento à produção e/ou CRI para aliviar "
                "a necessidade de capital próprio."
            ),
        ))

    # ===================================================================
    # 6. PONTOS POSITIVOS (para equilibrar o diagnóstico)
    # ===================================================================
    if sim.margem_vgv >= 20:
        itens.append(ItemDiagnostico(
            categoria="tese",
            severidade="positivo",
            titulo="Margem saudável",
            descricao=f"Margem de {sim.margem_vgv:.1f}% está acima do benchmark de 20%.",
            premissa_atual=f"{sim.margem_vgv:.1f}%",
            benchmark="20%",
            sugestao="Manter premissas atuais. Projeto com boa folga de rentabilidade.",
        ))

    if sim.tir_anual >= 20:
        itens.append(ItemDiagnostico(
            categoria="financeiro",
            severidade="positivo",
            titulo="TIR atrativa",
            descricao=f"TIR de {sim.tir_anual:.1f}% a.a. está acima da TMA.",
            premissa_atual=f"{sim.tir_anual:.1f}% a.a.",
            benchmark=f"{tma:.1f}% a.a. (TMA)",
            sugestao="Projeto remunera bem o capital investido.",
        ))

    if terreno_pct <= 12:
        itens.append(ItemDiagnostico(
            categoria="custo",
            severidade="positivo",
            titulo="Terreno com boa relação custo/VGV",
            descricao=f"Custo do terreno a {terreno_pct:.1f}% do VGV está abaixo do benchmark.",
            premissa_atual=f"{terreno_pct:.1f}%",
            benchmark="até 15%",
            sugestao="Excelente negociação de terreno. Contribui positivamente para a margem.",
        ))

    if vendas_lanc >= 40:
        itens.append(ItemDiagnostico(
            categoria="receita",
            severidade="positivo",
            titulo="Boa concentração de vendas no lançamento",
            descricao=f"{vendas_lanc:.0f}% de vendas no lançamento antecipa receita.",
            premissa_atual=f"{vendas_lanc:.0f}%",
            benchmark="30-50%",
            sugestao="Manter estratégia de pré-lançamento. Contribui para melhor TIR e payback.",
        ))

    # Ordenar: críticos primeiro, depois atenção, depois positivos
    ordem = {"critico": 0, "atencao": 1, "positivo": 2}
    itens.sort(key=lambda x: ordem.get(x.severidade, 1))

    return itens
