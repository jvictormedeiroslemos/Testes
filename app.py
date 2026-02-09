"""
Ferramenta DE-PARA: Mapeamento de Despesas e Receitas para a EAP Interna.

Uso:
    streamlit run app.py
"""

import json
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from eap_parser import (
    get_mapping_options,
    get_obras,
    parse_eap,
)
from ai_mapper import suggest_by_similarity, suggest_batch_by_similarity, suggest_by_ai

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DE-PARA | Mapeamento EAP",
    page_icon="📊",
    layout="wide",
)

EAP_FILE = Path("Plano de Contas.xlsx")
MAPPINGS_FILE = Path("mappings.json")


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def load_saved_mappings() -> dict:
    """Carrega mapeamentos salvos anteriormente."""
    if MAPPINGS_FILE.exists():
        with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_mappings(mappings: dict):
    """Salva mapeamentos em arquivo JSON para reutilização."""
    with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Converte DataFrame para bytes de arquivo Excel."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="DE-PARA")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Carregar EAP
# ---------------------------------------------------------------------------
@st.cache_data
def load_eap():
    return parse_eap(EAP_FILE)


@st.cache_data
def load_eap_options():
    df_eap = load_eap()
    options_df = get_mapping_options(df_eap)
    return options_df


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------
st.title("DE-PARA | Mapeamento de Despesas e Receitas")
st.markdown(
    "Ferramenta para apropriar lançamentos de despesas e receitas "
    "à estrutura interna de EAP (Plano de Contas)."
)

# Verificar se arquivo EAP existe
if not EAP_FILE.exists():
    st.error(f"Arquivo '{EAP_FILE}' não encontrado. Coloque-o na mesma pasta do app.")
    st.stop()

df_eap = load_eap()
options_df = load_eap_options()
obras = get_obras(df_eap)

# ---------------------------------------------------------------------------
# Sidebar: Visualizar EAP
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Estrutura EAP")
    obra_filter = st.selectbox("Filtrar por Obra:", ["TODAS"] + obras)

    if obra_filter == "TODAS":
        eap_view = df_eap
    else:
        eap_view = df_eap[df_eap["Obra"] == obra_filter]

    st.dataframe(
        eap_view[["Obra", "Produto", "Item", "Descricao"]].drop_duplicates(),
        height=500,
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown(f"**Total de registros EAP:** {len(df_eap)}")
    st.markdown(f"**Obras:** {len(obras)}")

# ---------------------------------------------------------------------------
# Tabs principais
# ---------------------------------------------------------------------------
tab_ai, tab_mapping, tab_batch, tab_saved, tab_export = st.tabs(
    ["Mapeamento com IA", "Mapeamento Manual", "Mapeamento em Lote", "Mapeamentos Salvos", "Exportar"]
)

# ========================== TAB IA: MAPEAMENTO COM IA =====================
with tab_ai:
    st.subheader("Mapeamento Inteligente com IA")
    st.markdown(
        "Faça upload de uma planilha ou insira descrições de lançamentos. "
        "A IA analisa cada item e sugere automaticamente o mapeamento para a EAP."
    )

    # Configuração do modo de IA
    ai_mode = st.radio(
        "Modo de análise:",
        ["Similaridade Textual (offline, sem API)", "Claude API (análise semântica avançada)"],
        key="ai_mode",
        horizontal=True,
    )

    api_key = None
    if "Claude API" in ai_mode:
        api_key = st.text_input(
            "Anthropic API Key:",
            type="password",
            key="ai_api_key",
            help="Obtenha em console.anthropic.com. A chave não é armazenada.",
        )
        if not api_key:
            st.warning("Insira sua API Key da Anthropic para usar o modo Claude API.")

    st.markdown("---")

    # Escolher fonte dos dados
    ai_source = st.radio(
        "Fonte dos lançamentos:",
        ["Digitar manualmente", "Upload de planilha"],
        key="ai_source",
        horizontal=True,
    )

    descriptions_to_map = []

    if ai_source == "Digitar manualmente":
        ai_text = st.text_area(
            "Descrições dos lançamentos (uma por linha):",
            height=200,
            key="ai_text_input",
            placeholder="Ex:\nPagamento energia elétrica obra\nComissão corretor João\nNota fiscal cimento 50 sacos\nHonorários advocatícios",
        )
        if ai_text:
            descriptions_to_map = [line.strip() for line in ai_text.strip().split("\n") if line.strip()]

    else:  # Upload
        ai_upload = st.file_uploader(
            "Upload da planilha:",
            type=["xlsx", "xls", "csv"],
            key="ai_upload",
        )
        if ai_upload:
            if ai_upload.name.endswith(".csv"):
                df_ai_input = pd.read_csv(ai_upload)
            else:
                xls_ai = pd.ExcelFile(ai_upload)
                if len(xls_ai.sheet_names) > 1:
                    ai_sheet = st.selectbox("Aba:", xls_ai.sheet_names, key="ai_sheet")
                else:
                    ai_sheet = xls_ai.sheet_names[0]
                df_ai_input = pd.read_excel(ai_upload, sheet_name=ai_sheet)

            st.dataframe(df_ai_input.head(10), use_container_width=True)

            ai_col_desc = st.selectbox(
                "Coluna com as descrições:",
                df_ai_input.columns.tolist(),
                key="ai_col_desc",
            )
            descriptions_to_map = df_ai_input[ai_col_desc].dropna().astype(str).tolist()

    # Filtro de obra para IA
    ai_obra_filter = st.selectbox(
        "Filtrar sugestões por Obra (opcional):",
        ["TODAS"] + obras,
        key="ai_obra_filter",
    )

    if ai_obra_filter == "TODAS":
        ai_options = options_df
    else:
        ai_options = options_df[options_df["Obra"] == ai_obra_filter]

    # Botão de análise
    if descriptions_to_map:
        st.markdown(f"**{len(descriptions_to_map)} lançamento(s) para analisar**")

        if st.button("Analisar com IA", key="btn_ai_analyze", type="primary"):
            with st.spinner("Analisando lançamentos..."):
                if "Claude API" in ai_mode and api_key:
                    # Modo Claude API
                    try:
                        ai_results = suggest_by_ai(
                            descriptions_to_map,
                            ai_options,
                            api_key=api_key,
                        )
                        if "_error" in ai_results:
                            st.error(f"Erro na resposta da API: {ai_results['_error']}")
                        else:
                            st.session_state["ai_suggestions"] = ai_results
                            st.session_state["ai_descriptions"] = descriptions_to_map
                            st.success("Análise concluída com Claude API!")
                    except Exception as e:
                        st.error(f"Erro ao chamar API: {e}")
                else:
                    # Modo similaridade textual
                    ai_results = suggest_batch_by_similarity(
                        descriptions_to_map,
                        ai_options,
                        top_n=5,
                    )
                    st.session_state["ai_suggestions"] = ai_results
                    st.session_state["ai_descriptions"] = descriptions_to_map
                    st.success("Análise por similaridade concluída!")

    # Exibir resultados da IA
    if st.session_state.get("ai_suggestions"):
        st.markdown("---")
        st.markdown("### Sugestões da IA")

        ai_suggestions = st.session_state["ai_suggestions"]
        ai_descs = st.session_state.get("ai_descriptions", [])
        saved_mappings = load_saved_mappings()
        ai_labels = ai_options["Label"].tolist()

        if "ai_accepted" not in st.session_state:
            st.session_state["ai_accepted"] = {}

        for idx, desc in enumerate(ai_descs):
            suggestions = ai_suggestions.get(desc, [])

            with st.expander(f"**{desc}**", expanded=True):
                if suggestions:
                    # Mostrar sugestões como tabela
                    df_sug = pd.DataFrame(suggestions)
                    display_cols = ["Obra", "Item", "Descricao_EAP", "Score"]
                    if "Justificativa" in df_sug.columns:
                        display_cols.append("Justificativa")
                    st.dataframe(
                        df_sug[display_cols],
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Selecionar sugestão ou escolher manualmente
                    suggestion_labels = [s["Label"] for s in suggestions if s["Label"] in ai_labels]
                    choice_options = suggestion_labels + ["-- Escolher manualmente --"]

                    choice = st.selectbox(
                        "Aceitar sugestão:",
                        choice_options,
                        key=f"ai_choice_{idx}",
                    )

                    if choice == "-- Escolher manualmente --":
                        manual_choice = st.selectbox(
                            "Selecionar item EAP:",
                            ai_labels,
                            key=f"ai_manual_{idx}",
                        )
                        st.session_state["ai_accepted"][desc] = manual_choice
                    else:
                        st.session_state["ai_accepted"][desc] = choice
                else:
                    st.warning("Nenhuma sugestão encontrada.")
                    manual_choice = st.selectbox(
                        "Selecionar item EAP manualmente:",
                        ai_labels,
                        key=f"ai_manual_nosug_{idx}",
                    )
                    st.session_state["ai_accepted"][desc] = manual_choice

        # Salvar mapeamentos aceitos
        if st.button("Confirmar todos os mapeamentos da IA", key="btn_ai_confirm", type="primary"):
            accepted = st.session_state.get("ai_accepted", {})
            for desc, label in accepted.items():
                if label:
                    saved_mappings[desc] = label
            save_mappings(saved_mappings)

            # Gerar resultado
            ai_final = []
            for desc in ai_descs:
                label = accepted.get(desc, "")
                entry = {"Descricao_Original": desc}
                if label and label in ai_options["Label"].values:
                    eap_row = ai_options[ai_options["Label"] == label].iloc[0]
                    entry["EAP_Obra"] = eap_row["Obra"]
                    entry["EAP_Produto"] = eap_row["Produto"]
                    entry["EAP_Item"] = eap_row["Item"]
                    entry["EAP_Descricao"] = eap_row["Descricao"]
                    entry["Status"] = "Mapeado"
                else:
                    entry["EAP_Obra"] = ""
                    entry["EAP_Produto"] = ""
                    entry["EAP_Item"] = ""
                    entry["EAP_Descricao"] = ""
                    entry["Status"] = "Pendente"
                ai_final.append(entry)

            df_ai_final = pd.DataFrame(ai_final)
            st.session_state["ai_results"] = df_ai_final

            mapped = df_ai_final[df_ai_final["Status"] == "Mapeado"].shape[0]
            st.success(f"Mapeamentos confirmados! {mapped}/{len(ai_descs)} apropriados.")

        if st.session_state.get("ai_results") is not None:
            st.markdown("### Resultado Final")
            df_ai_result = st.session_state["ai_results"]
            st.dataframe(df_ai_result, use_container_width=True)

            excel_ai = to_excel_bytes(df_ai_result)
            st.download_button(
                "Baixar resultado IA (Excel)",
                data=excel_ai,
                file_name="de_para_ia.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

# ========================== TAB 1: MAPEAMENTO MANUAL =======================
with tab_mapping:
    st.subheader("Mapeamento Manual DE-PARA")
    st.markdown(
        "Insira os dados do lançamento original e selecione para qual "
        "item da EAP ele deve ser apropriado."
    )

    saved_mappings = load_saved_mappings()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### DE (Origem)")
        orig_desc = st.text_input("Descrição do lançamento original:", key="manual_desc")
        orig_valor = st.number_input("Valor (R$):", value=0.0, step=0.01, key="manual_valor")
        orig_tipo = st.selectbox("Tipo:", ["Despesa", "Receita"], key="manual_tipo")
        orig_data = st.date_input("Data do lançamento:", key="manual_data")
        orig_fornecedor = st.text_input("Fornecedor/Origem:", key="manual_fornecedor")

    with col2:
        st.markdown("### PARA (EAP Destino)")

        # Filtrar por obra
        dest_obra = st.selectbox(
            "Obra destino:",
            ["TODAS"] + obras,
            key="manual_dest_obra",
        )

        if dest_obra == "TODAS":
            filtered_options = options_df
        else:
            filtered_options = options_df[options_df["Obra"] == dest_obra]

        # Selecionar item EAP
        labels = filtered_options["Label"].tolist()

        # Sugestão automática baseada em mapeamentos anteriores
        default_idx = 0
        if orig_desc and orig_desc in saved_mappings:
            saved_label = saved_mappings[orig_desc]
            if saved_label in labels:
                default_idx = labels.index(saved_label)

        selected_label = st.selectbox(
            "Item EAP destino:",
            labels,
            index=default_idx if labels else 0,
            key="manual_dest_item",
        )

        if selected_label:
            selected_row = filtered_options[filtered_options["Label"] == selected_label].iloc[0]
            st.info(
                f"**Obra:** {selected_row['Obra']}  \n"
                f"**Produto:** {selected_row['Produto']}  \n"
                f"**Item:** {selected_row['Item']}  \n"
                f"**Descrição:** {selected_row['Descricao']}"
            )

    if st.button("Salvar Mapeamento", key="btn_manual_save", type="primary"):
        if orig_desc and selected_label:
            # Salvar no session state para exibir na tabela
            if "manual_results" not in st.session_state:
                st.session_state["manual_results"] = []

            mapping_entry = {
                "Descricao_Original": orig_desc,
                "Valor": orig_valor,
                "Tipo": orig_tipo,
                "Data": str(orig_data),
                "Fornecedor": orig_fornecedor,
                "EAP_Obra": selected_row["Obra"],
                "EAP_Produto": selected_row["Produto"],
                "EAP_Item": selected_row["Item"],
                "EAP_Descricao": selected_row["Descricao"],
            }
            st.session_state["manual_results"].append(mapping_entry)

            # Salvar mapeamento para reutilização
            saved_mappings[orig_desc] = selected_label
            save_mappings(saved_mappings)

            st.success("Mapeamento salvo com sucesso!")
        else:
            st.warning("Preencha a descrição e selecione um item EAP.")

    # Exibir resultados
    if st.session_state.get("manual_results"):
        st.markdown("### Mapeamentos realizados")
        df_results = pd.DataFrame(st.session_state["manual_results"])
        st.dataframe(df_results, use_container_width=True)

# ========================== TAB 2: MAPEAMENTO EM LOTE =====================
with tab_batch:
    st.subheader("Mapeamento em Lote (Upload de Planilha)")
    st.markdown(
        "Faça upload de uma planilha de despesas/receitas. "
        "O sistema vai identificar as colunas e permitir o mapeamento DE-PARA para cada linha."
    )

    uploaded_file = st.file_uploader(
        "Upload da planilha de lançamentos:",
        type=["xlsx", "xls", "csv"],
        key="batch_upload",
    )

    if uploaded_file:
        # Ler arquivo
        if uploaded_file.name.endswith(".csv"):
            df_input = pd.read_csv(uploaded_file)
        else:
            # Mostrar as sheets disponíveis
            xls = pd.ExcelFile(uploaded_file)
            if len(xls.sheet_names) > 1:
                sheet = st.selectbox("Selecione a aba:", xls.sheet_names)
            else:
                sheet = xls.sheet_names[0]
            df_input = pd.read_excel(uploaded_file, sheet_name=sheet)

        st.markdown("### Pré-visualização dos dados importados")
        st.dataframe(df_input.head(20), use_container_width=True)

        st.markdown("---")

        # Mapear colunas
        st.markdown("### Configurar colunas")
        cols = ["(não usar)"] + df_input.columns.tolist()

        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        with col_cfg1:
            col_desc = st.selectbox("Coluna de Descrição:", cols, key="batch_col_desc")
            col_valor = st.selectbox("Coluna de Valor:", cols, key="batch_col_valor")
        with col_cfg2:
            col_data = st.selectbox("Coluna de Data:", cols, key="batch_col_data")
            col_tipo = st.selectbox("Coluna de Tipo (Despesa/Receita):", cols, key="batch_col_tipo")
        with col_cfg3:
            col_fornecedor = st.selectbox("Coluna de Fornecedor:", cols, key="batch_col_forn")

        st.markdown("---")
        st.markdown("### Mapeamento DE-PARA por linha")

        # Obra destino padrão para lote
        batch_obra = st.selectbox(
            "Obra destino padrão (aplica a todas as linhas):",
            ["TODAS"] + obras,
            key="batch_obra_default",
        )

        if batch_obra == "TODAS":
            batch_options = options_df
        else:
            batch_options = options_df[options_df["Obra"] == batch_obra]

        batch_labels = ["(selecionar)"] + batch_options["Label"].tolist()

        # Carregar mapeamentos anteriores
        saved_mappings = load_saved_mappings()

        if "batch_mappings" not in st.session_state:
            st.session_state["batch_mappings"] = {}

        # Interface de mapeamento por linha
        num_rows = len(df_input)
        st.markdown(f"**Total de lançamentos: {num_rows}**")

        # Paginação
        page_size = 20
        total_pages = max(1, (num_rows + page_size - 1) // page_size)
        page = st.number_input("Página:", min_value=1, max_value=total_pages, value=1)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, num_rows)

        for i in range(start_idx, end_idx):
            row = df_input.iloc[i]
            desc_val = str(row[col_desc]) if col_desc != "(não usar)" else f"Linha {i + 1}"
            valor_val = row[col_valor] if col_valor != "(não usar)" else ""

            with st.expander(f"**Linha {i + 1}:** {desc_val} | R$ {valor_val}", expanded=False):
                # Mostrar dados originais
                st.markdown("**Dados originais:**")
                row_data = {c: str(row[c]) for c in df_input.columns}
                st.json(row_data)

                # Sugestão automática
                default_batch_idx = 0
                if desc_val in saved_mappings:
                    saved_label = saved_mappings[desc_val]
                    if saved_label in batch_labels:
                        default_batch_idx = batch_labels.index(saved_label)

                selected = st.selectbox(
                    "Mapear para EAP:",
                    batch_labels,
                    index=default_batch_idx,
                    key=f"batch_map_{i}",
                )

                if selected != "(selecionar)":
                    st.session_state["batch_mappings"][i] = selected
                    # Salvar para reutilização
                    saved_mappings[desc_val] = selected

        # Botão para aplicar mapeamentos em lote
        if st.button("Aplicar Mapeamentos em Lote", key="btn_batch_apply", type="primary"):
            save_mappings(saved_mappings)

            results = []
            for i in range(num_rows):
                row = df_input.iloc[i]
                mapped_label = st.session_state["batch_mappings"].get(i, None)

                entry = {}
                # Dados originais
                for c in df_input.columns:
                    entry[f"ORIG_{c}"] = row[c]

                # Dados EAP mapeados
                if mapped_label and mapped_label in batch_options["Label"].values:
                    eap_row = batch_options[batch_options["Label"] == mapped_label].iloc[0]
                    entry["EAP_Obra"] = eap_row["Obra"]
                    entry["EAP_Produto"] = eap_row["Produto"]
                    entry["EAP_Item"] = eap_row["Item"]
                    entry["EAP_Descricao"] = eap_row["Descricao"]
                    entry["Status"] = "Mapeado"
                else:
                    entry["EAP_Obra"] = ""
                    entry["EAP_Produto"] = ""
                    entry["EAP_Item"] = ""
                    entry["EAP_Descricao"] = ""
                    entry["Status"] = "Pendente"

                results.append(entry)

            df_result = pd.DataFrame(results)
            st.session_state["batch_results"] = df_result
            st.success(
                f"Mapeamento aplicado! "
                f"{df_result[df_result['Status'] == 'Mapeado'].shape[0]}/{num_rows} mapeados."
            )

        # Exibir resultado do lote
        if st.session_state.get("batch_results") is not None:
            st.markdown("### Resultado do Mapeamento em Lote")
            df_batch_result = st.session_state["batch_results"]

            # Resumo
            col_r1, col_r2, col_r3 = st.columns(3)
            mapped_count = df_batch_result[df_batch_result["Status"] == "Mapeado"].shape[0]
            pending_count = df_batch_result[df_batch_result["Status"] == "Pendente"].shape[0]
            col_r1.metric("Total", len(df_batch_result))
            col_r2.metric("Mapeados", mapped_count)
            col_r3.metric("Pendentes", pending_count)

            st.dataframe(df_batch_result, use_container_width=True, height=400)

            # Download
            excel_bytes = to_excel_bytes(df_batch_result)
            st.download_button(
                "Baixar resultado (Excel)",
                data=excel_bytes,
                file_name="de_para_resultado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

# ========================== TAB 3: MAPEAMENTOS SALVOS =====================
with tab_saved:
    st.subheader("Mapeamentos Salvos")
    st.markdown(
        "Mapeamentos anteriores são salvos automaticamente. "
        "Quando uma descrição já conhecida aparecer, o sistema sugere o mapeamento anterior."
    )

    saved_mappings = load_saved_mappings()

    if saved_mappings:
        df_saved = pd.DataFrame(
            [
                {"Descricao_Original": k, "EAP_Destino": v}
                for k, v in saved_mappings.items()
            ]
        )
        st.dataframe(df_saved, use_container_width=True)

        # Permitir edição
        st.markdown("### Remover mapeamento")
        to_remove = st.multiselect(
            "Selecione mapeamentos para remover:",
            list(saved_mappings.keys()),
        )
        if st.button("Remover selecionados", key="btn_remove_mappings"):
            for key in to_remove:
                saved_mappings.pop(key, None)
            save_mappings(saved_mappings)
            st.success("Mapeamentos removidos.")
            st.rerun()

        # Download dos mapeamentos
        json_bytes = json.dumps(saved_mappings, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            "Baixar mapeamentos (JSON)",
            data=json_bytes,
            file_name="mappings.json",
            mime="application/json",
        )

        # Upload de mapeamentos
        st.markdown("### Importar mapeamentos")
        uploaded_mappings = st.file_uploader(
            "Upload de arquivo de mapeamentos (JSON):",
            type=["json"],
            key="upload_mappings",
        )
        if uploaded_mappings:
            imported = json.load(uploaded_mappings)
            saved_mappings.update(imported)
            save_mappings(saved_mappings)
            st.success(f"Importados {len(imported)} mapeamentos.")
            st.rerun()
    else:
        st.info("Nenhum mapeamento salvo ainda. Realize mapeamentos nas abas anteriores.")

# ========================== TAB 4: EXPORTAR ===============================
with tab_export:
    st.subheader("Exportar Dados")

    st.markdown("### Exportar estrutura EAP completa")
    excel_eap = to_excel_bytes(df_eap)
    st.download_button(
        "Baixar EAP completa (Excel)",
        data=excel_eap,
        file_name="eap_completa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if st.session_state.get("manual_results"):
        st.markdown("### Exportar mapeamentos manuais")
        df_manual = pd.DataFrame(st.session_state["manual_results"])
        excel_manual = to_excel_bytes(df_manual)
        st.download_button(
            "Baixar mapeamentos manuais (Excel)",
            data=excel_manual,
            file_name="de_para_manual.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if st.session_state.get("batch_results") is not None:
        st.markdown("### Exportar mapeamentos em lote")
        df_batch = st.session_state["batch_results"]
        excel_batch = to_excel_bytes(df_batch)
        st.download_button(
            "Baixar mapeamentos em lote (Excel)",
            data=excel_batch,
            file_name="de_para_lote.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
