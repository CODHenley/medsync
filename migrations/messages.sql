-- Staff messaging system. Messages auto-expire after 30 days.
-- channel = 'staff' is the all-staff broadcast channel.
-- channel = sorted pair of two user UUIDs joined by ':' for DMs.

CREATE TABLE IF NOT EXISTS messages (
  id          uuid        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  sender_id   uuid        NOT NULL,
  sender_name text        NOT NULL,
  sender_avatar text,                    -- base64 data URI or null
  channel     text        NOT NULL DEFAULT 'staff',
  content     text        NOT NULL,
  sent_at     timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL DEFAULT (now() + interval '30 days')
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_sent ON messages (channel, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_expires      ON messages (expires_at);
CREATE INDEX IF NOT EXISTS idx_messages_sender       ON messages (sender_id);

-- Track which messages each user has read
CREATE TABLE IF NOT EXISTS message_reads (
  message_id  uuid        NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  user_id     uuid        NOT NULL,
  read_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (message_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_message_reads_user ON message_reads (user_id);

ALTER TABLE messages       ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_reads  ENABLE ROW LEVEL SECURITY;

-- Service role full access
CREATE POLICY "service role messages"      ON messages       FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service role message_reads" ON message_reads  FOR ALL USING (auth.role() = 'service_role');

-- Authenticated users: insert + read messages, manage their own reads
CREATE POLICY "auth insert messages"  ON messages      FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "auth read messages"    ON messages      FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth insert reads"     ON message_reads FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "auth read reads"       ON message_reads FOR SELECT USING (auth.role() = 'authenticated');

-- Nightly cleanup: delete expired messages (run via pg_cron or manually)
-- SELECT cron.schedule('expire-messages', '0 3 * * *', $$DELETE FROM messages WHERE expires_at < now()$$);
