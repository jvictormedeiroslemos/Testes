"""
Parser para a planilha de Plano de Contas (EAP).
Extrai a estrutura hierárquica: Obra > Produto > Item > Serviço/Insumo.
"""

import pandas as pd
from pathlib import Path


def parse_eap(file_path: str | Path) -> pd.DataFrame:
    """
    Lê a planilha de Plano de Contas e retorna um DataFrame estruturado
    com as colunas: Obra, Produto, Item, Controle, Servico, Insumo, Descricao.
    Preenche os campos hierárquicos (Obra, Produto) para baixo (forward fill).
    """
    df = pd.read_excel(
        file_path,
        sheet_name="SPE",
        header=1,
        names=["Obra", "Produto", "Item", "Controle", "Servico", "Insumo", "Descricao"],
    )

    # Remover linhas completamente vazias
    df = df.dropna(how="all").reset_index(drop=True)

    # Forward fill nos campos hierárquicos
    df["Obra"] = df["Obra"].ffill()
    df["Produto"] = df["Produto"].ffill()

    # Limpar espaços
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("nan", "")
            df[col] = df[col].replace("None", "")

    # Remover linhas sem item e sem descrição
    df = df[df["Item"].str.len() > 0].reset_index(drop=True)

    return df


def get_obras(df: pd.DataFrame) -> list[str]:
    """Retorna lista única de Obras."""
    return sorted(df["Obra"].unique().tolist())


def get_produtos(df: pd.DataFrame, obra: str = None) -> list[str]:
    """Retorna lista única de Produtos, opcionalmente filtrado por Obra."""
    subset = df if obra is None else df[df["Obra"] == obra]
    return sorted(subset["Produto"].unique().tolist())


def get_items_tree(df: pd.DataFrame, obra: str = None, produto: str = None) -> pd.DataFrame:
    """Retorna itens filtrados por Obra e/ou Produto."""
    subset = df.copy()
    if obra:
        subset = subset[subset["Obra"] == obra]
    if produto:
        subset = subset[subset["Produto"] == produto]
    return subset


def build_eap_lookup(df: pd.DataFrame) -> dict:
    """
    Constrói um dicionário de lookup para mapeamento rápido.
    Chave: (Obra, Item) -> dict com todas as infos da EAP.
    """
    lookup = {}
    for _, row in df.iterrows():
        key = (row["Obra"], row["Item"])
        if key not in lookup:
            lookup[key] = {
                "Obra": row["Obra"],
                "Produto": row["Produto"],
                "Item": row["Item"],
                "Servico": row["Servico"],
                "Insumo": row["Insumo"],
                "Descricao": row["Descricao"],
            }
    return lookup


def get_description_options(df: pd.DataFrame) -> list[str]:
    """
    Retorna lista de opções formatadas como 'Obra | Item | Descrição'
    para uso nos selects de mapeamento.
    """
    options = []
    seen = set()
    for _, row in df.iterrows():
        desc = row["Descricao"]
        if not desc:
            continue
        label = f"{row['Obra']} | {row['Item']} | {desc}"
        if label not in seen:
            options.append(label)
            seen.add(label)
    return sorted(options)


def get_mapping_options(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna DataFrame com opções únicas para mapeamento,
    agrupando por Obra + Item + Descrição (sem duplicatas de serviço/insumo).
    """
    cols = ["Obra", "Produto", "Item", "Descricao"]
    unique = df[cols].drop_duplicates().reset_index(drop=True)
    unique = unique[unique["Descricao"].str.len() > 0]
    unique["Label"] = unique.apply(
        lambda r: f"{r['Obra']} | {r['Produto']} | {r['Item']} | {r['Descricao']}", axis=1
    )
    return unique.sort_values("Label").reset_index(drop=True)
