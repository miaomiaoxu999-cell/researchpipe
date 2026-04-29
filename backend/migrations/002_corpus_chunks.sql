-- Path B: corpus_chunks for vector embeddings
-- 1 chunk = ~450 tokens, ~750k chunks expected for 14,928 PDFs

CREATE TABLE IF NOT EXISTS corpus_chunks (
  id          BIGSERIAL PRIMARY KEY,
  file_id     BIGINT NOT NULL REFERENCES corpus_files(id) ON DELETE CASCADE,
  chunk_idx   INT NOT NULL,
  page_no     INT,
  content     TEXT NOT NULL,
  token_count INT,
  embedding   vector(1024),
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (file_id, chunk_idx)
);

CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON corpus_chunks (file_id);

-- ivfflat cosine index — built later after data is loaded (recommended for ivfflat)
-- For now create a small one to allow queries; will rebuild after embed run.
-- (Using ANALYZE rather than reindexing avoids blocking)

-- Track embed status on the file level
ALTER TABLE corpus_files
  ADD COLUMN IF NOT EXISTS embed_status TEXT NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS embed_error  TEXT,
  ADD COLUMN IF NOT EXISTS chunk_count  INT,
  ADD COLUMN IF NOT EXISTS embedded_at  TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_files_embed_status ON corpus_files (embed_status);
