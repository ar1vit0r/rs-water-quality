CREATE TABLE IF NOT EXISTS station (
    cd_estacao   TEXT PRIMARY KEY,
    uf           TEXT NOT NULL,
    entidade     TEXT,
    corpo_dagua  TEXT,
    ambiente     TEXT CHECK (ambiente IN ('lotico', 'lentico')),
    lat          DOUBLE PRECISION,
    lon          DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS measurement (
    cd_estacao   TEXT NOT NULL REFERENCES station (cd_estacao),
    indicator    TEXT NOT NULL,
    year         SMALLINT NOT NULL,
    stat         TEXT NOT NULL CHECK (stat IN ('mean', 'min', 'max')),
    value        DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (cd_estacao, indicator, year, stat)
);

CREATE TABLE IF NOT EXISTS limits (
    indicator     TEXT NOT NULL,
    ambiente      TEXT,
    op            TEXT NOT NULL CHECK (op IN ('min', 'max')),
    value         DOUBLE PRECISION NOT NULL,
    unit          TEXT NOT NULL,
    stat_checked  TEXT NOT NULL CHECK (stat_checked IN ('mean', 'min', 'max')),
    source        TEXT NOT NULL,
    UNIQUE (indicator, ambiente)
);

CREATE TABLE IF NOT EXISTS load_audit (
    id            BIGSERIAL PRIMARY KEY,
    dataset_id    TEXT NOT NULL,
    indicator     TEXT NOT NULL,
    url           TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    rows_read     INTEGER NOT NULL,
    rows_loaded   INTEGER NOT NULL,
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE VIEW violation AS
SELECT m.cd_estacao, s.corpo_dagua, s.ambiente, m.indicator, m.year,
       m.stat, m.value, l.op, l.value AS limit_value, l.unit, l.source
FROM measurement m
JOIN station s USING (cd_estacao)
JOIN limits l
  ON l.indicator = m.indicator
 AND l.stat_checked = m.stat
 AND (l.ambiente IS NULL OR l.ambiente = s.ambiente)
WHERE (l.op = 'min' AND m.value < l.value)
   OR (l.op = 'max' AND m.value > l.value);
