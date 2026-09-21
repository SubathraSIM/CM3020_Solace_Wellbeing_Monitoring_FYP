-- User table to store account details and consent information
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    profession TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    consent_accepted INTEGER NOT NULL DEFAULT 0,
    consent_accepted_at TEXT
);

-- Check ins table to store each check-in input details and analysis results
CREATE TABLE IF NOT EXISTS check_ins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    input_type TEXT NOT NULL CHECK (input_type IN ('audio', 'video')),
    -- original language, original transcript and English transcript
    original_language TEXT NOT NULL DEFAULT 'English',
    transcript_original TEXT NOT NULL,
    transcript TEXT NOT NULL,
    -- emotion scores, allowing no vision score for audio check-ins
    text_score REAL NOT NULL,
    audio_score REAL NOT NULL,
    vision_score REAL,
    -- combined strain and wellbeing scores
    strain_score REAL NOT NULL,
    wellbeing_score REAL NOT NULL,
    -- visual measurements when available alongside the speech measurements
    blink_rate REAL,
    head_position TEXT,
    speech_rate REAL NOT NULL,
    disfluency_rate REAL NOT NULL,
    lexical_variety REAL NOT NULL,
    -- summary, explanation, recommendations and result image name
    summary TEXT NOT NULL,
    explanation TEXT,
    recommendation TEXT,
    image_name TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Speed up history queries by user and date
CREATE INDEX IF NOT EXISTS idx_check_ins_user_date ON check_ins(user_id, created_at);

-- Questionnaire responses for in app participants
CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    answers_json TEXT NOT NULL,
    personal_burnout REAL,
    work_burnout REAL,
    cbi_score REAL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Weekly reminder preference for questionnaire
CREATE TABLE IF NOT EXISTS questionnaire_prefs (
    user_id INTEGER PRIMARY KEY,
    reminders_enabled INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stored comparison between a questionnaire and check-in
CREATE TABLE IF NOT EXISTS cbi_comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    questionnaire_id INTEGER NOT NULL,
    check_in_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cbi_score REAL,
    cbi_band TEXT,
    expected_wellbeing_band TEXT,
    wellbeing_score REAL,
    solace_band TEXT,
    bands_agree INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (questionnaire_id) REFERENCES questionnaire_responses(id) ON DELETE CASCADE,
    FOREIGN KEY (check_in_id) REFERENCES check_ins(id) ON DELETE CASCADE
);