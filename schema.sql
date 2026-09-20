-- Script SQL para ser executado no SQL Editor do Supabase

-- 1. Tabela de Saldos dos Usuários
CREATE TABLE IF NOT EXISTS public.saldos (
    user_id BIGINT PRIMARY KEY,
    saldo NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Tabela de Estoque de Cartões
CREATE TABLE IF NOT EXISTS public.estoque (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    categoria TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    adicionado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index para buscas rápidas por categoria no estoque
CREATE INDEX IF NOT EXISTS idx_estoque_categoria ON public.estoque(categoria);

-- 3. Tabela de Histórico de Eventos
CREATE TABLE IF NOT EXISTS public.historico (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    nome TEXT,
    username TEXT,
    acao TEXT NOT NULL,
    detalhe TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index para buscas rápidas por user_id no histórico
CREATE INDEX IF NOT EXISTS idx_historico_user_id ON public.historico(user_id);
