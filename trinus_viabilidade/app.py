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

import streamlit as st

from modelos import (
    ESTADOS_BRASIL,
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

        padrao = st.selectbox(
            "Padrão do empreendimento *",
            options=[p.value for p in Padrao],
            key="inp_padrao",
            help="Define o nível de acabamento e público-alvo",
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
        tab_receita, tab_custo, tab_despesa, tab_financeiro, tab_vendas = st.tabs(
            ["Receita", "Custo", "Despesa", "Financeiro", "Tabela de Vendas"]
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

        # --- Tabela de vendas ---
        with tab_vendas:
            st.subheader("Condições de Pagamento (Tabela de Vendas)")
            if resultado.tabela_vendas:
                df_vendas = tabela_vendas_para_dataframe(resultado)
                st.dataframe(df_vendas, use_container_width=True, hide_index=True)

                tv = resultado.tabela_vendas
                st.markdown("**Distribuição visual:**")
                cols_tv = st.columns(4)
                cols_tv[0].metric("Entrada", f"{tv.entrada_pct}%")
                cols_tv[1].metric("Parcelas Obra", f"{tv.parcelas_obra_pct}%")
                cols_tv[2].metric("Financiamento", f"{tv.financiamento_pct}%")
                cols_tv[3].metric("Reforços", f"{tv.reforcos_pct}%")

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


# =====================================================================
# Funções auxiliares de renderização
# =====================================================================
def _renderizar_premissas(premissas: list, editadas: dict):
    """Renderiza uma lista de premissas com campos editáveis."""
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
                    if p.editavel:
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
                    else:
                        if p.unidade == "R$":
                            st.markdown(f"**R$ {p.valor:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
                        else:
                            st.markdown(f"**{p.valor:,.2f} {p.unidade}**")

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
