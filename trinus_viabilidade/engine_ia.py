"""
Trinus Viabilidade - Motor de IA para sugestão de premissas.

Utiliza a API Anthropic (Claude) para refinar e enriquecer as premissas
geradas pelo motor estático, com base no conhecimento do mercado
imobiliário local.
"""

from __future__ import annotations

import json

from modelos import InputsUsuario, ResultadoPremissas


SYSTEM_PROMPT = """Você é um especialista sênior em viabilidade imobiliária no Brasil, \
com profundo conhecimento do mercado imobiliário brasileiro, incluindo \
preços por região, custos de construção, velocidade de vendas, \
estrutura de financiamento (produção, CRI), despesas operacionais \
e demais indicadores relevantes para o fluxo de caixa (DFC) de SPEs imobiliárias.

Seu papel é analisar os dados de um empreendimento imobiliário e ajustar \
as premissas de mercado sugeridas pelo sistema, levando em conta:
1. Características específicas da cidade e região informadas
2. Condições atuais do mercado imobiliário local
3. Tendências recentes do setor
4. Particularidades da tipologia e padrão do empreendimento
5. Estrutura típica do DFC para o tipo de empreendimento (Incorporação vs Urbanismo)
6. Premissas de inadimplência diferenciadas por tipologia (loteamentos abertos: 25-30%, \
   condomínios fechados: 10-15%, incorporação vertical: 5-12%)
7. Premissas de CRI (CDI + 4-6% ou IPCA + 13-15%) quando aplicável
8. Custos de projetos, aprovações, BDI de obra e despesas pré-operacionais

Você DEVE retornar EXCLUSIVAMENTE um JSON válido com a seguinte estrutura:
{
    "premissas_ajustadas": {
        "nome_exato_da_premissa": {
            "valor": <valor_numerico_ajustado>,
            "justificativa": "Breve explicação do ajuste"
        }
    },
    "insights": [
        "Insight 1 sobre o mercado local",
        "Insight 2 sobre oportunidades ou riscos"
    ],
    "recomendacoes": [
        "Recomendação 1 para o empreendimento",
        "Recomendação 2"
    ]
}

REGRAS IMPORTANTES:
- Use EXATAMENTE os mesmos nomes de premissa fornecidos (copie e cole)
- Ajuste APENAS premissas que você tem confiança para melhorar
- Mantenha os valores dentro das faixas mín-máx fornecidas
- Forneça justificativas claras baseadas em dados de mercado
- Se não tiver informação suficiente sobre a cidade, mantenha os valores originais
- Forneça 2-4 insights relevantes e acionáveis
- Forneça 2-3 recomendações estratégicas
- Considere as premissas expandidas: coordenação comercial, premiação, \
  taxa de gestão, seguros, despesas pré-operacionais, CRI, BDI, \
  custo de projetos e aprovações, IPTU do terreno, curva de vendas por fase
- Responda SEMPRE em português brasileiro
- NÃO inclua texto fora do JSON
"""


def _build_user_prompt(
    inputs: InputsUsuario,
    resultado: ResultadoPremissas,
) -> str:
    """Constrói o prompt do usuário com os dados do empreendimento."""
    premissas_text = ""
    for p in resultado.premissas:
        premissas_text += (
            f"  - {p.nome}: {p.valor} {p.unidade} "
            f"(mín: {p.valor_min}, máx: {p.valor_max}) "
            f"[{p.categoria}/{p.subcategoria}]\n"
        )

    negociacao_detalhes = f"Tipo: {inputs.tipo_negociacao.value}"
    if inputs.permuta_percentual is not None:
        negociacao_detalhes += f", Percentual: {inputs.permuta_percentual}%"
    if inputs.permuta_referencia:
        negociacao_detalhes += f", Referência: {inputs.permuta_referencia}"
    if inputs.valor_aquisicao is not None:
        negociacao_detalhes += f", Valor: R$ {inputs.valor_aquisicao:,.2f}"

    prompt = f"""Analise o seguinte empreendimento imobiliário e ajuste as premissas:

DADOS DO EMPREENDIMENTO:
- Tipologia: {inputs.tipologia.value}
- Padrão: {inputs.padrao.value}
- Estado: {inputs.estado}
- Cidade: {inputs.cidade}
- Região: {inputs.regiao.value}
- Número de unidades: {inputs.num_unidades}
- Negociação do terreno: {negociacao_detalhes}
- Área do terreno: {inputs.area_terreno_m2 or 'Não informado'} m²
- VGV estimado: {f'R$ {inputs.vgv_estimado:,.2f}' if inputs.vgv_estimado else 'Calculado pelo sistema'}
- Área privativa média: {inputs.area_privativa_media_m2 or 'Estimada pelo sistema'} m²

PREMISSAS ATUAIS (baseadas em benchmarks estáticos de mercado):
{premissas_text}

Analise estas premissas considerando o mercado imobiliário de \
{inputs.cidade}/{inputs.estado} e ajuste os valores conforme seu \
conhecimento especializado. Retorne o JSON conforme especificado."""
    return prompt


def gerar_premissas_com_ia(
    inputs: InputsUsuario,
    resultado_base: ResultadoPremissas,
    api_key: str,
) -> tuple[ResultadoPremissas, dict]:
    """
    Enriquece premissas usando IA (Anthropic Claude API).

    Returns:
        Tupla (resultado_ajustado, ia_metadata) com insights e recomendações.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return resultado_base, {
            "erro": "Pacote 'anthropic' não instalado. Adicione anthropic ao requirements.txt.",
        }

    client = Anthropic(api_key=api_key)
    user_prompt = _build_user_prompt(inputs, resultado_base)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        resultado_ia = json.loads(response.content[0].text)

        ajustes = resultado_ia.get("premissas_ajustadas", {})
        ajustes_aplicados = 0

        for p in resultado_base.premissas:
            if p.nome in ajustes and p.editavel:
                ajuste = ajustes[p.nome]
                novo_valor = ajuste.get("valor", p.valor)
                if isinstance(novo_valor, (int, float)):
                    if p.valor_min <= novo_valor <= p.valor_max:
                        p.valor = float(novo_valor)
                        justificativa = ajuste.get("justificativa", "")
                        if justificativa:
                            p.fonte = f"IA: {justificativa}"
                        ajustes_aplicados += 1

        ia_metadata = {
            "insights": resultado_ia.get("insights", []),
            "recomendacoes": resultado_ia.get("recomendacoes", []),
            "modelo": "claude-sonnet-4-5-20250929",
            "ajustes_aplicados": ajustes_aplicados,
        }

        return resultado_base, ia_metadata

    except Exception as e:
        return resultado_base, {"erro": str(e)}
