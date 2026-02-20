"""
Master Agent Orquestrador.

Responsabilidade: Coordenar todos os agentes especialistas, sintetizar suas
análises e produzir um plano estratégico integrado e priorizado.
"""

from typing import Optional
import anthropic

from .base_agent import BaseAgent
from .diagnostico_agent import DiagnosticoAgent
from .orcamento_agent import OrcamentoAgent
from .dividas_agent import DividasAgent
from .investimentos_agent import InvestimentosAgent
from .rotina_agent import RotinaAgent


class MasterAgent(BaseAgent):
    AGENT_NAME = "Master Orquestrador"

    SYSTEM_PROMPT = """Você é o Master Agent Orquestrador de um sistema financeiro pessoal modular.

Você recebeu as análises de 5 agentes especialistas:
- Agente de Diagnóstico & Métricas
- Agente de Orçamento & Redução de Custos
- Agente de Dívidas & Renegociação
- Agente de Estratégia de Investimentos
- Agente de Rotina & Auditoria Financeira

Sua função é sintetizar todas essas análises e produzir:

1. **Resumo Executivo** (situação atual em 5 linhas)

2. **Prioridades Estratégicas** (top 5 ações mais impactantes, ordenadas por urgência e impacto)

3. **Plano Integrado de 12 Meses:**
   - Meses 1-3: Estabilização e corte de sangramentos
   - Meses 4-6: Construção de reserva e quitação prioritária
   - Meses 7-9: Aceleração e consolidação
   - Meses 10-12: Crescimento e revisão

4. **Conflitos e decisões-chave:**
   - Onde o usuário precisa fazer escolhas difíceis
   - Trade-offs importantes (ex: pagar dívida vs. investir)
   - Como o Master Agent recomenda resolver cada conflito

5. **Indicadores de sucesso:**
   - Como saber que o plano está funcionando
   - Marcos a celebrar no caminho

6. **Mensagem de motivação e compromisso** para o usuário

Seja estratégico, integrado e orientado a resultados concretos.
Sempre responda em português do Brasil."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.agents = {
            "diagnostico": DiagnosticoAgent(api_key),
            "orcamento": OrcamentoAgent(api_key),
            "dividas": DividasAgent(api_key),
            "investimentos": InvestimentosAgent(api_key),
            "rotina": RotinaAgent(api_key),
        }

    def run_agent(self, agent_key: str, financial_data: dict, question: Optional[str] = None) -> str:
        """Run a single specialist agent."""
        return self.agents[agent_key].analyze(financial_data, question)

    def run_all_agents(self, financial_data: dict) -> dict:
        """Run all specialist agents and return their analyses."""
        results = {}
        for key, agent in self.agents.items():
            results[key] = agent.analyze(financial_data)
        return results

    def orchestrate(self, financial_data: dict, agent_results: dict) -> str:
        """
        Synthesize all agent results into an integrated strategic plan.
        """
        synthesis_prompt = self._build_synthesis_prompt(financial_data, agent_results)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=3000,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": synthesis_prompt}],
        )
        return message.content[0].text

    def _build_synthesis_prompt(self, financial_data: dict, agent_results: dict) -> str:
        """Build the synthesis prompt from all agent analyses."""
        lines = ["## Análises dos Agentes Especialistas\n"]

        agent_labels = {
            "diagnostico": "Agente de Diagnóstico & Métricas",
            "orcamento": "Agente de Orçamento & Redução de Custos",
            "dividas": "Agente de Dívidas & Renegociação",
            "investimentos": "Agente de Estratégia de Investimentos",
            "rotina": "Agente de Rotina & Auditoria Financeira",
        }

        for key, result in agent_results.items():
            label = agent_labels.get(key, key)
            lines.append(f"### {label}\n")
            lines.append(result)
            lines.append("\n---\n")

        lines.append(
            "\nCom base em todas as análises acima, produza o Plano Estratégico Integrado."
        )

        return "\n".join(lines)
