"""
Trinus Viabilidade - Gerador de Premissas de Viabilidade Imobiliária.

Interface Streamlit tipo wizard para coleta de inputs mínimos e
sugestão automática de premissas de mercado.

Uso:
    streamlit run app.py
"""

import sys
from pathlib import Path

# Garantir que o diretório do app está no path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st

from modelos import (
    ESTADOS_BRASIL,
    PADROES_POR_TIPOLOGIA,
    InputsUsuario,
    Padrao,
    Tipologia,
    TipoNegociacao,
)
from engine import gerar_premissas
from engine_ia import gerar_premissas_com_ia
from exportador import (
    exportar_excel_bytes,
    exportar_json_bytes,
    inputs_para_dataframe,
    premissas_para_dataframe,
    tabela_vendas_para_dataframe,
)
from simulador import simular
from cidades import CIDADES_POR_ESTADO

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Trinus Viabilidade | Gerador de Premissas",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS customizado
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stMetric > div {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px;
    }
    div[data-testid="stExpander"] details summary p {
        font-size: 1.1rem;
        font-weight: 600;
    }
    .main .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Estado da sessão
# ---------------------------------------------------------------------------
if "etapa" not in st.session_state:
    st.session_state["etapa"] = 1
if "resultado" not in st.session_state:
    st.session_state["resultado"] = None
if "premissas_editadas" not in st.session_state:
    st.session_state["premissas_editadas"] = {}
if "ia_metadata" not in st.session_state:
    st.session_state["ia_metadata"] = None


def ir_para_etapa(n: int):
    st.session_state["etapa"] = n


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/building.png", width=64)
    st.title("Trinus Viabilidade")
    st.markdown("**Gerador de Premissas**")
    st.markdown("---")

    etapa_atual = st.session_state["etapa"]
    etapas = [
        "1. Dados do Empreendimento",
        "2. Informações Complementares",
        "3. Premissas Sugeridas",
        "4. Exportar Resultados",
    ]
    for i, nome in enumerate(etapas, 1):
        if i == etapa_atual:
            st.markdown(f"**→ {nome}**")
        elif i < etapa_atual:
            st.markdown(f"~~{nome}~~")
        else:
            st.markdown(f"{nome}")

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Integração com IA
    # -----------------------------------------------------------------------
    st.subheader("Integração com IA")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        key="anthropic_api_key",
        help="Insira sua chave da API Anthropic (Claude) para usar IA na sugestão de premissas. "
             "Obtenha em console.anthropic.com",
    )
    if api_key:
        st.success("API Key configurada — IA ativada")
    else:
        st.info(
            "Sem API Key: premissas baseadas apenas em benchmarks estáticos de mercado."
        )

    st.markdown("---")
    if st.button("Recomeçar", use_container_width=True):
        api_key_backup = st.session_state.get("anthropic_api_key", "")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        if api_key_backup:
            st.session_state["anthropic_api_key"] = api_key_backup
        st.rerun()

# ---------------------------------------------------------------------------
# Título
# ---------------------------------------------------------------------------
st.title("Gerador de Premissas de Viabilidade Imobiliária")


# =====================================================================
# Funções auxiliares de renderização
# =====================================================================
def _renderizar_premissas(premissas: list, editadas: dict):
    """Renderiza uma lista de premissas — todas editáveis, com aviso fora do range."""
    if not premissas:
        st.info("Nenhuma premissa nesta categoria.")
        return

    # Agrupar por subcategoria
    subcategorias: dict[str, list] = {}
    for p in premissas:
        subcategorias.setdefault(p.subcategoria, []).append(p)

    for subcat, lista in subcategorias.items():
        st.markdown(f"#### {subcat}")

        for p in lista:
            with st.container():
                col_nome, col_valor, col_range, col_fonte = st.columns([3, 2, 2, 3])

                with col_nome:
                    st.markdown(f"**{p.nome}**")
                    if p.descricao and p.descricao != p.nome:
                        st.caption(p.descricao)

                with col_valor:
                    # Determinar step e format baseado na unidade
                    if p.unidade == "R$":
                        step = 1000.0
                        fmt = "%.2f"
                    elif p.unidade == "R$/m²":
                        step = 50.0
                        fmt = "%.2f"
                    elif "%" in p.unidade:
                        step = 0.1
                        fmt = "%.2f"
                    elif p.unidade == "meses":
                        step = 1.0
                        fmt = "%.0f"
                    elif p.unidade == "m²":
                        step = 5.0
                        fmt = "%.1f"
                    else:
                        step = 1.0
                        fmt = "%.2f"

                    novo_valor = st.number_input(
                        f"{p.unidade}",
                        min_value=0.0,
                        value=float(editadas.get(p.nome, p.valor)),
                        step=step,
                        format=fmt,
                        key=f"edit_{p.nome}",
                        label_visibility="collapsed",
                    )
                    editadas[p.nome] = novo_valor
                    st.caption(f"{p.unidade}")

                    # Aviso quando fora do range sugerido
                    if p.valor_min > 0 or p.valor_max > 0:
                        if novo_valor < p.valor_min:
                            st.warning(
                                f"Abaixo do mínimo sugerido ({p.valor_min:,.2f})",
                                icon="⚠️",
                            )
                        elif novo_valor > p.valor_max:
                            st.warning(
                                f"Acima do máximo sugerido ({p.valor_max:,.2f})",
                                icon="⚠️",
                            )

                with col_range:
                    if p.unidade == "R$":
                        st.caption(
                            f"Min: R$ {p.valor_min:,.0f}\n\n"
                            f"Max: R$ {p.valor_max:,.0f}"
                        )
                    else:
                        st.caption(
                            f"Min: {p.valor_min:,.2f}\n\n"
                            f"Max: {p.valor_max:,.2f}"
                        )

                with col_fonte:
                    st.caption(f"Fonte: {p.fonte}")

                st.markdown("---")

    st.session_state["premissas_editadas"] = editadas


def _aplicar_edicoes(resultado, editadas: dict):
    """Aplica os valores editados pelo usuário nas premissas."""
    for p in resultado.premissas:
        if p.nome in editadas:
            p.valor = editadas[p.nome]


# =====================================================================
# ETAPA 1: Dados do empreendimento (inputs obrigatórios)
# =====================================================================
if st.session_state["etapa"] == 1:
    st.header("Etapa 1 — Dados do Empreendimento")
    st.markdown(
        "Preencha as informações básicas do empreendimento. "
        "Com base nesses dados, o sistema irá sugerir premissas de mercado."
    )

    col1, col2 = st.columns(2)

    with col1:
        tipologia = st.selectbox(
            "Tipologia do empreendimento *",
            options=[t.value for t in Tipologia],
            key="inp_tipologia",
            help="Tipo de produto imobiliário",
        )

        # Filtrar padrões válidos para a tipologia selecionada
        tipologia_enum = Tipologia(tipologia)
        padroes_validos = PADROES_POR_TIPOLOGIA[tipologia_enum]

        padrao = st.selectbox(
            "Padrão do empreendimento *",
            options=[p.value for p in padroes_validos],
            key="inp_padrao",
            help="Define o nível de acabamento e público-alvo (filtrado pela tipologia)",
        )

        num_unidades = st.number_input(
            "Número de unidades (estimado) *",
            min_value=1,
            max_value=10_000,
            value=100,
            step=1,
            key="inp_num_unidades",
            help="Quantidade total de unidades do empreendimento",
        )

    with col2:
        estado = st.selectbox(
            "Estado (UF) *",
            options=ESTADOS_BRASIL,
            index=ESTADOS_BRASIL.index("GO"),
            key="inp_estado",
            help="Estado do empreendimento (define a região para benchmarks)",
        )

        # Lista de cidades filtrada pelo estado selecionado
        cidades_estado = CIDADES_POR_ESTADO.get(estado, [])
        opcoes_cidade = cidades_estado + ["Outra (digitar)"]

        cidade_selecionada = st.selectbox(
            "Cidade *",
            options=opcoes_cidade,
            key="inp_cidade_select",
            help="Comece a digitar para filtrar as cidades. Selecione 'Outra' se não encontrar.",
        )

        # Se "Outra" foi selecionada, mostrar campo de texto
        if cidade_selecionada == "Outra (digitar)":
            cidade_custom = st.text_input(
                "Digite o nome da cidade *",
                key="inp_cidade_custom",
                help="Informe o nome da cidade",
            )
            cidade_final = cidade_custom.strip()
        else:
            cidade_final = cidade_selecionada

        tipo_negociacao = st.selectbox(
            "Tipo de negociação do terreno *",
            options=[t.value for t in TipoNegociacao],
            key="inp_tipo_negociacao",
            help="Forma de aquisição/negociação do terreno",
        )

    # -------------------------------------------------------------------
    # Campos dinâmicos baseados no tipo de negociação
    # -------------------------------------------------------------------
    st.markdown("##### Parâmetros da Negociação")

    if tipo_negociacao == TipoNegociacao.PERMUTA_FISICA.value:
        st.info("**Permuta Física:** O proprietário recebe unidades do empreendimento.")
        permuta_pct = st.number_input(
            "Percentual de permuta (%)",
            min_value=0.0,
            max_value=100.0,
            value=15.0,
            step=0.5,
            key="inp_permuta_pct",
            help="Percentual das unidades que será destinado ao proprietário do terreno",
        )

    elif tipo_negociacao in [
        TipoNegociacao.PERMUTA_FINANCEIRA.value,
        TipoNegociacao.PERMUTA_RESULTADO.value,
    ]:
        label_tipo = (
            "Permuta Financeira" if tipo_negociacao == TipoNegociacao.PERMUTA_FINANCEIRA.value
            else "Permuta por Resultado"
        )
        st.info(
            f"**{label_tipo}:** O proprietário recebe um percentual "
            f"{'do valor financeiro' if 'Financeira' in label_tipo else 'do resultado'}."
        )
        col_perm1, col_perm2 = st.columns(2)
        with col_perm1:
            permuta_pct = st.number_input(
                "Percentual de permuta (%)",
                min_value=0.0,
                max_value=100.0,
                value=15.0,
                step=0.5,
                key="inp_permuta_pct",
                help="Percentual que será destinado ao proprietário do terreno",
            )
        with col_perm2:
            permuta_ref = st.selectbox(
                "Referência do percentual",
                options=["VGV", "Receita"],
                key="inp_permuta_ref",
                help="Se o percentual será calculado sobre o VGV ou sobre a Receita do empreendimento",
            )

    elif tipo_negociacao == TipoNegociacao.AQUISICAO.value:
        st.info("**Aquisição:** Compra direta do terreno por valor financeiro.")
        valor_aquisicao = st.number_input(
            "Valor da aquisição do terreno (R$)",
            min_value=0.0,
            value=0.0,
            step=100_000.0,
            key="inp_valor_aquisicao",
            format="%.2f",
            help="Valor total para aquisição do terreno",
        )

    st.markdown("---")

    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn2:
        if st.button("Próximo →", key="btn_etapa1_next", type="primary", use_container_width=True):
            if not cidade_final:
                st.error("Preencha o campo Cidade.")
            else:
                # Salvar valores da Etapa 1 em chaves persistentes
                st.session_state["data_tipologia"] = st.session_state["inp_tipologia"]
                st.session_state["data_padrao"] = st.session_state["inp_padrao"]
                st.session_state["data_num_unidades"] = st.session_state["inp_num_unidades"]
                st.session_state["data_estado"] = st.session_state["inp_estado"]
                st.session_state["data_cidade"] = cidade_final
                st.session_state["data_tipo_negociacao"] = st.session_state["inp_tipo_negociacao"]

                # Salvar parâmetros de negociação
                tipo_neg = st.session_state["inp_tipo_negociacao"]
                if tipo_neg == TipoNegociacao.PERMUTA_FISICA.value:
                    st.session_state["data_permuta_pct"] = st.session_state.get("inp_permuta_pct", 15.0)
                    st.session_state["data_permuta_ref"] = None
                    st.session_state["data_valor_aquisicao"] = None
                elif tipo_neg in [
                    TipoNegociacao.PERMUTA_FINANCEIRA.value,
                    TipoNegociacao.PERMUTA_RESULTADO.value,
                ]:
                    st.session_state["data_permuta_pct"] = st.session_state.get("inp_permuta_pct", 15.0)
                    st.session_state["data_permuta_ref"] = st.session_state.get("inp_permuta_ref", "VGV")
                    st.session_state["data_valor_aquisicao"] = None
                elif tipo_neg == TipoNegociacao.AQUISICAO.value:
                    st.session_state["data_permuta_pct"] = None
                    st.session_state["data_permuta_ref"] = None
                    val_aq = st.session_state.get("inp_valor_aquisicao", 0.0)
                    st.session_state["data_valor_aquisicao"] = val_aq if val_aq > 0 else None

                ir_para_etapa(2)
                st.rerun()

# =====================================================================
# ETAPA 2: Informações complementares (opcionais)
# =====================================================================
elif st.session_state["etapa"] == 2:
    st.header("Etapa 2 — Informações Complementares")
    st.markdown(
        "Estes campos são opcionais. Se não informados, o sistema estimará "
        "valores com base nos benchmarks de mercado."
    )

    col1, col2 = st.columns(2)

    with col1:
        area_terreno = st.number_input(
            "Área total do terreno (m²)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key="inp_area_terreno",
            help="Área total do terreno em metros quadrados. Deixe 0 se não souber.",
        )

        area_privativa = st.number_input(
            "Área privativa média por unidade (m²)",
            min_value=0.0,
            value=0.0,
            step=5.0,
            key="inp_area_privativa",
            help="Área privativa média de cada unidade. Deixe 0 para usar estimativa do sistema.",
        )

    with col2:
        vgv_estimado = st.number_input(
            "VGV estimado (R$)",
            min_value=0.0,
            value=0.0,
            step=100_000.0,
            key="inp_vgv",
            help="Valor Geral de Vendas estimado. Deixe 0 para o sistema calcular.",
            format="%.2f",
        )

    st.info(
        "**Dica:** Quanto mais informações você preencher, mais precisas "
        "serão as premissas sugeridas. Mas não se preocupe — o sistema "
        "funciona mesmo com apenas os dados obrigatórios da Etapa 1."
    )

    # Indicação se IA está ativa
    api_key = st.session_state.get("anthropic_api_key", "")
    if api_key:
        st.success(
            "A IA está ativada e será usada para refinar as premissas "
            "com base no mercado local da cidade selecionada."
        )

    st.markdown("---")

    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
        if st.button("← Voltar", key="btn_etapa2_back", use_container_width=True):
            ir_para_etapa(1)
            st.rerun()
    with col_btn2:
        if st.button(
            "Gerar Premissas →",
            key="btn_etapa2_next",
            type="primary",
            use_container_width=True,
        ):
            # Montar InputsUsuario (usa chaves persistentes salvas na Etapa 1)
            tipologia_enum = Tipologia(st.session_state["data_tipologia"])
            padrao_enum = Padrao(st.session_state["data_padrao"])
            negociacao_enum = TipoNegociacao(st.session_state["data_tipo_negociacao"])

            inputs = InputsUsuario(
                tipologia=tipologia_enum,
                estado=st.session_state["data_estado"],
                cidade=st.session_state["data_cidade"],
                padrao=padrao_enum,
                num_unidades=st.session_state["data_num_unidades"],
                tipo_negociacao=negociacao_enum,
                area_terreno_m2=area_terreno if area_terreno > 0 else None,
                vgv_estimado=vgv_estimado if vgv_estimado > 0 else None,
                area_privativa_media_m2=area_privativa if area_privativa > 0 else None,
                permuta_percentual=st.session_state.get("data_permuta_pct"),
                permuta_referencia=st.session_state.get("data_permuta_ref"),
                valor_aquisicao=st.session_state.get("data_valor_aquisicao"),
            )

            # Gerar premissas estáticas (base)
            with st.spinner("Gerando premissas com base nos benchmarks de mercado..."):
                resultado = gerar_premissas(inputs)

            # Enriquecer com IA se API Key disponível
            ia_metadata = None
            api_key = st.session_state.get("anthropic_api_key", "")
            if api_key:
                with st.spinner("Refinando premissas com IA... Isso pode levar alguns segundos."):
                    resultado, ia_metadata = gerar_premissas_com_ia(
                        inputs, resultado, api_key,
                    )

            st.session_state["resultado"] = resultado
            st.session_state["ia_metadata"] = ia_metadata
            st.session_state["premissas_editadas"] = {}
            ir_para_etapa(3)
            st.rerun()

# =====================================================================
# ETAPA 3: Premissas sugeridas (visualização e edição)
# =====================================================================
elif st.session_state["etapa"] == 3:
    st.header("Etapa 3 — Premissas Sugeridas")

    resultado = st.session_state.get("resultado")
    if not resultado:
        st.warning("Nenhum resultado disponível. Volte à Etapa 1.")
        if st.button("← Voltar ao início"):
            ir_para_etapa(1)
            st.rerun()
    else:
        inputs = resultado.inputs

        # Mostrar insights da IA se disponíveis
        ia_metadata = st.session_state.get("ia_metadata")
        if ia_metadata and "erro" not in ia_metadata:
            with st.expander(
                f"Insights da IA ({ia_metadata.get('ajustes_aplicados', 0)} "
                f"premissas ajustadas)",
                expanded=True,
            ):
                if ia_metadata.get("insights"):
                    st.markdown("**Insights do mercado:**")
                    for insight in ia_metadata["insights"]:
                        st.markdown(f"- {insight}")
                if ia_metadata.get("recomendacoes"):
                    st.markdown("**Recomendações:**")
                    for rec in ia_metadata["recomendacoes"]:
                        st.markdown(f"- {rec}")
        elif ia_metadata and "erro" in ia_metadata:
            st.warning(f"IA indisponível: {ia_metadata['erro']}")

        # Resumo dos inputs
        with st.expander("Resumo do empreendimento", expanded=False):
            df_inputs = inputs_para_dataframe(resultado)
            st.dataframe(df_inputs, use_container_width=True, hide_index=True)

        # Métricas principais
        vgv_premissa = resultado.get_premissa("VGV estimado")
        ticket_premissa = resultado.get_premissa("Ticket médio por unidade")
        prazo_premissa = resultado.get_premissa("Prazo de obra estimado")
        vel_premissa = resultado.get_premissa("Velocidade de vendas")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        if vgv_premissa:
            col_m1.metric(
                "VGV Estimado",
                f"R$ {vgv_premissa.valor:,.0f}".replace(",", "."),
            )
        if ticket_premissa:
            col_m2.metric(
                "Ticket Médio",
                f"R$ {ticket_premissa.valor:,.0f}".replace(",", "."),
            )
        if prazo_premissa:
            col_m3.metric("Prazo de Obra", f"{prazo_premissa.valor:.0f} meses")
        if vel_premissa:
            col_m4.metric("Veloc. Vendas", f"{vel_premissa.valor:.1f}%/mês")

        st.markdown("---")
        st.markdown(
            "Abaixo estão as premissas sugeridas pelo sistema, organizadas por categoria. "
            "Você pode **ajustar qualquer valor** antes de exportar. "
            "O range (mín-máx) indica a faixa de variação típica do mercado."
        )

        # Tabs por categoria
        tab_receita, tab_custo, tab_despesa, tab_financeiro, tab_vendas, tab_resumo_dfc, tab_simulacao = st.tabs(
            ["Receita", "Custo", "Despesa", "Financeiro", "Tabela de Vendas", "Resumo DFC", "Simulação"]
        )

        editadas = st.session_state.get("premissas_editadas", {})

        # --- Receita ---
        with tab_receita:
            st.subheader("Premissas de Receita")
            _renderizar_premissas(resultado.por_categoria("Receita"), editadas)

        # --- Custo ---
        with tab_custo:
            st.subheader("Premissas de Custo")
            _renderizar_premissas(resultado.por_categoria("Custo"), editadas)

        # --- Despesa ---
        with tab_despesa:
            st.subheader("Premissas de Despesa")
            _renderizar_premissas(resultado.por_categoria("Despesa"), editadas)

        # --- Financeiro ---
        with tab_financeiro:
            st.subheader("Premissas Financeiras")
            _renderizar_premissas(resultado.por_categoria("Financeiro"), editadas)

        # --- Tabela de vendas (editável) ---
        with tab_vendas:
            if resultado.tabela_vendas_loteamento:
                # ========= LOTEAMENTO =========
                tv = resultado.tabela_vendas_loteamento
                st.subheader("Tabela de Vendas — Loteamento")
                st.markdown(
                    "Modelo de **parcelamento direto** pelo loteador. "
                    "Não há financiamento bancário na entrega das chaves. "
                    "Edite os valores abaixo conforme necessário."
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    tv.entrada_pct = st.number_input(
                        "Entrada (%)", min_value=0.0, max_value=100.0,
                        value=float(tv.entrada_pct), step=1.0, format="%.1f",
                        key="tv_lot_entrada",
                    )
                with col2:
                    tv.saldo_parcelado_pct = st.number_input(
                        "Saldo Parcelado (%)", min_value=0.0, max_value=100.0,
                        value=float(tv.saldo_parcelado_pct), step=1.0, format="%.1f",
                        key="tv_lot_saldo",
                    )
                with col3:
                    tv.intermediarias_pct = st.number_input(
                        "Intermediárias (%)", min_value=0.0, max_value=50.0,
                        value=float(tv.intermediarias_pct), step=1.0, format="%.1f",
                        key="tv_lot_inter",
                    )

                # Validar soma
                soma_lot = tv.entrada_pct + tv.saldo_parcelado_pct + tv.intermediarias_pct
                if abs(soma_lot - 100.0) > 0.5:
                    st.warning(
                        f"A soma Entrada + Saldo + Intermediárias = {soma_lot:.1f}%. "
                        f"O ideal é que totalize 100%.",
                        icon="⚠️",
                    )

                st.markdown("---")
                st.markdown("**Detalhes do Parcelamento:**")
                det_col1, det_col2 = st.columns(2)
                with det_col1:
                    tv.num_parcelas = st.number_input(
                        "Nº de parcelas", min_value=12, max_value=360,
                        value=int(tv.num_parcelas), step=12,
                        key="tv_lot_num_parc",
                    )
                    tv.num_parcelas_entrada = st.number_input(
                        "Parcelas da entrada", min_value=1, max_value=12,
                        value=int(tv.num_parcelas_entrada), step=1,
                        key="tv_lot_parc_ent",
                    )
                with det_col2:
                    tv.juros_am = st.number_input(
                        "Juros (% a.m.)", min_value=0.0, max_value=3.0,
                        value=float(tv.juros_am), step=0.05, format="%.2f",
                        key="tv_lot_juros",
                    )
                    if tv.juros_am < 0.50 or tv.juros_am > 1.0:
                        st.warning(
                            f"Juros fora da faixa típica (0,50% a 1,00% a.m.)",
                            icon="⚠️",
                        )
                    juros_aa = round(((1 + tv.juros_am / 100) ** 12 - 1) * 100, 2)
                    st.caption(f"Equivalente anual: {juros_aa}% a.a.")

                    tv.sistema_amortizacao = st.selectbox(
                        "Sistema de amortização",
                        options=["Price", "Gradiente", "SAC"],
                        index=["Price", "Gradiente", "SAC"].index(tv.sistema_amortizacao)
                        if tv.sistema_amortizacao in ["Price", "Gradiente", "SAC"] else 0,
                        key="tv_lot_sistema",
                    )

                tv.indexador = st.selectbox(
                    "Indexador de correção",
                    options=["IPCA", "IGPM"],
                    index=["IPCA", "IGPM"].index(tv.indexador) if tv.indexador in ["IPCA", "IGPM"] else 0,
                    key="tv_lot_indexador",
                )

                st.info(
                    "Em loteamentos, o incorporador/loteador financia diretamente o comprador. "
                    "As tabelas mais comuns são **Price** (parcelas fixas + correção) e "
                    "**Gradiente** (parcelas crescentes). Prazos de **120x a 240x** são o padrão."
                )

            elif resultado.tabela_vendas:
                # ========= INCORPORAÇÃO =========
                tv = resultado.tabela_vendas
                st.subheader("Tabela de Vendas — Incorporação")
                st.markdown(
                    "Modelo de **captação + financiamento bancário** na entrega das chaves. "
                    "Edite os valores abaixo conforme necessário."
                )

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    tv.entrada_pct = st.number_input(
                        "Entrada (%)", min_value=0.0, max_value=100.0,
                        value=float(tv.entrada_pct), step=1.0, format="%.1f",
                        key="tv_inc_entrada",
                    )
                with col2:
                    tv.parcelas_obra_pct = st.number_input(
                        "Parcelas Obra (%)", min_value=0.0, max_value=100.0,
                        value=float(tv.parcelas_obra_pct), step=1.0, format="%.1f",
                        key="tv_inc_parcelas",
                    )
                with col3:
                    tv.financiamento_pct = st.number_input(
                        "Financiamento (%)", min_value=0.0, max_value=100.0,
                        value=float(tv.financiamento_pct), step=1.0, format="%.1f",
                        key="tv_inc_financiamento",
                        help="Repasse bancário na entrega das chaves",
                    )
                with col4:
                    tv.reforcos_pct = st.number_input(
                        "Reforços (%)", min_value=0.0, max_value=50.0,
                        value=float(tv.reforcos_pct), step=1.0, format="%.1f",
                        key="tv_inc_reforcos",
                        help="Parcelas semestrais/anuais",
                    )

                # Validar soma
                soma_inc = tv.entrada_pct + tv.parcelas_obra_pct + tv.financiamento_pct + tv.reforcos_pct
                if abs(soma_inc - 100.0) > 0.5:
                    st.warning(
                        f"A soma Entrada + Parcelas + Financiamento + Reforços = {soma_inc:.1f}%. "
                        f"O ideal é que totalize 100%.",
                        icon="⚠️",
                    )

                st.markdown("---")
                det_col1, det_col2 = st.columns(2)
                with det_col1:
                    tv.num_parcelas_obra = st.number_input(
                        "Nº parcelas durante obra", min_value=1, max_value=60,
                        value=int(tv.num_parcelas_obra), step=1,
                        key="tv_inc_num_parc",
                    )
                with det_col2:
                    tv.indexador_pre_chaves = st.selectbox(
                        "Indexador pré-chaves",
                        options=["INCC", "IPCA", "IGPM"],
                        index=["INCC", "IPCA", "IGPM"].index(tv.indexador_pre_chaves)
                        if tv.indexador_pre_chaves in ["INCC", "IPCA", "IGPM"] else 0,
                        key="tv_inc_idx_pre",
                    )
                    tv.indexador_pos_chaves = st.selectbox(
                        "Indexador pós-chaves",
                        options=["IGPM", "IPCA", "INCC"],
                        index=["IGPM", "IPCA", "INCC"].index(tv.indexador_pos_chaves)
                        if tv.indexador_pos_chaves in ["IGPM", "IPCA", "INCC"] else 0,
                        key="tv_inc_idx_pos",
                    )

            else:
                st.warning("Nenhuma tabela de vendas disponível.")

        # --- Resumo DFC ---
        with tab_resumo_dfc:
            st.subheader("Resumo do Fluxo de Caixa Projetado")
            st.markdown(
                "Visão consolidada das premissas, mapeadas para as categorias "
                "do DFC (Demonstração de Fluxo de Caixa) padrão Trinus."
            )

            vgv_p = resultado.get_premissa("VGV estimado")
            vgv_val = vgv_p.valor if vgv_p else 0

            # Receita
            with st.expander("**RECEITA**", expanded=True):
                st.markdown("##### Composição da Receita")
                receita_items = resultado.por_categoria("Receita")
                for p in receita_items:
                    if p.unidade == "R$":
                        st.markdown(f"- **{p.nome}:** R$ {p.valor:,.2f}")
                    elif p.unidade in ("% estoque/mês", "%", "% do total"):
                        st.markdown(f"- **{p.nome}:** {p.valor:.1f}{p.unidade}")
                    elif p.unidade in ("INCC", "IPCA", "IGPM", "meses"):
                        st.markdown(f"- **{p.nome}:** {p.descricao}")
                    else:
                        st.markdown(f"- **{p.nome}:** {p.valor:.2f} {p.unidade}")

            # Custos
            with st.expander("**CUSTOS**", expanded=True):
                st.markdown("##### Composição dos Custos")
                custo_items = resultado.por_categoria("Custo")
                for p in custo_items:
                    if p.unidade == "R$":
                        st.markdown(f"- **{p.nome}:** R$ {p.valor:,.2f}")
                    elif "% do VGV" in p.unidade and vgv_val > 0:
                        valor_abs = vgv_val * p.valor / 100
                        st.markdown(
                            f"- **{p.nome}:** {p.valor:.1f}% do VGV "
                            f"(~R$ {valor_abs:,.0f})"
                        )
                    else:
                        st.markdown(f"- **{p.nome}:** {p.valor:.2f} {p.unidade}")

            # Despesas
            with st.expander("**DESPESAS**", expanded=True):
                st.markdown("##### Composição das Despesas")
                despesa_items = resultado.por_categoria("Despesa")
                total_desp_pct = 0
                for p in despesa_items:
                    if "% do VGV" in p.unidade or "% sobre receita" in p.unidade:
                        total_desp_pct += p.valor
                        if vgv_val > 0:
                            valor_abs = vgv_val * p.valor / 100
                            st.markdown(
                                f"- **{p.nome}:** {p.valor:.1f}% "
                                f"(~R$ {valor_abs:,.0f})"
                            )
                        else:
                            st.markdown(f"- **{p.nome}:** {p.valor:.1f}%")
                    else:
                        st.markdown(f"- **{p.nome}:** {p.valor:.2f} {p.unidade}")
                if vgv_val > 0:
                    st.markdown(
                        f"**Total despesas estimadas:** {total_desp_pct:.1f}% do VGV "
                        f"(~R$ {vgv_val * total_desp_pct / 100:,.0f})"
                    )

            # Financeiro
            with st.expander("**FINANCEIRO**", expanded=True):
                st.markdown("##### Premissas Financeiras e CRI")
                fin_items = resultado.por_categoria("Financeiro")
                for p in fin_items:
                    st.markdown(f"- **{p.nome}:** {p.valor:.2f} {p.unidade}")

        # --- Simulação ---
        with tab_simulacao:
            st.subheader("Simulação do Resultado do Empreendimento")
            st.markdown(
                "Projeção financeira com base nas premissas editadas. "
                "Altere qualquer premissa nas abas anteriores para ver o impacto no resultado."
            )

            # Aplicar edições atuais antes de simular
            _aplicar_edicoes(resultado, editadas)

            # Executar simulação
            sim = simular(resultado)

            if sim.vgv <= 0:
                st.warning("Preencha o VGV estimado para gerar a simulação.")
            else:
                # === Indicadores principais ===
                st.markdown("### Indicadores de Viabilidade")

                ind_col1, ind_col2, ind_col3, ind_col4 = st.columns(4)
                ind_col1.metric(
                    "Resultado do Projeto",
                    f"R$ {sim.resultado_projeto:,.0f}".replace(",", "."),
                    delta=f"{sim.margem_vgv:.1f}% do VGV",
                    delta_color="normal" if sim.resultado_projeto >= 0 else "inverse",
                )
                ind_col2.metric(
                    "Margem sobre VGV",
                    f"{sim.margem_vgv:.1f}%",
                    delta="Saudável" if sim.margem_vgv >= 15 else "Atenção" if sim.margem_vgv >= 10 else "Crítico",
                    delta_color="normal" if sim.margem_vgv >= 15 else "off" if sim.margem_vgv >= 10 else "inverse",
                )
                ind_col3.metric(
                    "TIR Anual",
                    f"{sim.tir_anual:.1f}%",
                    delta="Atrativa" if sim.tir_anual >= 20 else "Moderada" if sim.tir_anual >= 15 else "Baixa",
                    delta_color="normal" if sim.tir_anual >= 20 else "off" if sim.tir_anual >= 15 else "inverse",
                )
                ind_col4.metric(
                    "VPL (a valor presente)",
                    f"R$ {sim.vpl:,.0f}".replace(",", "."),
                    delta="Viável" if sim.vpl > 0 else "Inviável",
                    delta_color="normal" if sim.vpl > 0 else "inverse",
                )

                st.markdown("---")

                ind2_col1, ind2_col2, ind2_col3, ind2_col4 = st.columns(4)
                ind2_col1.metric(
                    "Margem sobre Custo",
                    f"{sim.margem_custo:.1f}%",
                )
                ind2_col2.metric(
                    "Payback",
                    f"{sim.payback_meses} meses",
                    delta=f"~{sim.payback_meses / 12:.1f} anos",
                )
                ind2_col3.metric(
                    "Exposição Máxima",
                    f"R$ {sim.exposicao_maxima:,.0f}".replace(",", "."),
                    help="Maior saldo negativo acumulado — capital necessário",
                )
                ind2_col4.metric(
                    "Lucro / Investimento",
                    f"{sim.lucro_sobre_investimento:.1f}%",
                    help="Resultado / Exposição Máxima",
                )

                ind3_col1, ind3_col2 = st.columns(2)
                ind3_col1.metric("TIR Mensal", f"{sim.tir_mensal:.2f}%")
                ind3_col2.metric(
                    "Receita Líquida",
                    f"R$ {sim.receita_liquida:,.0f}".replace(",", "."),
                )

                # === DRE Resumido ===
                st.markdown("---")
                st.markdown("### DRE Simplificado do Projeto")

                dre_data = {
                    "Linha": [
                        "VGV (Valor Geral de Vendas)",
                        "(-) Distrato / Inadimplência",
                        "= Receita Líquida",
                        "",
                        "(-) Custo do Terreno",
                        f"(-) Custo de {'Infraestrutura' if resultado.e_loteamento else 'Construção'}",
                        "(-) BDI / Administração de Obra",
                        "(-) Projetos e Aprovações",
                        "(-) Outros Custos (IPTU, ITBI)",
                        "= Total de Custos",
                        "",
                        "(-) Despesas Comerciais",
                        "(-) Despesas Administrativas",
                        "(-) Despesas Tributárias",
                        "(-) Despesas Cartoriais",
                        "= Total de Despesas",
                        "",
                        "= RESULTADO DO PROJETO",
                    ],
                    "Valor (R$)": [
                        f"R$ {sim.vgv:,.0f}",
                        f"R$ {(sim.vgv - sim.receita_liquida):,.0f}",
                        f"R$ {sim.receita_liquida:,.0f}",
                        "",
                        f"R$ {sim.custo_terreno:,.0f}",
                        f"R$ {sim.custo_construcao_infra:,.0f}",
                        f"R$ {sim.custo_bdi:,.0f}",
                        f"R$ {sim.custo_projetos_aprovacoes:,.0f}",
                        f"R$ {sim.custo_outros:,.0f}",
                        f"R$ {sim.custo_total:,.0f}",
                        "",
                        f"R$ {sim.despesa_comercial:,.0f}",
                        f"R$ {sim.despesa_administrativa:,.0f}",
                        f"R$ {sim.despesa_tributaria:,.0f}",
                        f"R$ {sim.despesa_cartorial:,.0f}",
                        f"R$ {sim.despesa_total:,.0f}",
                        "",
                        f"R$ {sim.resultado_projeto:,.0f}",
                    ],
                    "% VGV": [
                        "100,0%",
                        f"{(sim.vgv - sim.receita_liquida) / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.receita_liquida / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        "",
                        f"{sim.custo_terreno / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.custo_construcao_infra / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.custo_bdi / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.custo_projetos_aprovacoes / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.custo_outros / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.custo_total / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        "",
                        f"{sim.despesa_comercial / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.despesa_administrativa / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.despesa_tributaria / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.despesa_cartorial / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        f"{sim.despesa_total / sim.vgv * 100:.1f}%" if sim.vgv > 0 else "-",
                        "",
                        f"{sim.margem_vgv:.1f}%",
                    ],
                }

                df_dre = pd.DataFrame(dre_data)
                st.dataframe(df_dre, use_container_width=True, hide_index=True, height=680)

                # === Gráfico de Fluxo de Caixa ===
                st.markdown("---")
                st.markdown("### Fluxo de Caixa Acumulado")

                # Preparar dados para gráfico
                df_fluxo = pd.DataFrame({
                    "Mês": list(range(sim.total_meses)),
                    "Fluxo Mensal (R$)": sim.fluxo_mensal,
                    "Acumulado (R$)": sim.fluxo_acumulado,
                })

                st.line_chart(
                    df_fluxo.set_index("Mês")[["Acumulado (R$)"]],
                    use_container_width=True,
                )

                # Gráfico de barras: receitas vs custos vs despesas por trimestre
                st.markdown("### Composição Trimestral")
                trimestres = max(1, sim.total_meses // 3)
                trim_receitas = []
                trim_custos = []
                trim_despesas = []
                trim_labels = []
                for t in range(min(trimestres, 40)):  # máx 40 trimestres no gráfico
                    inicio = t * 3
                    fim = min(inicio + 3, sim.total_meses)
                    trim_receitas.append(sum(sim.receitas_mensais[inicio:fim]))
                    trim_custos.append(-sum(sim.custos_mensais[inicio:fim]))
                    trim_despesas.append(-sum(sim.despesas_mensais[inicio:fim]))
                    trim_labels.append(f"T{t + 1}")

                df_trim = pd.DataFrame({
                    "Trimestre": trim_labels,
                    "Receitas": trim_receitas,
                    "Custos": trim_custos,
                    "Despesas": trim_despesas,
                })
                st.bar_chart(
                    df_trim.set_index("Trimestre"),
                    use_container_width=True,
                )

                # Avaliação final
                st.markdown("---")
                st.markdown("### Avaliação da Viabilidade")

                if sim.margem_vgv >= 20 and sim.tir_anual >= 20 and sim.vpl > 0:
                    st.success(
                        f"**Projeto VIÁVEL** — Margem de {sim.margem_vgv:.1f}%, "
                        f"TIR de {sim.tir_anual:.1f}% a.a. e VPL positivo de "
                        f"R$ {sim.vpl:,.0f}. Indicadores acima dos benchmarks de mercado."
                    )
                elif sim.margem_vgv >= 12 and sim.tir_anual >= 15 and sim.vpl > 0:
                    st.info(
                        f"**Projeto VIÁVEL com ressalvas** — Margem de {sim.margem_vgv:.1f}%, "
                        f"TIR de {sim.tir_anual:.1f}% a.a. O projeto é viável mas "
                        f"tem sensibilidade a variações nas premissas. Recomenda-se "
                        f"análise de cenários."
                    )
                elif sim.vpl > 0:
                    st.warning(
                        f"**Projeto MARGINAL** — Margem de {sim.margem_vgv:.1f}%, "
                        f"TIR de {sim.tir_anual:.1f}% a.a. Embora o VPL seja positivo "
                        f"(R$ {sim.vpl:,.0f}), os indicadores estão abaixo do ideal. "
                        f"Reavalie premissas de custo e receita."
                    )
                else:
                    st.error(
                        f"**Projeto INVIÁVEL** — Margem de {sim.margem_vgv:.1f}%, "
                        f"TIR de {sim.tir_anual:.1f}% a.a. e VPL negativo de "
                        f"R$ {sim.vpl:,.0f}. O projeto não remunera o capital investido "
                        f"à taxa mínima de atratividade definida."
                    )

        st.markdown("---")

        # Navegação
        col_btn1, col_btn2, _ = st.columns([1, 1, 2])
        with col_btn1:
            if st.button("← Voltar", key="btn_etapa3_back", use_container_width=True):
                ir_para_etapa(2)
                st.rerun()
        with col_btn2:
            if st.button(
                "Exportar Resultados →",
                key="btn_etapa3_next",
                type="primary",
                use_container_width=True,
            ):
                # Aplicar edições antes de exportar
                _aplicar_edicoes(resultado, editadas)
                ir_para_etapa(4)
                st.rerun()

# =====================================================================
# ETAPA 4: Exportar resultados
# =====================================================================
elif st.session_state["etapa"] == 4:
    st.header("Etapa 4 — Exportar Resultados")

    resultado = st.session_state.get("resultado")
    if not resultado:
        st.warning("Nenhum resultado disponível.")
        if st.button("← Voltar ao início"):
            ir_para_etapa(1)
            st.rerun()
    else:
        st.success("Premissas geradas com sucesso! Escolha o formato de exportação.")

        # Resumo final
        st.subheader("Resumo Final")
        df_premissas = premissas_para_dataframe(resultado)
        st.dataframe(df_premissas, use_container_width=True, height=400, hide_index=True)

        st.markdown("---")

        # Botões de exportação
        st.subheader("Formatos de Exportação")
        col_exp1, col_exp2, col_exp3 = st.columns(3)

        with col_exp1:
            excel_bytes = exportar_excel_bytes(resultado)
            st.download_button(
                "Baixar Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"viabilidade_premissas_{resultado.versao}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )

        with col_exp2:
            json_bytes = exportar_json_bytes(resultado)
            st.download_button(
                "Baixar JSON",
                data=json_bytes,
                file_name=f"viabilidade_premissas_{resultado.versao}.json",
                mime="application/json",
                use_container_width=True,
            )

        with col_exp3:
            st.button(
                "PDF (em breve)",
                disabled=True,
                use_container_width=True,
                help="Exportação em PDF será disponibilizada em versões futuras",
            )

        st.markdown("---")

        # Navegação
        col_btn1, col_btn2, _ = st.columns([1, 1, 2])
        with col_btn1:
            if st.button("← Voltar às Premissas", key="btn_etapa4_back", use_container_width=True):
                ir_para_etapa(3)
                st.rerun()
        with col_btn2:
            if st.button("Nova Viabilidade", key="btn_etapa4_new", use_container_width=True):
                api_key_backup = st.session_state.get("anthropic_api_key", "")
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                if api_key_backup:
                    st.session_state["anthropic_api_key"] = api_key_backup
                st.rerun()
