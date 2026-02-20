"""
Sistema Financeiro Modular com Agentes Especialistas.

Uso:
    streamlit run finance_app.py
"""

import hashlib
import hmac
import json
import time
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Sistema Financeiro | Agentes IA",
    page_icon="💰",
    layout="wide",
)

DATA_FILE = Path("data/financial_data.json")
try:
    DATA_FILE.parent.mkdir(exist_ok=True)
except Exception:
    DATA_FILE = None  # Streamlit Cloud: usar apenas session_state

# Lê API key dos secrets do Streamlit Cloud (se configurado)
_secret_api_key = ""
try:
    _secret_api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
except Exception:
    pass

AGENT_LABELS = {
    "diagnostico": ("🩺", "Diagnóstico & Métricas"),
    "orcamento": ("📊", "Orçamento & Redução de Custos"),
    "dividas": ("💳", "Dívidas & Renegociação"),
    "investimentos": ("📈", "Estratégia de Investimentos"),
    "rotina": ("📅", "Rotina & Auditoria"),
}


# ---------------------------------------------------------------------------
# Persistência de dados
# ---------------------------------------------------------------------------
def load_data() -> dict:
    if DATA_FILE and DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "perfil": {},
        "receitas": [],
        "despesas": [],
        "dividas": [],
        "investimentos": [],
        "reserva_emergencia": 0.0,
    }


def save_data(data: dict):
    if DATA_FILE:
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # No Streamlit Cloud os dados ficam apenas na sessão


# ---------------------------------------------------------------------------
# Autenticação e Segurança
# ---------------------------------------------------------------------------
_MAX_TENTATIVAS = 5
_TEMPO_BLOQUEIO = 300  # 5 minutos em segundos


def _get_hash_senha() -> str:
    """Obtém o hash SHA-256 da senha configurada nos secrets do Streamlit."""
    try:
        return st.secrets.get("PASSWORD_HASH", "")
    except Exception:
        return ""


def verificar_autenticacao() -> bool:
    """
    Exibe tela de login e verifica autenticação.
    Retorna True se o usuário já está autenticado.
    Interrompe o app (st.stop) caso não esteja.
    """
    if st.session_state.get("autenticado", False):
        return True

    hash_senha = _get_hash_senha()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 Acesso Restrito")
        st.markdown(
            "Este sistema contém **dados financeiros pessoais e sigilosos**. "
            "Apenas usuários autorizados podem acessar."
        )
        st.markdown("---")

        if not hash_senha:
            st.error("⚠️ Configuração de segurança ausente.")
            st.info(
                "Configure `PASSWORD_HASH` nos secrets do Streamlit.  \n"
                "Execute o script abaixo para gerar o hash da sua senha:  \n"
                "```\npython generate_password_hash.py\n```"
            )
            st.stop()

        tentativas = st.session_state.get("tentativas_falhas", 0)
        bloqueado_ate = st.session_state.get("bloqueado_ate", 0.0)

        if time.time() < bloqueado_ate:
            restante = int(bloqueado_ate - time.time())
            minutos, segundos = divmod(restante, 60)
            st.error(
                f"🔒 Acesso bloqueado por excesso de tentativas.  \n"
                f"Aguarde **{minutos}m {segundos:02d}s** para tentar novamente."
            )
            st.stop()

        if bloqueado_ate > 0 and time.time() >= bloqueado_ate:
            st.session_state["tentativas_falhas"] = 0
            st.session_state["bloqueado_ate"] = 0.0
            tentativas = 0

        with st.form("form_login"):
            senha = st.text_input("🔑 Senha:", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            hash_digitado = hashlib.sha256(senha.encode()).hexdigest()
            if hmac.compare_digest(hash_digitado, hash_senha):
                st.session_state["autenticado"] = True
                st.session_state["tentativas_falhas"] = 0
                st.session_state["bloqueado_ate"] = 0.0
                st.rerun()
            else:
                novas_tentativas = tentativas + 1
                st.session_state["tentativas_falhas"] = novas_tentativas
                if novas_tentativas >= _MAX_TENTATIVAS:
                    st.session_state["bloqueado_ate"] = time.time() + _TEMPO_BLOQUEIO
                    st.error(
                        f"🔒 Muitas tentativas incorretas. "
                        f"Acesso bloqueado por {_TEMPO_BLOQUEIO // 60} minutos."
                    )
                else:
                    restantes = _MAX_TENTATIVAS - novas_tentativas
                    st.error(
                        f"❌ Senha incorreta. {restantes} tentativa(s) restante(s)."
                    )

    return False


# ---------------------------------------------------------------------------
# Verificação de autenticação — bloqueia o app se não autenticado
# ---------------------------------------------------------------------------
if not verificar_autenticacao():
    st.stop()


# ---------------------------------------------------------------------------
# Inicialização do session state
# ---------------------------------------------------------------------------
if "financial_data" not in st.session_state:
    st.session_state["financial_data"] = load_data()

if "agent_results" not in st.session_state:
    st.session_state["agent_results"] = {}

if "master_result" not in st.session_state:
    st.session_state["master_result"] = None


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("💰 Sistema Financeiro Modular")
st.markdown(
    "**Agentes Especialistas de IA** trabalhando para organizar sua vida financeira "
    "e construir sua liberdade financeira."
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Sidebar: API Key e navegação
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuração")

    if st.button("🚪 Sair", use_container_width=True, type="secondary"):
        st.session_state["autenticado"] = False
        st.rerun()

    st.markdown("---")

    if _secret_api_key:
        api_key = _secret_api_key
        st.success("🔑 API Key carregada dos secrets")
    else:
        api_key = st.text_input(
            "Anthropic API Key:",
            type="password",
            help="Obtenha em console.anthropic.com",
        )

    st.markdown("---")
    st.markdown("### 🤖 Agentes do Sistema")
    for key, (emoji, label) in AGENT_LABELS.items():
        status = "✅" if key in st.session_state["agent_results"] else "⬜"
        st.markdown(f"{status} {emoji} {label}")

    master_status = "✅" if st.session_state["master_result"] else "⬜"
    st.markdown(f"{master_status} 🎯 Master Orquestrador")

    st.markdown("---")

    data = st.session_state["financial_data"]
    total_rec = sum(i["valor"] for i in data.get("receitas", []))
    total_desp = sum(i["valor"] for i in data.get("despesas", []))
    total_div = sum(i["saldo"] for i in data.get("dividas", []))
    total_inv = sum(i["valor"] for i in data.get("investimentos", []))
    reserva = data.get("reserva_emergencia", 0.0)

    st.markdown("### 📊 Resumo dos Dados")
    st.metric("Receitas/mês", f"R$ {total_rec:,.0f}")
    st.metric("Despesas/mês", f"R$ {total_desp:,.0f}")
    st.metric("Saldo Mensal", f"R$ {total_rec - total_desp:,.0f}")
    st.metric("Total Dívidas", f"R$ {total_div:,.0f}")
    st.metric("Investimentos", f"R$ {total_inv:,.0f}")
    st.metric("Reserva", f"R$ {reserva:,.0f}")


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_dados, tab_agentes, tab_master, tab_chat = st.tabs(
    ["📝 Meus Dados", "🤖 Agentes Especialistas", "🎯 Plano Integrado", "💬 Chat Financeiro"]
)


# ============================================================
# TAB 1: DADOS FINANCEIROS
# ============================================================
with tab_dados:
    st.subheader("📝 Cadastro dos Dados Financeiros")
    st.markdown("Preencha seus dados para que os agentes possam analisá-los.")

    data = st.session_state["financial_data"]

    # ---- Perfil ----
    with st.expander("👤 Perfil Pessoal", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Seu nome:", value=data["perfil"].get("nome", ""))
            renda_liquida = st.number_input(
                "Renda líquida mensal (R$):",
                value=float(data["perfil"].get("renda_liquida", 0)),
                min_value=0.0,
                step=100.0,
            )
        with col2:
            dependentes = st.number_input(
                "Número de dependentes:",
                value=int(data["perfil"].get("dependentes", 0)),
                min_value=0,
                step=1,
            )
            objetivo = st.text_area(
                "Objetivo financeiro principal:",
                value=data["perfil"].get("objetivo", ""),
                placeholder="Ex: Eliminar dívidas em 2 anos e construir reserva de emergência",
                height=80,
            )

        reserva = st.number_input(
            "Reserva de emergência atual (R$):",
            value=float(data.get("reserva_emergencia", 0)),
            min_value=0.0,
            step=100.0,
        )

        if st.button("Salvar Perfil", key="btn_save_perfil"):
            data["perfil"] = {
                "nome": nome,
                "renda_liquida": renda_liquida,
                "dependentes": dependentes,
                "objetivo": objetivo,
            }
            data["reserva_emergencia"] = reserva
            save_data(data)
            st.session_state["financial_data"] = data
            st.success("Perfil salvo!")

    # ---- Receitas ----
    with st.expander("💵 Receitas Mensais", expanded=False):
        st.markdown("Adicione suas fontes de receita mensal.")

        rec_desc = st.text_input("Descrição:", key="rec_desc", placeholder="Ex: Salário CLT")
        rec_valor = st.number_input("Valor (R$):", key="rec_valor", min_value=0.0, step=50.0)

        if st.button("Adicionar Receita", key="btn_add_rec"):
            if rec_desc and rec_valor > 0:
                data["receitas"].append({"descricao": rec_desc, "valor": rec_valor})
                save_data(data)
                st.session_state["financial_data"] = data
                st.success(f"Receita '{rec_desc}' adicionada!")
                st.rerun()

        if data["receitas"]:
            st.markdown("**Receitas cadastradas:**")
            for i, item in enumerate(data["receitas"]):
                col_a, col_b = st.columns([4, 1])
                col_a.markdown(f"- {item['descricao']}: **R$ {item['valor']:,.2f}**")
                if col_b.button("❌", key=f"del_rec_{i}"):
                    data["receitas"].pop(i)
                    save_data(data)
                    st.session_state["financial_data"] = data
                    st.rerun()
            total = sum(i["valor"] for i in data["receitas"])
            st.markdown(f"**Total: R$ {total:,.2f}**")

    # ---- Despesas ----
    with st.expander("💸 Despesas Mensais", expanded=False):
        st.markdown("Cadastre suas despesas mensais por categoria.")

        categorias = [
            "Moradia (aluguel/financiamento)",
            "Alimentação",
            "Transporte",
            "Saúde",
            "Educação",
            "Lazer / Entretenimento",
            "Vestuário",
            "Comunicação (internet/celular)",
            "Assinaturas / Streaming",
            "Pessoal / Beleza",
            "Outros",
        ]

        col1, col2, col3 = st.columns(3)
        with col1:
            desp_cat = st.selectbox("Categoria:", categorias, key="desp_cat")
        with col2:
            desp_desc = st.text_input("Descrição:", key="desp_desc", placeholder="Ex: Aluguel do apartamento")
        with col3:
            desp_valor = st.number_input("Valor (R$):", key="desp_valor", min_value=0.0, step=10.0)

        if st.button("Adicionar Despesa", key="btn_add_desp"):
            if desp_desc and desp_valor > 0:
                data["despesas"].append({
                    "categoria": desp_cat,
                    "descricao": desp_desc,
                    "valor": desp_valor,
                })
                save_data(data)
                st.session_state["financial_data"] = data
                st.success(f"Despesa '{desp_desc}' adicionada!")
                st.rerun()

        if data["despesas"]:
            st.markdown("**Despesas cadastradas:**")
            # Agrupar por categoria
            by_cat = {}
            for item in data["despesas"]:
                cat = item["categoria"]
                by_cat.setdefault(cat, []).append(item)

            for cat, items in by_cat.items():
                total_cat = sum(i["valor"] for i in items)
                st.markdown(f"**{cat}** — R$ {total_cat:,.2f}")
                for i, item in enumerate(data["despesas"]):
                    if item["categoria"] == cat:
                        idx = data["despesas"].index(item)
                        col_a, col_b = st.columns([4, 1])
                        col_a.markdown(f"  - {item['descricao']}: R$ {item['valor']:,.2f}")
                        if col_b.button("❌", key=f"del_desp_{idx}"):
                            data["despesas"].pop(idx)
                            save_data(data)
                            st.session_state["financial_data"] = data
                            st.rerun()

            total = sum(i["valor"] for i in data["despesas"])
            st.markdown(f"**Total Despesas: R$ {total:,.2f}**")

    # ---- Dívidas ----
    with st.expander("💳 Dívidas", expanded=False):
        st.markdown("Cadastre suas dívidas atuais.")

        col1, col2 = st.columns(2)
        with col1:
            div_desc = st.text_input("Descrição:", key="div_desc", placeholder="Ex: Cartão de crédito Itaú")
            div_saldo = st.number_input("Saldo devedor (R$):", key="div_saldo", min_value=0.0, step=100.0)
        with col2:
            div_juros = st.number_input(
                "Juros mensais (% a.m.):",
                key="div_juros",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                help="Ex: Cartão de crédito ≈ 15-20% a.m., Cheque especial ≈ 8% a.m.",
            )
            div_parcela = st.number_input("Parcela mensal (R$):", key="div_parcela", min_value=0.0, step=10.0)

        if st.button("Adicionar Dívida", key="btn_add_div"):
            if div_desc and div_saldo > 0:
                data["dividas"].append({
                    "descricao": div_desc,
                    "saldo": div_saldo,
                    "juros_mensal": div_juros,
                    "parcela": div_parcela,
                })
                save_data(data)
                st.session_state["financial_data"] = data
                st.success(f"Dívida '{div_desc}' adicionada!")
                st.rerun()

        if data["dividas"]:
            st.markdown("**Dívidas cadastradas:**")
            for i, item in enumerate(data["dividas"]):
                col_a, col_b = st.columns([5, 1])
                col_a.markdown(
                    f"- **{item['descricao']}**: Saldo R$ {item['saldo']:,.2f} | "
                    f"{item['juros_mensal']}% a.m. | Parcela R$ {item['parcela']:,.2f}"
                )
                if col_b.button("❌", key=f"del_div_{i}"):
                    data["dividas"].pop(i)
                    save_data(data)
                    st.session_state["financial_data"] = data
                    st.rerun()

            total = sum(i["saldo"] for i in data["dividas"])
            total_parcelas = sum(i["parcela"] for i in data["dividas"])
            st.markdown(f"**Total Dívidas: R$ {total:,.2f} | Parcelas/mês: R$ {total_parcelas:,.2f}**")

    # ---- Investimentos ----
    with st.expander("📈 Investimentos Atuais", expanded=False):
        st.markdown("Cadastre seus investimentos atuais.")

        tipos_inv = [
            "Poupança",
            "Tesouro Direto",
            "CDB / RDB",
            "LCI / LCA",
            "Fundos de Renda Fixa",
            "Fundos de Renda Variável",
            "Ações",
            "ETFs (fundos de índice)",
            "FIIs (fundos imobiliários)",
            "Previdência Privada (PGBL/VGBL)",
            "Criptomoedas",
            "Outro",
        ]

        col1, col2, col3 = st.columns(3)
        with col1:
            inv_tipo = st.selectbox("Tipo:", tipos_inv, key="inv_tipo")
        with col2:
            inv_valor = st.number_input("Valor atual (R$):", key="inv_valor", min_value=0.0, step=100.0)
        with col3:
            inv_rent = st.text_input(
                "Rentabilidade:",
                key="inv_rent",
                placeholder="Ex: 12% a.a. / CDI+1%",
            )

        if st.button("Adicionar Investimento", key="btn_add_inv"):
            if inv_tipo and inv_valor > 0:
                data["investimentos"].append({
                    "tipo": inv_tipo,
                    "valor": inv_valor,
                    "rentabilidade": inv_rent,
                })
                save_data(data)
                st.session_state["financial_data"] = data
                st.success(f"Investimento '{inv_tipo}' adicionado!")
                st.rerun()

        if data["investimentos"]:
            st.markdown("**Investimentos cadastrados:**")
            for i, item in enumerate(data["investimentos"]):
                col_a, col_b = st.columns([5, 1])
                col_a.markdown(
                    f"- **{item['tipo']}**: R$ {item['valor']:,.2f} | "
                    f"Rentabilidade: {item.get('rentabilidade', 'N/A')}"
                )
                if col_b.button("❌", key=f"del_inv_{i}"):
                    data["investimentos"].pop(i)
                    save_data(data)
                    st.session_state["financial_data"] = data
                    st.rerun()

            total = sum(i["valor"] for i in data["investimentos"])
            st.markdown(f"**Total Investimentos: R$ {total:,.2f}**")


# ============================================================
# TAB 2: AGENTES ESPECIALISTAS
# ============================================================
with tab_agentes:
    st.subheader("🤖 Agentes Especialistas")
    st.markdown(
        "Execute cada agente especialista individualmente para obter análises detalhadas. "
        "Você precisará da **API Key da Anthropic** configurada na barra lateral."
    )

    if not api_key:
        st.warning("⚠️ Configure sua Anthropic API Key na barra lateral para usar os agentes.")
    else:
        data = st.session_state["financial_data"]

        # Verificar se há dados suficientes
        has_data = bool(data.get("receitas") or data.get("despesas"))
        if not has_data:
            st.info("ℹ️ Cadastre suas receitas e despesas na aba 'Meus Dados' primeiro.")

        for agent_key, (emoji, label) in AGENT_LABELS.items():
            with st.expander(f"{emoji} {label}", expanded=False):
                question = st.text_input(
                    "Pergunta específica (opcional):",
                    key=f"q_{agent_key}",
                    placeholder="Ex: Como devo priorizar o pagamento das minhas dívidas?",
                )

                col_btn, col_status = st.columns([2, 3])

                with col_btn:
                    run_btn = st.button(
                        f"Executar {label}",
                        key=f"btn_{agent_key}",
                        type="primary",
                        disabled=not has_data,
                    )

                if run_btn:
                    with st.spinner(f"Analisando com {label}..."):
                        try:
                            from agents.master_agent import MasterAgent
                            master = MasterAgent(api_key)
                            result = master.run_agent(agent_key, data, question or None)
                            st.session_state["agent_results"][agent_key] = result
                            st.success("Análise concluída!")
                        except Exception as e:
                            st.error(f"Erro: {e}")

                if agent_key in st.session_state["agent_results"]:
                    st.markdown("---")
                    st.markdown(st.session_state["agent_results"][agent_key])

        st.markdown("---")

        # Botão para rodar todos os agentes
        st.subheader("🚀 Executar Todos os Agentes")
        st.markdown("Execute todos os 5 agentes de uma vez para alimentar o Plano Integrado.")

        if st.button(
            "Executar Todos os Agentes",
            key="btn_run_all",
            type="primary",
            disabled=not has_data or not api_key,
        ):
            with st.spinner("Executando todos os agentes... (pode levar 1-2 minutos)"):
                try:
                    from agents.master_agent import MasterAgent
                    master = MasterAgent(api_key)
                    results = master.run_all_agents(data)
                    st.session_state["agent_results"] = results
                    st.success("Todos os agentes executados! Vá para a aba 'Plano Integrado'.")
                except Exception as e:
                    st.error(f"Erro: {e}")


# ============================================================
# TAB 3: PLANO INTEGRADO (MASTER AGENT)
# ============================================================
with tab_master:
    st.subheader("🎯 Plano Estratégico Integrado")
    st.markdown(
        "O **Master Orquestrador** sintetiza as análises de todos os agentes especialistas "
        "e produz um plano estratégico integrado e priorizado."
    )

    agent_results = st.session_state["agent_results"]
    has_results = len(agent_results) >= 3

    if not has_results:
        st.info(
            f"Execute pelo menos 3 agentes especialistas na aba anterior. "
            f"Agentes executados: {len(agent_results)}/5"
        )

    if not api_key:
        st.warning("⚠️ Configure sua Anthropic API Key na barra lateral.")

    if has_results and api_key:
        agents_done = len(agent_results)
        st.markdown(f"**Agentes disponíveis para síntese:** {agents_done}/5")

        for key, (emoji, label) in AGENT_LABELS.items():
            status = "✅" if key in agent_results else "❌"
            st.markdown(f"  {status} {emoji} {label}")

        st.markdown("---")

        if st.button("🎯 Gerar Plano Integrado", key="btn_master", type="primary"):
            with st.spinner("Master Orquestrador sintetizando análises... (pode levar 1-2 minutos)"):
                try:
                    from agents.master_agent import MasterAgent
                    master = MasterAgent(api_key)
                    result = master.orchestrate(
                        st.session_state["financial_data"],
                        agent_results,
                    )
                    st.session_state["master_result"] = result
                    st.success("Plano Integrado gerado!")
                except Exception as e:
                    st.error(f"Erro: {e}")

    if st.session_state["master_result"]:
        st.markdown("---")
        st.markdown("## 📋 Plano Estratégico Integrado")
        st.markdown(st.session_state["master_result"])

        # Download do plano
        plan_text = st.session_state["master_result"]
        st.download_button(
            "📥 Baixar Plano (texto)",
            data=plan_text.encode("utf-8"),
            file_name="plano_financeiro.txt",
            mime="text/plain",
        )


# ============================================================
# TAB 4: CHAT FINANCEIRO
# ============================================================
with tab_chat:
    st.subheader("💬 Chat Financeiro")
    st.markdown(
        "Tire dúvidas sobre finanças pessoais, estratégias e seu plano financeiro. "
        "O assistente tem acesso aos seus dados cadastrados."
    )

    if not api_key:
        st.warning("⚠️ Configure sua Anthropic API Key na barra lateral.")
    else:
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        # Exibir histórico do chat
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input do usuário
        user_input = st.chat_input("Faça uma pergunta sobre suas finanças...")

        if user_input:
            # Adicionar mensagem do usuário
            st.session_state["chat_history"].append({"role": "user", "content": user_input})

            with st.chat_message("user"):
                st.markdown(user_input)

            # Gerar resposta
            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    try:
                        import anthropic as ant
                        client = ant.Anthropic(api_key=api_key)

                        # Construir contexto financeiro
                        data = st.session_state["financial_data"]
                        from agents.base_agent import BaseAgent

                        base = BaseAgent(api_key)
                        financial_context = base._build_user_message(data, None)

                        system_chat = f"""Você é um assistente financeiro pessoal especializado.
Você tem acesso aos dados financeiros do usuário:

{financial_context}

Responda de forma clara, prática e personalizada com base nesses dados.
Seja direto e objetivo. Use linguagem simples e amigável.
Sempre responda em português do Brasil."""

                        messages_for_api = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state["chat_history"]
                        ]

                        response = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=1024,
                            system=system_chat,
                            messages=messages_for_api,
                        )
                        answer = response.content[0].text
                        st.markdown(answer)

                        st.session_state["chat_history"].append({
                            "role": "assistant",
                            "content": answer,
                        })

                    except Exception as e:
                        st.error(f"Erro: {e}")

        if st.session_state.get("chat_history"):
            if st.button("🗑️ Limpar conversa", key="btn_clear_chat"):
                st.session_state["chat_history"] = []
                st.rerun()
