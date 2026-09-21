CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    last_login_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX users_status_idx ON users (status);
CREATE INDEX users_email_lower_idx ON users (lower(email));

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX user_roles_role_id_idx ON user_roles (role_id);

CREATE TABLE model_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    base_url TEXT,
    api_key_env_name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX model_providers_active_idx ON model_providers (is_active);

CREATE TABLE model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES model_providers(id) ON DELETE RESTRICT,
    name TEXT NOT NULL UNIQUE,
    model_name TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('answer', 'summarize', 'embedding', 'rerank')),
    temperature DOUBLE PRECISION CHECK (temperature IS NULL OR temperature BETWEEN 0 AND 2),
    max_tokens INTEGER CHECK (max_tokens IS NULL OR max_tokens > 0),
    top_p DOUBLE PRECISION CHECK (top_p IS NULL OR top_p BETWEEN 0 AND 1),
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX model_configs_provider_id_idx ON model_configs (provider_id);
CREATE INDEX model_configs_purpose_idx ON model_configs (purpose);
CREATE UNIQUE INDEX model_configs_one_default_per_purpose_idx
    ON model_configs (purpose)
    WHERE is_default;

CREATE TABLE rag_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    embedding_model_config_id UUID REFERENCES model_configs(id) ON DELETE SET NULL,
    chunk_size INTEGER NOT NULL DEFAULT 1000 CHECK (chunk_size > 0),
    chunk_overlap INTEGER NOT NULL DEFAULT 150 CHECK (chunk_overlap >= 0),
    retrieval_limit INTEGER NOT NULL DEFAULT 10 CHECK (retrieval_limit BETWEEN 1 AND 100),
    similarity_threshold DOUBLE PRECISION CHECK (similarity_threshold IS NULL OR similarity_threshold BETWEEN 0 AND 1),
    hybrid_keyword_weight DOUBLE PRECISION NOT NULL DEFAULT 0.55 CHECK (hybrid_keyword_weight BETWEEN 0 AND 1),
    hybrid_vector_weight DOUBLE PRECISION NOT NULL DEFAULT 0.35 CHECK (hybrid_vector_weight BETWEEN 0 AND 1),
    rerank_enabled BOOLEAN NOT NULL DEFAULT false,
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rag_configs_chunk_overlap_lt_size CHECK (chunk_overlap < chunk_size)
);

CREATE UNIQUE INDEX rag_configs_one_default_idx
    ON rag_configs ((true))
    WHERE is_default;

CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('paper_summary', 'research_brief', 'qa', 'ranking_explanation')),
    template_text TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1',
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

CREATE INDEX prompt_templates_purpose_idx ON prompt_templates (purpose);
CREATE INDEX prompt_templates_active_idx ON prompt_templates (is_active);

CREATE TABLE app_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT false,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE admin_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX admin_audit_logs_actor_user_id_idx ON admin_audit_logs (actor_user_id);
CREATE INDEX admin_audit_logs_entity_idx ON admin_audit_logs (entity_type, entity_id);
CREATE INDEX admin_audit_logs_created_at_idx ON admin_audit_logs (created_at DESC);

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER model_providers_set_updated_at
BEFORE UPDATE ON model_providers
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER model_configs_set_updated_at
BEFORE UPDATE ON model_configs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER rag_configs_set_updated_at
BEFORE UPDATE ON rag_configs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER prompt_templates_set_updated_at
BEFORE UPDATE ON prompt_templates
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER app_settings_set_updated_at
BEFORE UPDATE ON app_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

INSERT INTO roles (name, description)
VALUES
    ('admin', 'Can manage users, model settings, prompts, and application config.'),
    ('user', 'Can search papers and use assistant features.');

INSERT INTO model_providers (name, base_url, api_key_env_name)
VALUES
    ('openai', 'https://api.openai.com/v1', 'OPENAI_API_KEY');

INSERT INTO model_configs (
    provider_id,
    name,
    model_name,
    purpose,
    temperature,
    max_tokens,
    top_p,
    is_default
)
SELECT
    model_providers.id,
    defaults.name,
    defaults.model_name,
    defaults.purpose,
    defaults.temperature,
    defaults.max_tokens,
    defaults.top_p,
    true
FROM model_providers
CROSS JOIN (
    VALUES
        ('Default answer model', 'gpt-4.1-mini', 'answer', 0.2::double precision, 1200, 1::double precision),
        ('Default summary model', 'gpt-4.1-mini', 'summarize', 0.2::double precision, 900, 1::double precision),
        ('Default embedding model', 'text-embedding-3-small', 'embedding', NULL::double precision, NULL::integer, NULL::double precision)
) AS defaults(name, model_name, purpose, temperature, max_tokens, top_p)
WHERE model_providers.name = 'openai';

INSERT INTO rag_configs (
    name,
    embedding_model_config_id,
    chunk_size,
    chunk_overlap,
    retrieval_limit,
    similarity_threshold,
    hybrid_keyword_weight,
    hybrid_vector_weight,
    rerank_enabled,
    is_default
)
SELECT
    'Default RAG config',
    model_configs.id,
    1000,
    150,
    10,
    0.2,
    0.55,
    0.35,
    false,
    true
FROM model_configs
WHERE model_configs.purpose = 'embedding'
    AND model_configs.is_default;

INSERT INTO app_settings (key, value, description, is_public)
VALUES
    ('app.name', '"AI Knowledge Assistant"'::jsonb, 'Application display name.', true),
    ('search.default_limit', '10'::jsonb, 'Default number of papers returned by search.', true),
    ('search.max_limit', '25'::jsonb, 'Maximum number of papers returned by search.', false);
