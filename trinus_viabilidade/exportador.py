"""
Trinus Viabilidade - Exportação de premissas.

Exporta resultados em JSON e Excel.
"""

from __future__ import annotations

import json
from io import BytesIO
from datetime import datetime

import pandas as pd

from modelos import ResultadoPremissas


def exportar_json(resultado: ResultadoPremissas) -> str:
    """Exporta premissas para JSON formatado."""
    data = resultado.to_dict()
    data["exportado_em"] = datetime.now().isoformat()
    return json.dumps(data, ensure_ascii=False, indent=2)


def exportar_json_bytes(resultado: ResultadoPremissas) -> bytes:
    """Exporta premissas para bytes JSON (para download)."""
    return exportar_json(resultado).encode("utf-8")


def _premissas_para_dataframe(resultado: ResultadoPremissas) -> pd.DataFrame:
    """Converte premissas para DataFrame do pandas."""
    rows = []
    for p in resultado.premissas:
        rows.append({
            "Categoria": p.categoria,
            "Subcategoria": p.subcategoria,
            "Premissa": p.nome,
            "Valor": p.valor,
            "Unidade": p.unidade,
            "Mínimo": p.valor_min,
            "Máximo": p.valor_max,
            "Fonte": p.fonte,
            "Descrição": p.descricao,
        })
    return pd.DataFrame(rows)


def _inputs_para_dataframe(resultado: ResultadoPremissas) -> pd.DataFrame:
    """Converte inputs do usuário para DataFrame."""
    inp = resultado.inputs
    rows = [
        {"Campo": "Tipologia", "Valor": inp.tipologia.value},
        {"Campo": "Estado", "Valor": inp.estado},
        {"Campo": "Cidade", "Valor": inp.cidade},
        {"Campo": "Região", "Valor": inp.regiao.value},
        {"Campo": "Padrão", "Valor": inp.padrao.value},
        {"Campo": "Nº Unidades", "Valor": inp.num_unidades},
        {"Campo": "Tipo de Negociação", "Valor": inp.tipo_negociacao.value},
        {"Campo": "Área do Terreno (m²)", "Valor": inp.area_terreno_m2 or "Não informado"},
        {"Campo": "VGV Estimado (R$)", "Valor": inp.vgv_estimado or "Calculado pelo sistema"},
        {"Campo": "Área Privativa Média (m²)", "Valor": inp.area_privativa_media_m2 or "Estimado pelo sistema"},
    ]
    # Parâmetros de negociação
    if inp.permuta_percentual is not None:
        rows.append({"Campo": "Permuta (%)", "Valor": inp.permuta_percentual})
    if inp.permuta_referencia:
        rows.append({"Campo": "Referência da Permuta", "Valor": inp.permuta_referencia})
    if inp.valor_aquisicao is not None:
        rows.append({"Campo": "Valor da Aquisição (R$)", "Valor": inp.valor_aquisicao})
    return pd.DataFrame(rows)


def _tabela_vendas_para_dataframe(resultado: ResultadoPremissas) -> pd.DataFrame:
    """Converte tabela de vendas para DataFrame."""
    tv = resultado.tabela_vendas
    if not tv:
        return pd.DataFrame()
    rows = [
        {"Condição": "Entrada", "Percentual (%)": tv.entrada_pct},
        {"Condição": "Parcelas durante obra", "Percentual (%)": tv.parcelas_obra_pct},
        {"Condição": "Financiamento (chaves)", "Percentual (%)": tv.financiamento_pct},
        {"Condição": "Reforços", "Percentual (%)": tv.reforcos_pct},
        {"Condição": "Nº parcelas durante obra", "Percentual (%)": tv.num_parcelas_obra},
    ]
    return pd.DataFrame(rows)


def _resumo_dfc_dataframe(resultado: ResultadoPremissas) -> pd.DataFrame:
    """Gera resumo consolidado no formato DFC."""
    vgv_p = resultado.get_premissa("VGV estimado")
    vgv_val = vgv_p.valor if vgv_p else 0

    rows = []
    for cat in ["Receita", "Custo", "Despesa", "Financeiro"]:
        rows.append({"Categoria DFC": f"=== {cat.upper()} ===", "Premissa": "", "Valor": "", "Unidade": "", "Valor Estimado (R$)": ""})
        for p in resultado.por_categoria(cat):
            valor_abs = ""
            if p.unidade == "R$":
                valor_abs = f"R$ {p.valor:,.2f}"
            elif ("% do VGV" in p.unidade or "% sobre receita" in p.unidade) and vgv_val > 0:
                valor_abs = f"R$ {vgv_val * p.valor / 100:,.2f}"
            rows.append({
                "Categoria DFC": p.subcategoria,
                "Premissa": p.nome,
                "Valor": p.valor,
                "Unidade": p.unidade,
                "Valor Estimado (R$)": valor_abs,
            })
    return pd.DataFrame(rows)


def exportar_excel_bytes(resultado: ResultadoPremissas) -> bytes:
    """Exporta premissas para bytes Excel (para download)."""
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Aba 1: Inputs
        df_inputs = _inputs_para_dataframe(resultado)
        df_inputs.to_excel(writer, index=False, sheet_name="Inputs")

        # Aba 2: Premissas completas
        df_premissas = _premissas_para_dataframe(resultado)
        df_premissas.to_excel(writer, index=False, sheet_name="Premissas")

        # Aba 3: Tabela de vendas
        df_vendas = _tabela_vendas_para_dataframe(resultado)
        if not df_vendas.empty:
            df_vendas.to_excel(writer, index=False, sheet_name="Tabela de Vendas")

        # Abas por categoria (dinâmico)
        categorias = df_premissas["Categoria"].unique()
        for cat in categorias:
            df_cat = df_premissas[df_premissas["Categoria"] == cat].copy()
            if not df_cat.empty:
                # Limitar nome da aba a 31 caracteres (limite Excel)
                sheet_name = cat[:31]
                df_cat.to_excel(writer, index=False, sheet_name=sheet_name)

        # Aba Resumo DFC
        df_resumo = _resumo_dfc_dataframe(resultado)
        if not df_resumo.empty:
            df_resumo.to_excel(writer, index=False, sheet_name="Resumo DFC")

    return buffer.getvalue()


def premissas_para_dataframe(resultado: ResultadoPremissas) -> pd.DataFrame:
    """Interface pública para converter premissas em DataFrame."""
    return _premissas_para_dataframe(resultado)


def inputs_para_dataframe(resultado: ResultadoPremissas) -> pd.DataFrame:
    """Interface pública para converter inputs em DataFrame."""
    return _inputs_para_dataframe(resultado)


def tabela_vendas_para_dataframe(resultado: ResultadoPremissas) -> pd.DataFrame:
    """Interface pública para converter tabela de vendas em DataFrame."""
    return _tabela_vendas_para_dataframe(resultado)
