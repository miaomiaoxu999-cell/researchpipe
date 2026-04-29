-- ResearchPipe 2026 研报合集 corpus schema
-- Path A: filename manifest
-- Path B (future): chunks + embeddings

CREATE TABLE IF NOT EXISTS corpus_files (
  id               BIGSERIAL PRIMARY KEY,
  week             TEXT NOT NULL,
  library          TEXT NOT NULL,
  title            TEXT NOT NULL,
  broker           TEXT,
  report_date      DATE,
  pages            INT,
  industry_tags    TEXT[] DEFAULT '{}',
  file_path        TEXT NOT NULL UNIQUE,
  file_size        BIGINT,
  filename_pattern TEXT,
  created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_files_broker     ON corpus_files (broker);
CREATE INDEX IF NOT EXISTS idx_files_date       ON corpus_files (report_date DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_files_industry   ON corpus_files USING GIN (industry_tags);
CREATE INDEX IF NOT EXISTS idx_files_title_trgm ON corpus_files USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_files_week       ON corpus_files (week);
CREATE INDEX IF NOT EXISTS idx_files_library    ON corpus_files (library);
