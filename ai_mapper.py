"""
Módulo de sugestão inteligente DE-PARA usando IA.

Oferece duas abordagens:
1. Similaridade textual (offline, sem API) — difflib SequenceMatcher
2. Claude API (Anthropic) — análise semântica contextual
"""

import os
import re
import json
from difflib import SequenceMatcher
from unicodedata import normalize

import pandas as pd

# ---------------------------------------------------------------------------
# Utilidades de normalização de texto
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Remove acentos, converte para minúsculas e limpa pontuação."""
    if not text:
        return ""
    text = normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


# ---------------------------------------------------------------------------
# 1) Sugestão por similaridade textual (offline)
# ---------------------------------------------------------------------------

def suggest_by_similarity(
    description: str,
    eap_options: pd.DataFrame,
    top_n: int = 5,
    min_score: float = 0.25,
) -> list[dict]:
    """
    Compara a descrição do lançamento com todas as descrições da EAP
    usando SequenceMatcher + busca por tokens.

    Retorna lista de sugestões ordenadas por score (0-1).
    """
    desc_norm = _normalize_text(description)
    desc_tokens = set(desc_norm.split())

    results = []
    for _, row in eap_options.iterrows():
        eap_desc = str(row.get("Descricao", ""))
        eap_norm = _normalize_text(eap_desc)

        if not eap_norm:
            continue

        # Score 1: SequenceMatcher (subsequência comum)
        seq_score = SequenceMatcher(None, desc_norm, eap_norm).ratio()

        # Score 2: Tokens em comum (Jaccard-like)
        eap_tokens = set(eap_norm.split())
        common = desc_tokens & eap_tokens
        if desc_tokens or eap_tokens:
            token_score = len(common) / max(len(desc_tokens | eap_tokens), 1)
        else:
            token_score = 0.0

        # Score 3: Substring match bonus
        substring_bonus = 0.0
        if desc_norm in eap_norm or eap_norm in desc_norm:
            substring_bonus = 0.3

        # Score 4: Cada token do input que aparece no EAP (recall)
        if desc_tokens:
            recall_score = len(common) / len(desc_tokens)
        else:
            recall_score = 0.0

        # Score 5: Tokens significativos (ignora palavras curtas/comuns)
        stopwords = {"de", "do", "da", "dos", "das", "em", "com", "para", "por", "e", "a", "o", "no", "na"}
        sig_desc = desc_tokens - stopwords
        sig_eap = eap_tokens - stopwords
        sig_common = sig_desc & sig_eap
        if sig_desc:
            sig_score = len(sig_common) / len(sig_desc)
        else:
            sig_score = 0.0

        # Score combinado
        combined = (
            seq_score * 0.25
            + token_score * 0.15
            + substring_bonus * 0.1
            + recall_score * 0.2
            + sig_score * 0.3
        )
        combined = min(combined, 1.0)

        if combined >= min_score:
            results.append({
                "Label": row.get("Label", ""),
                "Obra": row.get("Obra", ""),
                "Produto": row.get("Produto", ""),
                "Item": row.get("Item", ""),
                "Descricao_EAP": eap_desc,
                "Score": round(combined, 3),
            })

    results.sort(key=lambda x: x["Score"], reverse=True)
    return results[:top_n]


def suggest_batch_by_similarity(
    descriptions: list[str],
    eap_options: pd.DataFrame,
    top_n: int = 3,
) -> dict[str, list[dict]]:
    """Aplica sugestão por similaridade a uma lista de descrições."""
    return {
        desc: suggest_by_similarity(desc, eap_options, top_n=top_n)
        for desc in descriptions
    }


# ---------------------------------------------------------------------------
# 2) Sugestão via Claude API (Anthropic)
# ---------------------------------------------------------------------------

def _build_eap_context(eap_options: pd.DataFrame, max_items: int = 300) -> str:
    """Monta o texto de contexto da EAP para enviar ao Claude."""
    lines = ["ESTRUTURA EAP (Plano de Contas) - Opções disponíveis:"]
    lines.append("Formato: Obra | Produto | Item | Descrição")
    lines.append("-" * 60)

    for i, (_, row) in enumerate(eap_options.iterrows()):
        if i >= max_items:
            lines.append(f"... (mais {len(eap_options) - max_items} itens omitidos)")
            break
        lines.append(f"{row['Obra']} | {row['Produto']} | {row['Item']} | {row['Descricao']}")

    return "\n".join(lines)


def suggest_by_ai(
    descriptions: list[str],
    eap_options: pd.DataFrame,
    api_key: str = None,
    model: str = "claude-sonnet-4-5-20250929",
) -> dict[str, list[dict]]:
    """
    Usa a API do Claude para analisar lançamentos e sugerir mapeamentos.

    Retorna dict: { descrição_original: [ {Label, Obra, Item, Descricao_EAP, Score, Justificativa} ] }
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ImportError("Instale o SDK: pip install anthropic")

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("API key não configurada. Defina ANTHROPIC_API_KEY ou passe via parâmetro.")

    client = Anthropic(api_key=api_key)

    eap_context = _build_eap_context(eap_options)

    # Montar lista de lançamentos
    items_text = "\n".join(
        f"{i + 1}. \"{desc}\"" for i, desc in enumerate(descriptions)
    )

    prompt = f"""Você é um especialista em contabilidade e gestão de empreendimentos imobiliários.

Abaixo está a estrutura de EAP (Estrutura Analítica de Processos / Plano de Contas) de uma empresa:

{eap_context}

---

Preciso que você analise os seguintes lançamentos financeiros (despesas/receitas) e sugira para qual item da EAP cada um deve ser apropriado.

LANÇAMENTOS:
{items_text}

---

Para cada lançamento, sugira até 3 opções da EAP, ordenadas da mais provável para a menos provável.

Responda EXCLUSIVAMENTE no formato JSON abaixo (sem markdown, sem texto adicional):
{{
  "mapeamentos": [
    {{
      "descricao_original": "texto do lançamento",
      "sugestoes": [
        {{
          "obra": "SIGLA",
          "produto": "código produto",
          "item": "código item",
          "descricao_eap": "descrição do item EAP",
          "confianca": 0.95,
          "justificativa": "breve explicação"
        }}
      ]
    }}
  ]
}}"""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parsear resposta
    response_text = response.content[0].text.strip()

    # Tentar extrair JSON da resposta
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Tentar encontrar JSON dentro do texto
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            data = json.loads(json_match.group())
        else:
            return {"_error": response_text}

    # Converter para formato padronizado
    result = {}
    for item in data.get("mapeamentos", []):
        desc = item["descricao_original"]
        suggestions = []
        for sug in item.get("sugestoes", []):
            label = f"{sug['obra']} | {sug['produto']} | {sug['item']} | {sug['descricao_eap']}"
            suggestions.append({
                "Label": label,
                "Obra": sug["obra"],
                "Produto": sug.get("produto", ""),
                "Item": sug["item"],
                "Descricao_EAP": sug["descricao_eap"],
                "Score": sug.get("confianca", 0.5),
                "Justificativa": sug.get("justificativa", ""),
            })
        result[desc] = suggestions

    return result
