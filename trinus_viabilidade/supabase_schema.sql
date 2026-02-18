-- =====================================================================
-- Trinus Viabilidade — Schema Supabase
-- =====================================================================
-- Execute este SQL no SQL Editor do Supabase (https://supabase.com/dashboard)
-- Ordem: 1) tabelas, 2) índices, 3) RLS policies
-- =====================================================================

-- 1. ESTUDOS — registro principal de cada viabilidade
CREATE TABLE IF NOT EXISTS estudos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Dados do empreendimento (inputs)
    tipologia TEXT NOT NULL,
    padrao TEXT NOT NULL,
    estado TEXT NOT NULL,
    cidade TEXT NOT NULL,
    regiao TEXT,
    num_unidades INTEGER NOT NULL,
    tipo_negociacao TEXT,
    area_terreno_m2 DOUBLE PRECISION,
    area_privativa_media_m2 DOUBLE PRECISION,
    vgv_estimado DOUBLE PRECISION,
    permuta_percentual DOUBLE PRECISION,
    permuta_referencia TEXT,
    valor_aquisicao DOUBLE PRECISION,

    -- Status do estudo
    status TEXT NOT NULL DEFAULT 'gerado'
        CHECK (status IN ('gerado', 'simulado', 'exportado'))
);

-- 2. PREMISSAS — cada premissa final por estudo
CREATE TABLE IF NOT EXISTS premissas_registro (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estudo_id UUID NOT NULL REFERENCES estudos(id) ON DELETE CASCADE,

    nome TEXT NOT NULL,
    valor_original DOUBLE PRECISION NOT NULL,
    valor_ia DOUBLE PRECISION,
    valor_final DOUBLE PRECISION NOT NULL,
    unidade TEXT NOT NULL,
    categoria TEXT NOT NULL,
    subcategoria TEXT NOT NULL,
    fonte TEXT,

    UNIQUE(estudo_id, nome)
);

-- 3. CRONOGRAMA — datas macro por estudo
CREATE TABLE IF NOT EXISTS cronograma_registro (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estudo_id UUID NOT NULL REFERENCES estudos(id) ON DELETE CASCADE,

    inicio_projeto DATE NOT NULL,
    lancamento DATE,
    inicio_obra DATE,
    fim_obra DATE,
    inicio_vendas_pos DATE,

    UNIQUE(estudo_id)
);

-- 4. SIMULACAO — indicadores de resultado por estudo
CREATE TABLE IF NOT EXISTS simulacao_resultado (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estudo_id UUID NOT NULL REFERENCES estudos(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    vgv DOUBLE PRECISION,
    receita_liquida DOUBLE PRECISION,
    custo_total DOUBLE PRECISION,
    despesa_total DOUBLE PRECISION,
    resultado_projeto DOUBLE PRECISION,
    margem_vgv DOUBLE PRECISION,
    margem_custo DOUBLE PRECISION,
    tir_mensal DOUBLE PRECISION,
    tir_anual DOUBLE PRECISION,
    vpl DOUBLE PRECISION,
    payback_meses INTEGER,
    exposicao_maxima DOUBLE PRECISION,
    lucro_sobre_investimento DOUBLE PRECISION,

    UNIQUE(estudo_id)
);

-- 5. IA_FEEDBACK — insights e cronograma gerados pela IA
CREATE TABLE IF NOT EXISTS ia_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estudo_id UUID NOT NULL REFERENCES estudos(id) ON DELETE CASCADE,

    insights JSONB DEFAULT '[]'::jsonb,
    recomendacoes JSONB DEFAULT '[]'::jsonb,
    cronograma_justificativas JSONB DEFAULT '{}'::jsonb,
    ajustes_aplicados INTEGER DEFAULT 0,
    modelo TEXT,

    UNIQUE(estudo_id)
);

-- =====================================================================
-- INDICES para consultas de retroalimentação
-- =====================================================================
CREATE INDEX IF NOT EXISTS idx_estudos_cidade_tipologia
    ON estudos(cidade, tipologia);

CREATE INDEX IF NOT EXISTS idx_estudos_estado_tipologia
    ON estudos(estado, tipologia);

CREATE INDEX IF NOT EXISTS idx_estudos_status
    ON estudos(status);

CREATE INDEX IF NOT EXISTS idx_premissas_estudo
    ON premissas_registro(estudo_id);

CREATE INDEX IF NOT EXISTS idx_premissas_nome_estudo
    ON premissas_registro(nome, estudo_id);

CREATE INDEX IF NOT EXISTS idx_simulacao_estudo
    ON simulacao_resultado(estudo_id);

-- =====================================================================
-- VIEW para retroalimentação: estatísticas agregadas
-- =====================================================================
CREATE OR REPLACE VIEW vw_estatisticas_premissas AS
SELECT
    e.cidade,
    e.estado,
    e.tipologia,
    e.padrao,
    pr.nome AS premissa_nome,
    pr.unidade,
    COUNT(*) AS total_estudos,
    AVG(pr.valor_final) AS media,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pr.valor_final) AS mediana,
    MIN(pr.valor_final) AS minimo,
    MAX(pr.valor_final) AS maximo,
    STDDEV(pr.valor_final) AS desvio_padrao
FROM premissas_registro pr
JOIN estudos e ON e.id = pr.estudo_id
WHERE e.status IN ('simulado', 'exportado')
GROUP BY e.cidade, e.estado, e.tipologia, e.padrao, pr.nome, pr.unidade;

-- VIEW para retroalimentação: indicadores por perfil
CREATE OR REPLACE VIEW vw_estatisticas_indicadores AS
SELECT
    e.cidade,
    e.estado,
    e.tipologia,
    e.padrao,
    COUNT(*) AS total_estudos,
    AVG(sr.margem_vgv) AS media_margem_vgv,
    AVG(sr.tir_anual) AS media_tir_anual,
    AVG(sr.vpl) AS media_vpl,
    AVG(sr.payback_meses) AS media_payback,
    AVG(sr.exposicao_maxima) AS media_exposicao
FROM simulacao_resultado sr
JOIN estudos e ON e.id = sr.estudo_id
WHERE e.status IN ('simulado', 'exportado')
GROUP BY e.cidade, e.estado, e.tipologia, e.padrao;

-- =====================================================================
-- RLS (Row Level Security) — desativado por padrão para simplicidade.
-- Ative e configure conforme seu modelo de autenticação.
-- =====================================================================
-- ALTER TABLE estudos ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE premissas_registro ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cronograma_registro ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE simulacao_resultado ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ia_feedback ENABLE ROW LEVEL SECURITY;

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_estudos_updated_at
    BEFORE UPDATE ON estudos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
