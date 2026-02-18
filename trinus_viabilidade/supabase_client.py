"""
Trinus Viabilidade — Cliente Supabase.

CRUD para persistência de estudos e funções de retroalimentação
(RAG + estatísticas agregadas) que enriquecem a IA.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

from modelos import DatasMacro, InputsUsuario, ResultadoPremissas


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

def get_client(url: str, key: str):
    """Retorna instância do Supabase client. Levanta ImportError se SDK ausente."""
    from supabase import create_client
    return create_client(url, key)


# ---------------------------------------------------------------------------
# CRUD — Salvar estudo completo
# ---------------------------------------------------------------------------

def salvar_estudo(
    client,
    resultado: ResultadoPremissas,
    ia_metadata: Optional[dict] = None,
    premissas_editadas: Optional[dict] = None,
    datas_macro: Optional[DatasMacro] = None,
    sim=None,
    status: str = "gerado",
) -> str:
    """
    Salva ou atualiza um estudo completo no Supabase.

    Returns:
        estudo_id (str) — UUID do estudo criado/atualizado.
    """
    inputs = resultado.inputs
    editadas = premissas_editadas or {}

    # --- 1. Inserir/atualizar estudo principal ---
    estudo_data = {
        "tipologia": inputs.tipologia.value,
        "padrao": inputs.padrao.value,
        "estado": inputs.estado,
        "cidade": inputs.cidade,
        "regiao": inputs.regiao.value if hasattr(inputs.regiao, "value") else str(inputs.regiao),
        "num_unidades": inputs.num_unidades,
        "tipo_negociacao": inputs.tipo_negociacao.value if inputs.tipo_negociacao else None,
        "area_terreno_m2": inputs.area_terreno_m2,
        "area_privativa_media_m2": inputs.area_privativa_media_m2,
        "vgv_estimado": inputs.vgv_estimado,
        "permuta_percentual": getattr(inputs, "permuta_percentual", None),
        "permuta_referencia": getattr(inputs, "permuta_referencia", None),
        "valor_aquisicao": getattr(inputs, "valor_aquisicao", None),
        "status": status,
    }

    resp = client.table("estudos").insert(estudo_data).execute()
    estudo_id = resp.data[0]["id"]

    # --- 2. Salvar premissas ---
    premissas_rows = []
    for p in resultado.premissas:
        valor_final = editadas.get(p.nome, p.valor)
        # Detectar se IA ajustou (fonte começa com "IA:")
        valor_ia = p.valor if p.fonte.startswith("IA:") else None
        premissas_rows.append({
            "estudo_id": estudo_id,
            "nome": p.nome,
            "valor_original": p.valor if valor_ia is None else p.valor_min,  # benchmark original
            "valor_ia": valor_ia,
            "valor_final": float(valor_final),
            "unidade": p.unidade,
            "categoria": p.categoria,
            "subcategoria": p.subcategoria,
            "fonte": p.fonte,
        })

    if premissas_rows:
        client.table("premissas_registro").insert(premissas_rows).execute()

    # --- 3. Salvar cronograma ---
    if datas_macro:
        crono_data = {
            "estudo_id": estudo_id,
            "inicio_projeto": datas_macro.inicio_projeto.isoformat(),
            "lancamento": datas_macro.lancamento.isoformat() if datas_macro.lancamento else None,
            "inicio_obra": datas_macro.inicio_obra.isoformat() if datas_macro.inicio_obra else None,
            "fim_obra": datas_macro.fim_obra.isoformat() if datas_macro.fim_obra else None,
            "inicio_vendas_pos": datas_macro.inicio_vendas_pos.isoformat() if datas_macro.inicio_vendas_pos else None,
        }
        client.table("cronograma_registro").insert(crono_data).execute()

    # --- 4. Salvar feedback IA ---
    if ia_metadata and "erro" not in ia_metadata:
        ia_data = {
            "estudo_id": estudo_id,
            "insights": json.dumps(ia_metadata.get("insights", []), ensure_ascii=False),
            "recomendacoes": json.dumps(ia_metadata.get("recomendacoes", []), ensure_ascii=False),
            "cronograma_justificativas": json.dumps(ia_metadata.get("cronograma", {}), ensure_ascii=False),
            "ajustes_aplicados": ia_metadata.get("ajustes_aplicados", 0),
            "modelo": ia_metadata.get("modelo", ""),
        }
        client.table("ia_feedback").insert(ia_data).execute()

    # --- 5. Salvar simulação ---
    if sim and getattr(sim, "vgv", 0) > 0:
        sim_data = {
            "estudo_id": estudo_id,
            "vgv": sim.vgv,
            "receita_liquida": sim.receita_liquida,
            "custo_total": sim.custo_total,
            "despesa_total": sim.despesa_total,
            "resultado_projeto": sim.resultado_projeto,
            "margem_vgv": sim.margem_vgv,
            "margem_custo": sim.margem_custo,
            "tir_mensal": sim.tir_mensal,
            "tir_anual": sim.tir_anual,
            "vpl": sim.vpl,
            "payback_meses": sim.payback_meses,
            "exposicao_maxima": sim.exposicao_maxima,
            "lucro_sobre_investimento": sim.lucro_sobre_investimento,
        }
        client.table("simulacao_resultado").insert(sim_data).execute()

    return estudo_id


def atualizar_status(client, estudo_id: str, status: str):
    """Atualiza o status de um estudo existente."""
    client.table("estudos").update({"status": status}).eq("id", estudo_id).execute()


def salvar_simulacao(client, estudo_id: str, sim):
    """Salva/atualiza resultado de simulação para um estudo."""
    sim_data = {
        "estudo_id": estudo_id,
        "vgv": sim.vgv,
        "receita_liquida": sim.receita_liquida,
        "custo_total": sim.custo_total,
        "despesa_total": sim.despesa_total,
        "resultado_projeto": sim.resultado_projeto,
        "margem_vgv": sim.margem_vgv,
        "margem_custo": sim.margem_custo,
        "tir_mensal": sim.tir_mensal,
        "tir_anual": sim.tir_anual,
        "vpl": sim.vpl,
        "payback_meses": sim.payback_meses,
        "exposicao_maxima": sim.exposicao_maxima,
        "lucro_sobre_investimento": sim.lucro_sobre_investimento,
    }
    # Upsert: se já existir para este estudo, atualiza
    client.table("simulacao_resultado").upsert(
        sim_data, on_conflict="estudo_id"
    ).execute()


# ---------------------------------------------------------------------------
# RETROALIMENTAÇÃO — Buscar casos similares (RAG)
# ---------------------------------------------------------------------------

def buscar_casos_similares(
    client,
    cidade: str,
    estado: str,
    tipologia: str,
    padrao: str = "",
    limite: int = 5,
) -> list[dict]:
    """
    Busca estudos finalizados similares para contexto RAG.

    Prioridade: mesma cidade > mesmo estado > mesma tipologia.
    Retorna lista de dicts com inputs + premissas + indicadores.
    """
    # Buscar por cidade + tipologia (mais relevante)
    query = (
        client.table("estudos")
        .select(
            "id, tipologia, padrao, cidade, estado, num_unidades, vgv_estimado, "
            "created_at"
        )
        .in_("status", ["simulado", "exportado"])
        .eq("cidade", cidade)
        .eq("tipologia", tipologia)
        .order("created_at", desc=True)
        .limit(limite)
    )
    resp = query.execute()
    resultados = resp.data or []

    # Se poucos resultados, ampliar para estado + tipologia
    if len(resultados) < limite:
        faltam = limite - len(resultados)
        ids_existentes = [r["id"] for r in resultados]
        query2 = (
            client.table("estudos")
            .select(
                "id, tipologia, padrao, cidade, estado, num_unidades, vgv_estimado, "
                "created_at"
            )
            .in_("status", ["simulado", "exportado"])
            .eq("estado", estado)
            .eq("tipologia", tipologia)
            .neq("cidade", cidade)
            .order("created_at", desc=True)
            .limit(faltam)
        )
        resp2 = query2.execute()
        resultados.extend(resp2.data or [])

    if not resultados:
        return []

    # Enriquecer com premissas e indicadores
    casos = []
    for est in resultados:
        eid = est["id"]

        # Premissas finais
        resp_p = (
            client.table("premissas_registro")
            .select("nome, valor_final, unidade, categoria")
            .eq("estudo_id", eid)
            .execute()
        )
        premissas = {r["nome"]: r["valor_final"] for r in (resp_p.data or [])}

        # Indicadores da simulação
        resp_s = (
            client.table("simulacao_resultado")
            .select("margem_vgv, tir_anual, vpl, payback_meses, exposicao_maxima")
            .eq("estudo_id", eid)
            .limit(1)
            .execute()
        )
        indicadores = resp_s.data[0] if resp_s.data else {}

        casos.append({
            "cidade": est["cidade"],
            "estado": est["estado"],
            "tipologia": est["tipologia"],
            "padrao": est["padrao"],
            "num_unidades": est["num_unidades"],
            "vgv_estimado": est["vgv_estimado"],
            "premissas": premissas,
            "indicadores": indicadores,
        })

    return casos


# ---------------------------------------------------------------------------
# RETROALIMENTAÇÃO — Estatísticas agregadas
# ---------------------------------------------------------------------------

def buscar_estatisticas(
    client,
    cidade: str,
    estado: str,
    tipologia: str,
) -> list[dict]:
    """
    Busca estatísticas agregadas de premissas para uma cidade/tipologia.

    Usa a view vw_estatisticas_premissas do Supabase.
    Retorna lista de dicts com nome, media, mediana, total_estudos, etc.
    """
    # Tentar por cidade + tipologia
    resp = (
        client.table("vw_estatisticas_premissas")
        .select("*")
        .eq("cidade", cidade)
        .eq("tipologia", tipologia)
        .execute()
    )
    stats = resp.data or []

    # Se vazio, ampliar para estado + tipologia
    if not stats:
        resp = (
            client.table("vw_estatisticas_premissas")
            .select("*")
            .eq("estado", estado)
            .eq("tipologia", tipologia)
            .execute()
        )
        stats = resp.data or []

    return stats


def formatar_contexto_rag(casos: list[dict], stats: list[dict]) -> str:
    """
    Formata casos similares e estatísticas em texto para injeção no prompt da IA.
    """
    partes = []

    if casos:
        partes.append("DADOS HISTÓRICOS DE EMPREENDIMENTOS SIMILARES:")
        partes.append(f"(Base: {len(casos)} estudos anteriores finalizados)")
        partes.append("")
        for i, caso in enumerate(casos, 1):
            partes.append(f"--- Estudo #{i}: {caso['tipologia']} / {caso['padrao']} "
                          f"em {caso['cidade']}/{caso['estado']} "
                          f"({caso['num_unidades']} un.) ---")

            # Premissas principais
            premissas_chave = [
                "Preço médio por m²", "Custo de construção por m²",
                "Velocidade de vendas", "Prazo de obra estimado",
                "Comissão de corretagem", "Taxa Mínima de Atratividade (TMA)",
                "Custo do terreno (% VGV)",
            ]
            for nome in premissas_chave:
                if nome in caso["premissas"]:
                    partes.append(f"  {nome}: {caso['premissas'][nome]}")

            # Indicadores
            ind = caso.get("indicadores", {})
            if ind:
                partes.append(f"  → Margem VGV: {ind.get('margem_vgv', 'N/A')}% | "
                              f"TIR Anual: {ind.get('tir_anual', 'N/A')}% | "
                              f"Payback: {ind.get('payback_meses', 'N/A')} meses")
            partes.append("")

    if stats:
        partes.append("ESTATÍSTICAS AGREGADAS DO MERCADO LOCAL:")
        partes.append(f"(Base: premissas de estudos finalizados)")
        partes.append("")
        for s in stats:
            if s.get("total_estudos", 0) >= 2:
                partes.append(
                    f"  {s['premissa_nome']} ({s['unidade']}): "
                    f"média={s['media']:.2f}, mediana={s['mediana']:.2f}, "
                    f"min={s['minimo']:.2f}, max={s['maximo']:.2f} "
                    f"(n={s['total_estudos']})"
                )
        partes.append("")

    return "\n".join(partes)
