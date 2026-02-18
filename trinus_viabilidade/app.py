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

from datetime import date
from modelos import (
    ESTADOS_BRASIL,
    PADROES_POR_TIPOLOGIA,
    DatasMacro,
    InputsUsuario,
    Padrao,
    Tipologia,
    TipoNegociacao,
)
from engine import gerar_premissas
from engine_ia import gerar_premissas_com_ia
from supabase_client import (
    get_client as get_supabase_client,
    salvar_estudo,
    atualizar_status,
    salvar_simulacao,
    buscar_casos_similares,
    buscar_estatisticas,
    formatar_contexto_rag,
)
from exportador import (
    exportar_excel_bytes,
    exportar_json_bytes,
    exportar_dfc_aberto_excel_bytes,
    dfc_aberto_dataframe,
    inputs_para_dataframe,
    premissas_para_dataframe,
    tabela_vendas_para_dataframe,
)
from simulador import simular, gerar_diagnostico, _get_premissa_valor
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

    # -----------------------------------------------------------------------
    # Integração com Supabase (base de conhecimento)
    # -----------------------------------------------------------------------
    st.subheader("Base de Conhecimento")

    # Carregar credenciais automaticamente do secrets.toml (se existir)
    _sb_url_default = ""
    _sb_key_default = ""
    try:
        _sb_url_default = st.secrets.get("supabase", {}).get("url", "")
        _sb_key_default = st.secrets.get("supabase", {}).get("key", "")
    except Exception:
        pass

    # Preencher session_state na primeira carga (automático)
    if "supabase_url" not in st.session_state and _sb_url_default:
        st.session_state["supabase_url"] = _sb_url_default
    if "supabase_key" not in st.session_state and _sb_key_default:
        st.session_state["supabase_key"] = _sb_key_default

    _sb_url_atual = st.session_state.get("supabase_url", "")
    _sb_key_atual = st.session_state.get("supabase_key", "")

    if _sb_url_atual and _sb_key_atual:
        st.success("Supabase conectado — base de conhecimento ativa")
        with st.expander("Alterar credenciais Supabase", expanded=False):
            st.text_input(
                "Supabase URL",
                key="supabase_url",
                help="URL do projeto Supabase.",
            )
            st.text_input(
                "Supabase Anon Key",
                type="password",
                key="supabase_key",
                help="Chave anon/public do projeto Supabase.",
            )
    else:
        st.info("Configure o Supabase para ativar a base de conhecimento.")
        st.text_input(
            "Supabase URL",
            key="supabase_url",
            help="URL do projeto Supabase. Ex: https://xyz.supabase.co",
        )
        st.text_input(
            "Supabase Anon Key",
            type="password",
            key="supabase_key",
            help="Chave anon/public do projeto Supabase.",
        )

    st.markdown("---")
    if st.button("Recomeçar", use_container_width=True):
        api_key_backup = st.session_state.get("anthropic_api_key", "")
        sb_url_backup = st.session_state.get("supabase_url", "")
        sb_key_backup = st.session_state.get("supabase_key", "")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        if api_key_backup:
            st.session_state["anthropic_api_key"] = api_key_backup
        if sb_url_backup:
            st.session_state["supabase_url"] = sb_url_backup
        if sb_key_backup:
            st.session_state["supabase_key"] = sb_key_backup
        st.rerun()

# ---------------------------------------------------------------------------
# Helper: obter cliente Supabase (ou None)
# ---------------------------------------------------------------------------
def _get_supabase():
    """Retorna cliente Supabase se configurado, senão None."""
    url = st.session_state.get("supabase_url", "")
    key = st.session_state.get("supabase_key", "")
    if url and key:
        try:
            return get_supabase_client(url, key)
        except Exception:
            return None
    return None

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

            # Buscar contexto da base de conhecimento (retroalimentação)
            contexto_rag = ""
            sb = _get_supabase()
            if sb:
                try:
                    with st.spinner("Buscando dados históricos da base de conhecimento..."):
                        casos = buscar_casos_similares(
                            sb, inputs.cidade, inputs.estado,
                            inputs.tipologia.value, inputs.padrao.value,
                        )
                        stats = buscar_estatisticas(
                            sb, inputs.cidade, inputs.estado,
                            inputs.tipologia.value,
                        )
                        contexto_rag = formatar_contexto_rag(casos, stats)
                        if casos:
                            st.session_state["_rag_casos_count"] = len(casos)
                except Exception:
                    contexto_rag = ""

            # Enriquecer com IA se API Key disponível
            ia_metadata = None
            api_key = st.session_state.get("anthropic_api_key", "")
            if api_key:
                with st.spinner("Refinando premissas com IA... Isso pode levar alguns segundos."):
                    resultado, ia_metadata = gerar_premissas_com_ia(
                        inputs, resultado, api_key,
                        contexto_historico=contexto_rag,
                    )

            # Salvar estudo na base de conhecimento
            if sb:
                try:
                    estudo_id = salvar_estudo(
                        sb, resultado,
                        ia_metadata=ia_metadata,
                        status="gerado",
                    )
                    st.session_state["estudo_id"] = estudo_id
                except Exception:
                    pass  # Não bloquear o fluxo se Supabase falhar

            st.session_state["resultado"] = resultado
            st.session_state["ia_metadata"] = ia_metadata
            st.session_state["premissas_editadas"] = {}
            # Resetar datas macro para recalcular com novas premissas
            if "datas_macro" in st.session_state:
                del st.session_state["datas_macro"]
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

        # =================================================================
        # DATAS MACRO — Cronograma do empreendimento
        # =================================================================
        with st.expander("Datas Macro — Cronograma do Empreendimento", expanded=True):

            # Helper constantes
            MESES_NOMES = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
            ]
            _ano_base = date.today().year
            ANOS_OPCOES = list(range(_ano_base, _ano_base + 20))

            def _fmt_data(d: date) -> str:
                return f"{MESES_NOMES[d.month - 1]}/{d.year}"

            # ----- Ler prazos das premissas (incluindo edições do usuário) -----
            _editadas_atuais = st.session_state.get("premissas_editadas", {})
            _prazo_reg = int(_editadas_atuais.get(
                "Prazo para Registro de Incorporação/Loteamento",
                _get_premissa_valor(resultado, "Prazo para Registro de Incorporação/Loteamento", 6),
            ))
            _prazo_obra = int(_editadas_atuais.get(
                "Prazo de obra estimado",
                _get_premissa_valor(resultado, "Prazo de obra estimado", 24),
            ))

            # ----- Detectar mudança nas premissas de prazo para recalcular -----
            _prazos_key = f"{_prazo_reg}_{_prazo_obra}"
            _prazos_anterior = st.session_state.get("_prazos_macro_key", "")

            precisa_recalcular = False
            if "datas_macro" not in st.session_state:
                precisa_recalcular = True
            elif _prazos_key != _prazos_anterior:
                precisa_recalcular = True

            if precisa_recalcular:
                dm = DatasMacro()
                dm.sugerir_a_partir_de_premissas(_prazo_reg, _prazo_obra)
                st.session_state["datas_macro"] = dm
                st.session_state["_prazos_macro_key"] = _prazos_key

            dm = st.session_state["datas_macro"]

            # ----- Justificativas da IA para o cronograma -----
            ia_metadata = st.session_state.get("ia_metadata")
            crono_ia = ia_metadata.get("cronograma", {}) if ia_metadata and "erro" not in ia_metadata else {}
            crono_resumo = crono_ia.get("resumo", "")
            crono_marcos = crono_ia.get("marcos", {})

            # Justificativa padrão quando IA não disponível
            _just_padrao = {
                "inicio_projeto": f"Início imediato das atividades de projetos e aprovações.",
                "lancamento": f"Lançamento comercial após {_prazo_reg} meses (premissa: Prazo para Registro de Incorporação/Loteamento = {_prazo_reg} meses).",
                "inicio_obra": f"Início da obra coincide com o lançamento comercial.",
                "fim_obra": f"Conclusão da obra em {_prazo_obra} meses após início (premissa: Prazo de obra estimado = {_prazo_obra} meses).",
                "inicio_vendas_pos": f"Vendas pós-obra iniciam imediatamente após a conclusão.",
            }

            def _get_justificativa(marco: str) -> str:
                """Retorna justificativa da IA ou padrão."""
                if marco in crono_marcos and crono_marcos[marco].get("justificativa"):
                    return crono_marcos[marco]["justificativa"]
                return _just_padrao.get(marco, "")

            # ----- Resumo do cronograma sugerido pela IA -----
            if crono_resumo:
                st.info(f"**Sugestão da IA:** {crono_resumo}")
            else:
                st.markdown(
                    f"Cronograma calculado automaticamente com base nas premissas: "
                    f"**Prazo de Registro = {_prazo_reg} meses** | "
                    f"**Prazo de Obra = {_prazo_obra} meses**. "
                    f"Altere as premissas de prazo para recalcular automaticamente, "
                    f"ou edite as datas abaixo manualmente."
                )

            st.markdown("")

            # ----- Seletor de datas com justificativas -----
            def _date_selector(label: str, current: date, key_prefix: str, marco: str) -> date:
                """Renderiza par mês/ano com justificativa e retorna date."""
                st.markdown(f"**{label}**")
                justificativa = _get_justificativa(marco)
                if justificativa:
                    st.caption(f"_{justificativa}_")
                c_mes, c_ano = st.columns(2)
                with c_mes:
                    mes_idx = c_mes.selectbox(
                        "Mês",
                        options=list(range(1, 13)),
                        format_func=lambda x: MESES_NOMES[x - 1],
                        index=current.month - 1,
                        key=f"{key_prefix}_mes",
                        label_visibility="collapsed",
                    )
                with c_ano:
                    ano_val = c_ano.selectbox(
                        "Ano",
                        options=ANOS_OPCOES,
                        index=ANOS_OPCOES.index(current.year) if current.year in ANOS_OPCOES else 0,
                        key=f"{key_prefix}_ano",
                        label_visibility="collapsed",
                    )
                return date(ano_val, mes_idx, 1)

            dm_col1, dm_col2, dm_col3 = st.columns(3)
            with dm_col1:
                novo_inicio = _date_selector(
                    "Inicio do Projeto", dm.inicio_projeto, "dm_inicio",
                    "inicio_projeto",
                )
                if novo_inicio != dm.inicio_projeto:
                    dm.inicio_projeto = novo_inicio
                    dm.inicio_aprovacoes = None
                    dm.lancamento = None
                    dm.inicio_obra = None
                    dm.fim_obra = None
                    dm.inicio_vendas_pos = None
                    dm.sugerir_a_partir_de_premissas(_prazo_reg, _prazo_obra)

            with dm_col2:
                novo_lanc = _date_selector(
                    "Lançamento Comercial", dm.lancamento or dm.inicio_projeto, "dm_lanc",
                    "lancamento",
                )
                dm.lancamento = novo_lanc

            with dm_col3:
                novo_inicio_obra = _date_selector(
                    "Início da Obra", dm.inicio_obra or dm.lancamento, "dm_obra_ini",
                    "inicio_obra",
                )
                dm.inicio_obra = novo_inicio_obra

            dm_col4, dm_col5, _ = st.columns(3)
            with dm_col4:
                novo_fim_obra = _date_selector(
                    "Conclusão da Obra", dm.fim_obra or dm.inicio_projeto, "dm_obra_fim",
                    "fim_obra",
                )
                dm.fim_obra = novo_fim_obra

            with dm_col5:
                novo_pos = _date_selector(
                    "Início Vendas Pós-Obra", dm.inicio_vendas_pos or dm.fim_obra, "dm_pos",
                    "inicio_vendas_pos",
                )
                dm.inicio_vendas_pos = novo_pos

            # Resumo visual do cronograma
            _meses_ate_lanc = (dm.lancamento.year - dm.inicio_projeto.year) * 12 + (dm.lancamento.month - dm.inicio_projeto.month) if dm.lancamento else _prazo_reg
            _meses_obra = (dm.fim_obra.year - dm.inicio_obra.year) * 12 + (dm.fim_obra.month - dm.inicio_obra.month) if dm.fim_obra and dm.inicio_obra else _prazo_obra

            st.markdown("")
            st.success(
                f"**Cronograma:** {_fmt_data(dm.inicio_projeto)} → "
                f"Lançamento em {_fmt_data(dm.lancamento)} ({_meses_ate_lanc} meses) → "
                f"Obra de {_fmt_data(dm.inicio_obra)} a {_fmt_data(dm.fim_obra)} ({_meses_obra} meses)"
            )

        st.markdown("---")
        st.markdown(
            "Abaixo estão as premissas sugeridas pelo sistema, organizadas por categoria. "
            "Você pode **ajustar qualquer valor** antes de exportar. "
            "O range (mín-máx) indica a faixa de variação típica do mercado."
        )

        # Tabs por categoria
        tab_receita, tab_custo, tab_despesa, tab_financeiro, tab_vendas, tab_resumo_dfc, tab_simulacao, tab_dfc_aberto = st.tabs(
            ["Receita", "Custo", "Despesa", "Financeiro", "Tabela de Vendas", "Resumo DFC", "Simulacao", "DFC Aberto"]
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
            sim = simular(resultado, datas_macro=st.session_state.get("datas_macro"))

            # Salvar simulação na base de conhecimento
            _sb = _get_supabase()
            _eid = st.session_state.get("estudo_id")
            if _sb and _eid and sim.vgv > 0:
                try:
                    salvar_simulacao(_sb, _eid, sim)
                    atualizar_status(_sb, _eid, "simulado")
                except Exception:
                    pass

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

                # === FLUXO DE CAIXA (estrutura DFC Trinus) ===
                st.markdown("---")
                st.markdown("### Fluxo de Caixa do Projeto")

                def _fmt(v: float) -> str:
                    """Formata valor monetário (padrão brasileiro)."""
                    if v == 0:
                        return "-"
                    return f"R$ {v:,.0f}".replace(",", ".")

                def _pct(v: float, base: float) -> str:
                    """Calcula e formata percentual."""
                    if base == 0:
                        return "-"
                    return f"{v / base * 100:.1f}%"

                rl = sim.receita_liquida  # base para margem nominal
                v = sim.vgv

                e_lot = resultado.e_loteamento
                lbl_obra = "infraestrutura" if e_lot else "construção"
                lbl_inter = "Intermediárias / Saldo parcelado" if e_lot else "Financiamento / Reforços"

                # Montar linhas do DFC hierarquicamente
                # Cada linha: (indent, label, nominal, margem_nominal, pct_vgv)
                linhas = [
                    # --- VENDAS ---
                    (0, "VENDAS", "", "", ""),
                    (1, "VGV (Valor Geral de Vendas)", _fmt(v), "", "100,0%"),
                    (1, f"Unidades líquidas (após distrato)", f"{sim.num_unidades_liquidas:.0f} un.", "", ""),
                    (1, "(-) VGV cancelado (distratos)", _fmt(-sim.vgv_cancelado), "", _pct(-sim.vgv_cancelado, v)),
                    (1, "VGV Líquido", _fmt(v - sim.vgv_cancelado), "", _pct(v - sim.vgv_cancelado, v)),
                    (0, "", "", "", ""),
                    # --- RECEITA ---
                    (0, "RECEITA LÍQUIDA OPERACIONAL", _fmt(rl), "100,0%", _pct(rl, v)),
                    (1, "Receita Bruta Operacional", _fmt(sim.receita_bruta), _pct(sim.receita_bruta, rl), _pct(sim.receita_bruta, v)),
                    (2, "Entrada / Sinal", _fmt(sim.receita_entrada), _pct(sim.receita_entrada, rl), _pct(sim.receita_entrada, v)),
                    (2, "Parcelas mensais", _fmt(sim.receita_parcelas), _pct(sim.receita_parcelas, rl), _pct(sim.receita_parcelas, v)),
                    (2, lbl_inter, _fmt(sim.receita_intermediarias), _pct(sim.receita_intermediarias, rl), _pct(sim.receita_intermediarias, v)),
                    (1, "(-) Inadimplência", _fmt(-sim.valor_inadimplencia), _pct(-sim.valor_inadimplencia, rl), _pct(-sim.valor_inadimplencia, v)),
                    (0, "", "", "", ""),
                    # --- CUSTOS ---
                    (0, "(-) CUSTOS", _fmt(-sim.custo_total), _pct(-sim.custo_total, rl), _pct(-sim.custo_total, v)),
                    (1, f"Custo total de obra ({lbl_obra})", _fmt(-sim.custo_obra_total), _pct(-sim.custo_obra_total, rl), _pct(-sim.custo_obra_total, v)),
                    (2, f"Custo raso de {lbl_obra}", _fmt(-sim.custo_obra_raso), _pct(-sim.custo_obra_raso, rl), _pct(-sim.custo_obra_raso, v)),
                    (2, "Custo de administração de obra (BDI)", _fmt(-sim.custo_admin_obra), _pct(-sim.custo_admin_obra, rl), _pct(-sim.custo_admin_obra, v)),
                    (2, "Custo de projetos e consultorias", _fmt(-sim.custo_projetos), _pct(-sim.custo_projetos, rl), _pct(-sim.custo_projetos, v)),
                    (2, "Custo de aprovações e licenças", _fmt(-sim.custo_aprovacoes), _pct(-sim.custo_aprovacoes, rl), _pct(-sim.custo_aprovacoes, v)),
                    (1, "Custo de terreno", _fmt(-sim.custo_terreno_total), _pct(-sim.custo_terreno_total, rl), _pct(-sim.custo_terreno_total, v)),
                    (2, "Custo de aquisição do terreno", _fmt(-sim.custo_terreno_aquisicao), _pct(-sim.custo_terreno_aquisicao, rl), _pct(-sim.custo_terreno_aquisicao, v)),
                    (2, "Custo de ITBI", _fmt(-sim.custo_itbi), _pct(-sim.custo_itbi, rl), _pct(-sim.custo_itbi, v)),
                    (2, "Custo de IPTU do terreno", _fmt(-sim.custo_iptu), _pct(-sim.custo_iptu, rl), _pct(-sim.custo_iptu, v)),
                    (0, "", "", "", ""),
                    # --- DESPESAS ---
                    (0, "(-) DESPESAS", _fmt(-sim.despesa_total), _pct(-sim.despesa_total, rl), _pct(-sim.despesa_total, v)),
                    (1, "Despesas comerciais", _fmt(-(sim.despesa_comercial)), _pct(-(sim.despesa_comercial), rl), _pct(-(sim.despesa_comercial), v)),
                    (2, "Comissões (corretagem)", _fmt(-sim.desp_comissoes), _pct(-sim.desp_comissoes, rl), _pct(-sim.desp_comissoes, v)),
                    (2, "Premiação de corretores", _fmt(-sim.desp_premiacao), _pct(-sim.desp_premiacao, rl), _pct(-sim.desp_premiacao, v)),
                    (2, "Central de vendas / Stand", _fmt(-sim.desp_stand), _pct(-sim.desp_stand, rl), _pct(-sim.desp_stand, v)),
                    (2, "Coordenação comercial", _fmt(-sim.desp_coordenacao), _pct(-sim.desp_coordenacao, rl), _pct(-sim.desp_coordenacao, v)),
                    (1, "Despesas de marketing", _fmt(-sim.desp_marketing), _pct(-sim.desp_marketing, rl), _pct(-sim.desp_marketing, v)),
                    (1, "Despesas administrativas", _fmt(-sim.despesa_administrativa), _pct(-sim.despesa_administrativa, rl), _pct(-sim.despesa_administrativa, v)),
                    (2, "Gerenciamento / Taxa de gestão", _fmt(-sim.desp_gestao), _pct(-sim.desp_gestao, rl), _pct(-sim.desp_gestao, v)),
                    (2, "Despesas administrativas SPE", _fmt(-sim.desp_admin), _pct(-sim.desp_admin, rl), _pct(-sim.desp_admin, v)),
                    (2, "Seguros", _fmt(-sim.desp_seguros), _pct(-sim.desp_seguros, rl), _pct(-sim.desp_seguros, v)),
                    (2, "Despesas pré-operacionais", _fmt(-sim.desp_preop), _pct(-sim.desp_preop, rl), _pct(-sim.desp_preop, v)),
                    (1, "Despesas cartoriais", _fmt(-sim.despesa_cartorial), _pct(-sim.despesa_cartorial, rl), _pct(-sim.despesa_cartorial, v)),
                    (2, "Registro de incorporação / loteamento", _fmt(-sim.desp_ri), _pct(-sim.desp_ri, rl), _pct(-sim.desp_ri, v)),
                    (2, "Escrituras e registros", _fmt(-sim.desp_escrituras), _pct(-sim.desp_escrituras, rl), _pct(-sim.desp_escrituras, v)),
                    (1, "Impostos sobre receita", _fmt(-sim.despesa_tributaria), _pct(-sim.despesa_tributaria, rl), _pct(-sim.despesa_tributaria, v)),
                    (0, "", "", "", ""),
                    # --- RESULTADO OPERACIONAL ---
                    (0, "(=) ATIVIDADES OPERACIONAIS", _fmt(sim.resultado_projeto), _pct(sim.resultado_projeto, rl), _pct(sim.resultado_projeto, v)),
                    (0, "", "", "", ""),
                    # --- RESULTADO FINAL ---
                    (0, "(=) RESULTADO DO PROJETO", _fmt(sim.resultado_projeto), _pct(sim.resultado_projeto, rl), f"{sim.margem_vgv:.1f}%"),
                    (0, "", "", "", ""),
                    # --- SALDO ---
                    (0, "SALDO ACUMULADO FINAL", _fmt(sim.fluxo_acumulado[-1] if sim.fluxo_acumulado else 0), "", ""),
                    (0, "EXPOSIÇÃO MÁXIMA DE CAIXA", _fmt(sim.exposicao_maxima), "", _pct(abs(sim.exposicao_maxima), v)),
                ]

                # Construir DataFrame com indentação visual
                df_linhas = []
                for indent, label, nominal, margem, pct_vgv in linhas:
                    prefix = "    " * indent
                    df_linhas.append({
                        "Linha": f"{prefix}{label}",
                        "Nominal (R$)": nominal,
                        "Margem Nominal": margem,
                        "% VGV": pct_vgv,
                    })

                df_dfc = pd.DataFrame(df_linhas)
                st.dataframe(df_dfc, use_container_width=True, hide_index=True, height=1200)

                # === Gráfico de Fluxo de Caixa ===
                st.markdown("---")
                st.markdown("### Fluxo de Caixa Acumulado")

                # Preparar dados para gráfico
                df_fluxo = pd.DataFrame({
                    "Mês": sim.labels_mes if sim.labels_mes else list(range(sim.total_meses)),
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
                    # Usar label do primeiro mês do trimestre se disponível
                    if sim.labels_mes and inicio < len(sim.labels_mes):
                        trim_labels.append(sim.labels_mes[inicio])
                    else:
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

                # === Diagnóstico e Recomendações ===
                st.markdown("---")
                st.markdown("### Diagnóstico e Recomendações")
                st.markdown(
                    "Análise comparativa das premissas atuais contra benchmarks "
                    "de mercado, com sugestões para melhorar o resultado do projeto."
                )

                diagnostico = gerar_diagnostico(resultado, sim)

                if not diagnostico:
                    st.success("Todas as premissas estão dentro dos padrões de mercado.")
                else:
                    # Contadores
                    n_criticos = sum(1 for d in diagnostico if d.severidade == "critico")
                    n_atencao = sum(1 for d in diagnostico if d.severidade == "atencao")
                    n_positivos = sum(1 for d in diagnostico if d.severidade == "positivo")

                    # Resumo do diagnóstico
                    res_col1, res_col2, res_col3 = st.columns(3)
                    res_col1.metric("Pontos Críticos", n_criticos)
                    res_col2.metric("Pontos de Atenção", n_atencao)
                    res_col3.metric("Pontos Positivos", n_positivos)

                    st.markdown("")

                    # Renderizar cada item
                    for i, item in enumerate(diagnostico):
                        if item.severidade == "critico":
                            icone = "🔴"
                            cor_titulo = "Crítico"
                        elif item.severidade == "atencao":
                            icone = "🟡"
                            cor_titulo = "Atenção"
                        else:
                            icone = "🟢"
                            cor_titulo = "Positivo"

                        cat_label = {
                            "receita": "Receita",
                            "custo": "Custo",
                            "despesa": "Despesa",
                            "financeiro": "Financeiro",
                            "tese": "Tese de Negócio",
                        }.get(item.categoria, item.categoria)

                        with st.expander(
                            f"{icone} **[{cor_titulo}]** {item.titulo}  —  _{cat_label}_",
                            expanded=(item.severidade == "critico"),
                        ):
                            st.markdown(item.descricao)
                            st.markdown("")

                            comp_col1, comp_col2 = st.columns(2)
                            comp_col1.metric("Valor Atual", item.premissa_atual)
                            comp_col2.metric("Benchmark de Mercado", item.benchmark)

                            if item.severidade != "positivo":
                                st.markdown("---")
                                st.markdown(f"**Recomendação:**")
                                st.info(item.sugestao)
                            else:
                                st.markdown("---")
                                st.markdown(f"**Comentário:** {item.sugestao}")

                    # Síntese final
                    if n_criticos > 0:
                        st.markdown("---")
                        st.markdown("### Síntese — O que fazer para viabilizar o projeto")

                        # Calcular gap de margem
                        margem_alvo = 18.0
                        gap = margem_alvo - sim.margem_vgv
                        gap_reais = sim.vgv * gap / 100

                        st.markdown(
                            f"Para atingir uma **margem de {margem_alvo:.0f}%**, o projeto "
                            f"precisa melhorar o resultado em aproximadamente "
                            f"**R$ {gap_reais:,.0f}** ({gap:.1f}pp do VGV)."
                        )

                        st.markdown("**Alavancas prioritárias (por ordem de impacto):**")

                        # Gerar alavancas dinamicamente
                        alavancas = []
                        terreno_pct = sim.custo_terreno / sim.vgv * 100 if sim.vgv > 0 else 0
                        if terreno_pct > 15:
                            economia = sim.vgv * (terreno_pct - 15) / 100
                            alavancas.append(
                                f"**Terreno**: renegociar de {terreno_pct:.0f}% para 15% do VGV "
                                f"— economia de ~R$ {economia:,.0f}"
                            )

                        constr_pct = sim.custo_construcao_infra / sim.vgv * 100 if sim.vgv > 0 else 0
                        bench_c = 35 if resultado.e_loteamento else 40
                        if constr_pct > bench_c:
                            economia = sim.vgv * (constr_pct - bench_c) / 100
                            alavancas.append(
                                f"**Construção**: otimizar de {constr_pct:.0f}% para "
                                f"{bench_c}% do VGV — economia de ~R$ {economia:,.0f}"
                            )

                        comerc_pct = sim.despesa_comercial / sim.vgv * 100 if sim.vgv > 0 else 0
                        if comerc_pct > 9:
                            economia = sim.vgv * (comerc_pct - 9) / 100
                            alavancas.append(
                                f"**Despesas Comerciais**: reduzir de {comerc_pct:.0f}% para "
                                f"9% do VGV — economia de ~R$ {economia:,.0f}"
                            )

                        aliq = _get_premissa_valor(resultado, "Alíquota tributária (regime sugerido)", 0)
                        if aliq > 4.5:
                            economia = sim.receita_liquida * (aliq - 4.0) / 100
                            alavancas.append(
                                f"**Regime tributário**: migrar para RET (4%) "
                                f"— economia de ~R$ {economia:,.0f}"
                            )

                        distrato_v = _get_premissa_valor(resultado, "Taxa de distrato estimada", 0)
                        bench_d = 8.0
                        if distrato_v > bench_d + 3:
                            receita_extra = sim.vgv * (distrato_v - bench_d) / 100 * 0.7
                            alavancas.append(
                                f"**Distrato**: reduzir de {distrato_v:.0f}% para {bench_d:.0f}% "
                                f"— receita extra de ~R$ {receita_extra:,.0f}"
                            )

                        if not alavancas:
                            alavancas.append(
                                "Buscar otimizações incrementais em múltiplas linhas "
                                "de custo e despesa."
                            )

                        for idx, alav in enumerate(alavancas, 1):
                            st.markdown(f"{idx}. {alav}")

                        economia_total = sum(
                            sim.vgv * max(0, (sim.custo_terreno / sim.vgv * 100) - 15) / 100
                            if sim.vgv > 0 else 0
                            for _ in [1]
                        )

                        st.markdown("")
                        st.info(
                            "Ajuste as premissas nas abas anteriores (Receita, Custo, "
                            "Despesa, Financeiro, Tabela de Vendas) e o resultado será "
                            "recalculado automaticamente nesta simulação."
                        )

        # --- DFC Aberto (mês a mês) ---
        with tab_dfc_aberto:
            st.subheader("DFC Aberto — Fluxo de Caixa Mês a Mês")
            st.markdown(
                "Visão completa do fluxo de caixa aberto, com cada linha de receita, custo e despesa "
                "detalhada mês a mês, no formato padrão Trinus. "
                "As 3 primeiras linhas mostram os totais nominais, margem sobre receita líquida e % do VGV."
            )

            # Aplicar edições e simular
            _aplicar_edicoes(resultado, editadas)
            sim_dfc = simular(resultado, datas_macro=st.session_state.get("datas_macro"))

            if sim_dfc.vgv <= 0:
                st.warning("Preencha o VGV estimado para gerar o DFC Aberto.")
            else:
                df_dfc_aberto = dfc_aberto_dataframe(sim_dfc, resultado.e_loteamento)

                if df_dfc_aberto.empty:
                    st.warning("Nenhum dado para exibir.")
                else:
                    # Salvar simulação para uso na exportação
                    st.session_state["sim_dfc"] = sim_dfc

                    # Controles de visualização
                    ctrl_col1, ctrl_col2 = st.columns([1, 1])
                    with ctrl_col1:
                        mostrar_zeros = st.checkbox(
                            "Mostrar meses sem movimentação",
                            value=False,
                            key="dfc_mostrar_zeros",
                            help="Se desmarcado, meses onde todas as colunas financeiras são zero serão ocultados.",
                        )
                    with ctrl_col2:
                        formato_display = st.radio(
                            "Formato de exibição",
                            options=["Valores numéricos", "Formatado (R$)"],
                            index=0,
                            horizontal=True,
                            key="dfc_formato",
                        )

                    # Filtrar meses sem movimentação
                    df_view = df_dfc_aberto.copy()
                    if not mostrar_zeros:
                        # Manter as 3 primeiras linhas (resumo) + linhas com algum valor != 0
                        financial_cols = [c for c in df_view.columns if c != "Mês"]
                        mask_summary = df_view.index < 3
                        mask_data = pd.Series(False, index=df_view.index)
                        for idx in df_view.index:
                            if idx >= 3:
                                for col in financial_cols:
                                    val = df_view.at[idx, col]
                                    if isinstance(val, (int, float)) and abs(val) > 0.01:
                                        mask_data.at[idx] = True
                                        break
                        df_view = df_view[mask_summary | mask_data].reset_index(drop=True)

                    # Formatação para exibição
                    if formato_display == "Formatado (R$)":
                        def _fmt_cell(val):
                            if isinstance(val, str):
                                return val
                            if isinstance(val, (int, float)):
                                if abs(val) < 0.01:
                                    return "-"
                                return f"R$ {val:,.0f}".replace(",", ".")
                            return val

                        df_display = df_view.copy()
                        for col in df_display.columns:
                            if col != "Mês":
                                df_display[col] = df_display[col].apply(_fmt_cell)
                    else:
                        df_display = df_view

                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        hide_index=True,
                        height=min(800, 35 * len(df_display) + 38),
                    )

                    st.markdown("---")

                    # Botão de exportação do DFC Aberto
                    st.markdown("### Exportar DFC Aberto")
                    exp_col1, exp_col2 = st.columns(2)

                    with exp_col1:
                        excel_dfc = exportar_dfc_aberto_excel_bytes(sim_dfc, resultado.e_loteamento)
                        st.download_button(
                            "Baixar DFC Aberto (.xlsx)",
                            data=excel_dfc,
                            file_name=f"dfc_aberto_{resultado.versao}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            use_container_width=True,
                        )

                    with exp_col2:
                        # Exportar como CSV
                        csv_data = df_dfc_aberto.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
                        st.download_button(
                            "Baixar DFC Aberto (.csv)",
                            data=csv_data,
                            file_name=f"dfc_aberto_{resultado.versao}.csv",
                            mime="text/csv",
                            use_container_width=True,
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

        # Salvar estado final na base de conhecimento
        _sb = _get_supabase()
        _eid = st.session_state.get("estudo_id")
        if _sb and _eid:
            try:
                atualizar_status(_sb, _eid, "exportado")
            except Exception:
                pass

        with col_exp1:
            # Incluir DFC Aberto no Excel se simulação disponível
            sim_export = st.session_state.get("sim_dfc")
            if sim_export is None:
                _aplicar_edicoes(resultado, st.session_state.get("premissas_editadas", {}))
                sim_export = simular(resultado, datas_macro=st.session_state.get("datas_macro"))
            excel_bytes = exportar_excel_bytes(resultado, sim=sim_export)
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
