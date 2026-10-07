CREATE DATABASE IF NOT EXISTS saude_suplementar CHARACTER SET utf8mb4;
USE saude_suplementar;

CREATE TABLE IF NOT EXISTS dim_operadora (
    registro_ans      CHAR(6)      PRIMARY KEY,
    cnpj              CHAR(14),
    razao_social      VARCHAR(150) NOT NULL,
    nome_fantasia     VARCHAR(150),
    modalidade        VARCHAR(60),
    uf                CHAR(2),
    data_registro_ans DATE
);

CREATE TABLE IF NOT EXISTS dim_periodo (
    id_periodo SMALLINT PRIMARY KEY,
    ano        SMALLINT NOT NULL,
    trimestre  TINYINT  NOT NULL,
    rotulo     CHAR(6)  NOT NULL,
    data_fim   DATE     NOT NULL,
    UNIQUE KEY uk_ano_trimestre (ano, trimestre)
);

CREATE TABLE IF NOT EXISTS stg_demonstracao_contabil (
    id                BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_ref          DATE           NOT NULL,
    registro_ans      CHAR(6)        NOT NULL,
    cd_conta_contabil VARCHAR(20)    NOT NULL,
    descricao         VARCHAR(255),
    vl_saldo_inicial  DECIMAL(18,2),
    vl_saldo_final    DECIMAL(18,2),
    arquivo_origem    VARCHAR(60)    NOT NULL,
    dt_carga          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY ix_stg_busca (registro_ans, data_ref, cd_conta_contabil)
);

CREATE TABLE IF NOT EXISTS fato_financeiro (
    registro_ans              CHAR(6),
    id_periodo                SMALLINT,
    contraprestacoes_efetivas DECIMAL(18,2),
    despesas_assistenciais    DECIMAL(18,2),
    resultado_liquido         DECIMAL(18,2),
    ativo_total               DECIMAL(18,2),
    passivo_total             DECIMAL(18,2),
    patrimonio_liquido        DECIMAL(18,2),
    PRIMARY KEY (registro_ans, id_periodo),
    CONSTRAINT fk_fato_op  FOREIGN KEY (registro_ans)
        REFERENCES dim_operadora (registro_ans),
    CONSTRAINT fk_fato_per FOREIGN KEY (id_periodo)
        REFERENCES dim_periodo (id_periodo)
);