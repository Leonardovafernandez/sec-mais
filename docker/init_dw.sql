-- Script de Inicialização do Data Warehouse Analítico SEC MAIS
-- Executado automaticamente na criação do container PostgreSQL

CREATE SCHEMA IF NOT EXISTS ouro;
CREATE SCHEMA IF NOT EXISTS marts;

COMMENT ON SCHEMA ouro IS 'Camada Ouro: Tabelas fatos e dimensões consolidadas e integradas';
COMMENT ON SCHEMA marts IS 'Camada Marts / Analítica: Visões de consumo, agregações e indicadores para BI e relatórios';
