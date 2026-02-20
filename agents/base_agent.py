"""
Base agent class for Sistema Financeiro Modular.
All specialist agents inherit from this.
"""

import anthropic
from typing import Optional


class BaseAgent:
    """Base class for all financial specialist agents."""

    AGENT_NAME = "Base Agent"
    SYSTEM_PROMPT = "You are a financial assistant."

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-6"

    def analyze(self, financial_data: dict, user_question: Optional[str] = None) -> str:
        """
        Run agent analysis on financial data.
        Returns markdown-formatted response.
        """
        user_content = self._build_user_message(financial_data, user_question)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return message.content[0].text

    def _build_user_message(self, financial_data: dict, user_question: Optional[str]) -> str:
        """Build the user message from financial data."""
        lines = ["## Dados Financeiros do Usuário\n"]

        if financial_data.get("perfil"):
            p = financial_data["perfil"]
            lines.append(f"**Nome:** {p.get('nome', 'Não informado')}")
            lines.append(f"**Renda Mensal Líquida:** R$ {p.get('renda_liquida', 0):,.2f}")
            lines.append(f"**Dependentes:** {p.get('dependentes', 0)}")
            lines.append(f"**Objetivo principal:** {p.get('objetivo', 'Não informado')}\n")

        if financial_data.get("receitas"):
            lines.append("### Receitas Mensais")
            for item in financial_data["receitas"]:
                lines.append(f"- {item['descricao']}: R$ {item['valor']:,.2f}")
            total_rec = sum(i["valor"] for i in financial_data["receitas"])
            lines.append(f"**Total Receitas:** R$ {total_rec:,.2f}\n")

        if financial_data.get("despesas"):
            lines.append("### Despesas Mensais")
            for item in financial_data["despesas"]:
                lines.append(f"- {item['categoria']} - {item['descricao']}: R$ {item['valor']:,.2f}")
            total_desp = sum(i["valor"] for i in financial_data["despesas"])
            lines.append(f"**Total Despesas:** R$ {total_desp:,.2f}\n")

        if financial_data.get("dividas"):
            lines.append("### Dívidas")
            for item in financial_data["dividas"]:
                lines.append(
                    f"- {item['descricao']}: R$ {item['saldo']:,.2f} | "
                    f"Juros: {item['juros_mensal']}% a.m. | "
                    f"Parcela: R$ {item['parcela']:,.2f}"
                )
            total_div = sum(i["saldo"] for i in financial_data["dividas"])
            lines.append(f"**Total Dívidas:** R$ {total_div:,.2f}\n")

        if financial_data.get("investimentos"):
            lines.append("### Investimentos")
            for item in financial_data["investimentos"]:
                lines.append(
                    f"- {item['tipo']}: R$ {item['valor']:,.2f} | "
                    f"Rentabilidade: {item.get('rentabilidade', 'N/A')}"
                )
            total_inv = sum(i["valor"] for i in financial_data["investimentos"])
            lines.append(f"**Total Investimentos:** R$ {total_inv:,.2f}\n")

        if financial_data.get("reserva_emergencia"):
            lines.append(f"**Reserva de Emergência:** R$ {financial_data['reserva_emergencia']:,.2f}\n")

        if user_question:
            lines.append(f"\n---\n**Pergunta específica do usuário:** {user_question}")

        return "\n".join(lines)
