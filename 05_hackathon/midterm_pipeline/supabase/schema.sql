-- City Congestion Tracker: Supabase schema
-- Run this in the Supabase SQL Editor to create tables and seed synthetic data.
-- Pipeline: Supabase → REST API → dashboard → AI.

-- Table: congestion_readings (location, timestamp, congestion level)
CREATE TABLE IF NOT EXISTS congestion_readings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_name TEXT NOT NULL,
  segment_zone TEXT,
  recorded_at TIMESTAMPTZ NOT NULL,
  congestion_level INTEGER NOT NULL CHECK (congestion_level >= 1 AND congestion_level <= 5),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 1 = free flow, 5 = severe congestion
CREATE INDEX IF NOT EXISTS idx_congestion_location ON congestion_readings(location_name);
CREATE INDEX IF NOT EXISTS idx_congestion_recorded_at ON congestion_readings(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_congestion_level ON congestion_readings(congestion_level);

-- Allow API (anon key) to read
ALTER TABLE congestion_readings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access on congestion_readings" ON congestion_readings;
CREATE POLICY "Allow public read access on congestion_readings" ON congestion_readings FOR SELECT USING (true);

-- Synthetic data: sample readings (run once; add more as needed)
INSERT INTO congestion_readings (location_name, segment_zone, recorded_at, congestion_level) VALUES
  ('Main & 5th', 'Downtown', now() - interval '2 hours', 4),
  ('Main & 5th', 'Downtown', now() - interval '5 hours', 3),
  ('Main & 5th', 'Downtown', now() - interval '1 day', 5),
  ('Highway 101 @ Exit 12', 'North Corridor', now() - interval '1 hour', 5),
  ('Highway 101 @ Exit 12', 'North Corridor', now() - interval '6 hours', 2),
  ('Highway 101 @ Exit 12', 'North Corridor', now() - interval '2 days', 4),
  ('Downtown Plaza', 'Central', now() - interval '3 hours', 3),
  ('Downtown Plaza', 'Central', now() - interval '1 day', 4),
  ('River Bridge South', 'East Side', now() - interval '4 hours', 2),
  ('River Bridge South', 'East Side', now() - interval '3 days', 5),
  ('Airport Access Rd', 'West', now() - interval '2 hours', 1),
  ('Airport Access Rd', 'West', now() - interval '5 days', 3);
