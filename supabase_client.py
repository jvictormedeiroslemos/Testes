"""
Cliente Supabase para persistência mensal dos dados financeiros.

Tabelas necessárias no Supabase (execute no SQL Editor):

    CREATE TABLE monthly_data (
        month_key TEXT PRIMARY KEY,
        perfil JSONB DEFAULT '{}',
        receitas JSONB DEFAULT '[]',
        despesas JSONB DEFAULT '[]',
        dividas JSONB DEFAULT '[]',
        investimentos JSONB DEFAULT '[]',
        reserva_emergencia FLOAT DEFAULT 0,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE bank_statements (
        month_key TEXT PRIMARY KEY,
        bank TEXT DEFAULT 'C6',
        transactions JSONB DEFAULT '[]',
        raw_filename TEXT,
        total_gastos FLOAT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE monthly_analyses (
        month_key TEXT,
        agent_key TEXT,
        analysis TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (month_key, agent_key)
    );

    CREATE TABLE monthly_plans (
        month_key TEXT PRIMARY KEY,
        plan TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
"""

from datetime import datetime
from typing import Optional

import streamlit as st


def get_supabase():
    """Retorna cliente Supabase ou None se não configurado."""
    try:
        from supabase import create_client
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None


def list_months(supabase) -> list:
    """Lista meses disponíveis, do mais recente ao mais antigo."""
    try:
        res = (
            supabase.table("monthly_data")
            .select("month_key")
            .order("month_key", desc=True)
            .execute()
        )
        return [r["month_key"] for r in res.data]
    except Exception:
        return []


def load_monthly_data(supabase, month_key: str) -> dict:
    """Carrega dados financeiros fixos de um mês."""
    empty = {
        "perfil": {},
        "receitas": [],
        "despesas": [],
        "dividas": [],
        "investimentos": [],
        "reserva_emergencia": 0.0,
    }
    try:
        res = (
            supabase.table("monthly_data")
            .select("*")
            .eq("month_key", month_key)
            .execute()
        )
        if res.data:
            row = res.data[0]
            return {
                "perfil": row.get("perfil") or {},
                "receitas": row.get("receitas") or [],
                "despesas": row.get("despesas") or [],
                "dividas": row.get("dividas") or [],
                "investimentos": row.get("investimentos") or [],
                "reserva_emergencia": row.get("reserva_emergencia") or 0.0,
            }
    except Exception:
        pass
    return empty


def save_monthly_data(supabase, month_key: str, data: dict):
    """Salva dados financeiros fixos de um mês."""
    try:
        payload = {
            "month_key": month_key,
            "perfil": data.get("perfil", {}),
            "receitas": data.get("receitas", []),
            "despesas": data.get("despesas", []),
            "dividas": data.get("dividas", []),
            "investimentos": data.get("investimentos", []),
            "reserva_emergencia": data.get("reserva_emergencia", 0.0),
            "updated_at": datetime.now().isoformat(),
        }
        supabase.table("monthly_data").upsert(payload, on_conflict="month_key").execute()
    except Exception:
        pass


def load_statement(supabase, month_key: str) -> Optional[dict]:
    """Carrega extrato processado de um mês."""
    try:
        res = (
            supabase.table("bank_statements")
            .select("*")
            .eq("month_key", month_key)
            .execute()
        )
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return None


def save_statement(supabase, month_key: str, transactions: list, filename: str, bank: str = "C6"):
    """Salva extrato processado."""
    try:
        total = sum(abs(t["valor"]) for t in transactions if t["valor"] < 0)
        payload = {
            "month_key": month_key,
            "bank": bank,
            "transactions": transactions,
            "raw_filename": filename,
            "total_gastos": total,
            "created_at": datetime.now().isoformat(),
        }
        supabase.table("bank_statements").upsert(payload, on_conflict="month_key").execute()
    except Exception:
        pass


def load_analysis(supabase, month_key: str, agent_key: str) -> Optional[str]:
    """Carrega análise de um agente para um mês."""
    try:
        res = (
            supabase.table("monthly_analyses")
            .select("analysis")
            .eq("month_key", month_key)
            .eq("agent_key", agent_key)
            .execute()
        )
        if res.data:
            return res.data[0]["analysis"]
    except Exception:
        pass
    return None


def save_analysis(supabase, month_key: str, agent_key: str, analysis: str):
    """Salva análise de um agente."""
    try:
        payload = {
            "month_key": month_key,
            "agent_key": agent_key,
            "analysis": analysis,
            "created_at": datetime.now().isoformat(),
        }
        supabase.table("monthly_analyses").upsert(
            payload, on_conflict="month_key,agent_key"
        ).execute()
    except Exception:
        pass


def load_plan(supabase, month_key: str) -> Optional[str]:
    """Carrega plano integrado de um mês."""
    try:
        res = (
            supabase.table("monthly_plans")
            .select("plan")
            .eq("month_key", month_key)
            .execute()
        )
        if res.data:
            return res.data[0]["plan"]
    except Exception:
        pass
    return None


def save_plan(supabase, month_key: str, plan: str):
    """Salva plano integrado de um mês."""
    try:
        payload = {
            "month_key": month_key,
            "plan": plan,
            "created_at": datetime.now().isoformat(),
        }
        supabase.table("monthly_plans").upsert(payload, on_conflict="month_key").execute()
    except Exception:
        pass


def load_all_analyses(supabase, month_key: str) -> dict:
    """Carrega todas as análises de um mês de uma vez."""
    try:
        res = (
            supabase.table("monthly_analyses")
            .select("agent_key, analysis")
            .eq("month_key", month_key)
            .execute()
        )
        return {r["agent_key"]: r["analysis"] for r in res.data}
    except Exception:
        return {}
