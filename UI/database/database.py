# Import required libraries
import csv, hashlib, hmac, json, os, sqlite3
from pathlib import Path
from contextlib import contextmanager

# database inside the project data folder
ROOT = Path(__file__).resolve().parents[2]
DATABASE_FOLDER = ROOT / 'data' / 'database'
DATABASE_PATH = DATABASE_FOLDER / 'wellbeing_system.db'

# schema beside this module
SCHEMA_PATH = Path(__file__).resolve().parent / 'schema.sql'

# number of rounds used to hash passwords
PBKDF2_ITERATIONS = 100000

# Folder and column layout for the questionnaire CSV export
QUESTIONNAIRE_EXPORT_FOLDER = ROOT / 'data' / 'questionnaire results'

# question headers
QUESTION_HEADERS = [
    "How often do you feel tired?",
    "How often are you physically exhausted?",
    "How often are you emotionally exhausted?",
    "How often do you think: \"I can't take it anymore\"?",
    "How often do you feel worn out?",
    "How often do you feel weak and susceptible to illness?",
    "Is your work emotionally exhausting?",
    "Do you feel burnt out because of your work?",
    "Does your work frustrate you?",
    "Do you feel worn out at the end of the working day?",
    "Are you exhausted in the morning at the thought of another day at work?",
    "Do you feel that every working hour is tiring for you?",
    "Do you have enough energy for family and friends during leisure time?",
]

# Band thresholds for the CBI vs Solace comparison
CBI_HIGH = 75
CBI_MODERATE = 50
WELLBEING_HIGH = 67
WELLBEING_MIXED = 34

# Map a CBI burnout score to its band
def _cbi_band(score):
    if score >= CBI_HIGH:
        return 'High burnout'
    if score >= CBI_MODERATE:
        return 'Moderate burnout'
    return 'Low burnout'

# wellbeing band CBI band correspond to
def _expected_wellbeing_band(cbi_band):
    return {'High burnout': 'Low', 'Moderate burnout': 'Mixed', 'Low burnout': 'High'}[cbi_band]

# Solace wellbeing score to its band
def _wellbeing_band(score):
    if score >= WELLBEING_HIGH:
        return 'High'
    if score >= WELLBEING_MIXED:
        return 'Mixed'
    return 'Low'

# Compare a check-in with questionnaire from same local date
def _record_cbi_comparison(connection, user_id, check_in_id, wellbeing_score):
    # execute select statement
    row = connection.execute(
        """
        SELECT q.id, q.cbi_score
        FROM questionnaire_responses q
        JOIN check_ins c ON c.user_id = q.user_id
        WHERE q.user_id = ?
        AND c.id = ?
        AND date(q.created_at, 'localtime') = date(c.created_at, 'localtime')
        ORDER BY q.created_at DESC, q.id DESC
        LIMIT 1
        """,
        (user_id, check_in_id)
    ).fetchone()

    # Remove earlier comparison before refreshing it
    connection.execute("DELETE FROM cbi_comparisons WHERE check_in_id = ?",(check_in_id,))

    # check-in without a comparison if no questionnaire matches
    if row is None or row["cbi_score"] is None:
        return

    cbi_score = float(row["cbi_score"])
    wellbeing_score = float(wellbeing_score)
    cbi_band = _cbi_band(cbi_score)
    expected = _expected_wellbeing_band(cbi_band)
    solace_band = _wellbeing_band(wellbeing_score)
    agree = 1 if solace_band == expected else 0

    # Save same day comparison
    connection.execute(
        """
        INSERT INTO cbi_comparisons
            (user_id, questionnaire_id, check_in_id, cbi_score, cbi_band,
             expected_wellbeing_band, wellbeing_score, solace_band, bands_agree)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, row["id"], check_in_id, cbi_score, cbi_band,expected, wellbeing_score, solace_band, agree)
    )

# database connection and its transaction
@contextmanager
def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    # query results to be read by column name
    connection.row_factory = sqlite3.Row
    # Enable linked record rules including deletion of user check-ins
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        yield connection
        # Commit changes only when operation succeeds
        connection.commit()
    # Roll back changes if an operation fails
    except Exception:
        connection.rollback()
        raise
    # close connection
    finally:
        connection.close()

# missing columns to an existing table
def add_columns(connection, table, columns):
    existing = {row['name'] for row in connection.execute(f'PRAGMA table_info({table})')}
    for name, column_type in columns.items():
        if name not in existing:
            # alter table and add column
            connection.execute(f'ALTER TABLE {table} ADD COLUMN {name} {column_type}')

# Create database and update older table layouts
def create_database():
    DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        # Create tables and indexes from the schema
        connection.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
        # newer profile and check in fields when they are missing
        add_columns(connection, 'users', {'consent_accepted': 'INTEGER NOT NULL DEFAULT 0', 'consent_accepted_at': 'TEXT', 'email': "TEXT NOT NULL DEFAULT ''", 'profession': "TEXT NOT NULL DEFAULT ''", 'address': "TEXT NOT NULL DEFAULT ''"})
        add_columns(connection, 'check_ins', {'original_language': "TEXT NOT NULL DEFAULT 'English'", 'transcript_original': 'TEXT', 'explanation': 'TEXT', 'recommendation': 'TEXT', 'image_name': 'TEXT', 'blink_rate': 'REAL', 'head_position': 'TEXT', 'speech_rate': 'REAL', 'disfluency_rate': 'REAL', 'lexical_variety': 'REAL'})
    return DATABASE_PATH

# Hash password with a fresh random salt
def hash_password(password):
    # salt 16
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    # store salt and hash together so the password can be checked later
    return f'{salt.hex()}:{password_hash.hex()}'

# check password exactly as typed using its stored salt
def verify_password(password, stored_password):
    # salt text and hash text
    salt_text, hash_text = stored_password.split(':')
    salt = bytes.fromhex(salt_text)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    # compare hash using constant time comparison helper
    return hmac.compare_digest(password_hash.hex(), hash_text)

# account with a hashed password
def create_user(full_name, username, password):
    try:
        with connect() as connection:
            # insert the values
            connection.execute(
                """
                INSERT INTO users (full_name, username, password_hash)
                VALUES (?, ?, ?)
                """,
                (full_name, username, hash_password(password))
            )
        return True
    # error when the new account breaks a database constraint
    except sqlite3.IntegrityError:
        return False

# Check username and password before returning account details
def authenticate_user(username, password):
    with connect() as connection:
        # Match username uppercase and lowercase letters exactly
        user = connection.execute(
            """
            SELECT id, full_name, username, password_hash, consent_accepted
            FROM users
            WHERE username COLLATE BINARY = ?
            """,
            (username,)
        ).fetchone()
    # missing users and incorrect passwords
    if user is None or not verify_password(password, user['password_hash']):
        return None
    return {'id': user['id'], 'full_name': user['full_name'], 'username': user['username'], 'consent_accepted': bool(user['consent_accepted'])}

# Record user consent and when it was accepted
def save_consent(user_id):
    with connect() as connection:
        # update users table
        connection.execute(
            """
            UPDATE users
            SET consent_accepted = 1,
                consent_accepted_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id,)
        )

# Save check-in or replace user latest one from today
def save_check_in(user_id, result):
    with connect() as connection:
        # existing check in on today local date
        existing = connection.execute(
            """
            SELECT id
            FROM check_ins
            WHERE user_id = ?
            AND date(created_at, 'localtime') = date('now', 'localtime')
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()
        # result values in the same order as the database fields
        values = (result['recording_type'], result['language'], result['transcript'], result['transcript_english'], result['text_score'], result['audio_score'], result.get('vision_score'), result['strain_score'], result['wellbeing_score'], result['phrase_english'], result['explanation_english'], result['recommendation_english'], result['image_name'], result.get('blink_rate'), result.get('head_position'), result['speech_rate'], result['disfluency_rate'], result['lexical_variety'])
        # Update today existing check in instead of adding another
        if existing:
            connection.execute(
                """
                UPDATE check_ins
                SET
                    created_at = CURRENT_TIMESTAMP,
                    input_type = ?,
                    original_language = ?,
                    transcript_original = ?,
                    transcript = ?,
                    text_score = ?,
                    audio_score = ?,
                    vision_score = ?,
                    strain_score = ?,
                    wellbeing_score = ?,
                    summary = ?,
                    explanation = ?,
                    recommendation = ?,
                    image_name = ?,
                    blink_rate = ?,
                    head_position = ?,
                    speech_rate = ?,
                    disfluency_rate = ?,
                    lexical_variety = ?
                WHERE id = ?
                """,
                values + (existing['id'],)
            )
            check_in_id = existing['id']
        else:
        # insert new check in when none exists for today
            cursor = connection.execute(
                """
                INSERT INTO check_ins (
                    user_id,
                    input_type,
                    original_language,
                    transcript_original,
                    transcript,
                    text_score,
                    audio_score,
                    vision_score,
                    strain_score,
                    wellbeing_score,
                    summary,
                    explanation,
                    recommendation,
                    image_name,
                    blink_rate,
                    head_position,
                    speech_rate,
                    disfluency_rate,
                    lexical_variety
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id,) + values
            )
            check_in_id = cursor.lastrowid
        # pair check-in with the latest questionnaire and store the comparison
        _record_cbi_comparison(connection, user_id, check_in_id, result['wellbeing_score'])
        return check_in_id

# recent wellbeing scores in time order
def get_recent_scores(user_id, limit=7):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT wellbeing_score
            FROM check_ins
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()
    # newest first query results for the trend view
    return [float(row['wellbeing_score']) for row in reversed(rows)]

# past strain scores from oldest to newest
def get_previous_strain_scores(user_id, limit=30):
    with connect() as connection:
        # select statement
        rows = connection.execute(
            """
            SELECT strain_score
            FROM check_ins
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()
    return [float(row['strain_score']) for row in reversed(rows)]

# Count all check ins saved for user
def get_check_in_count(user_id):
    with connect() as connection:
        # count statement
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM check_ins
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()
    return int(row['total'])

# recent daily check-ins for the history view
def get_month_check_ins(user_id, limit=31):
    with connect() as connection:
        # highest check-in ID for each local date
        rows = connection.execute(
            """
            SELECT
                date(current_row.created_at, 'localtime') AS date,
                current_row.wellbeing_score AS score,
                current_row.summary AS phrase
            FROM check_ins AS current_row
            WHERE current_row.user_id = ?
            AND current_row.id IN (
                SELECT MAX(grouped_row.id)
                FROM check_ins AS grouped_row
                WHERE grouped_row.user_id = ?
                GROUP BY date(grouped_row.created_at, 'localtime')
            )
            ORDER BY current_row.created_at DESC, current_row.id DESC
            LIMIT ?
            """,
            (user_id, user_id, limit)
        ).fetchall()
    # date, day, score and summary for display
    return [{'date': row['date'], 'day': row['date'][8:10], 'score': float(row['score']), 'phrase': row['phrase']} for row in reversed(rows)]

# all dates with a check-in in the selected month
def get_check_in_dates(user_id, year, month):
    month_key = f'{int(year):04d}-{int(month):02d}'
    with connect() as connection:
        # select the distinct 
        rows = connection.execute(
            """
            SELECT DISTINCT date(created_at, 'localtime') AS check_in_date
            FROM check_ins
            WHERE user_id = ?
            AND strftime('%Y-%m', created_at, 'localtime') = ?
            ORDER BY check_in_date
            """,
            (user_id, month_key)
        ).fetchall()
    # return the row
    return [row['check_in_date'] for row in rows]

# latest check in for a chosen local date
def get_check_in_for_date(user_id, date_text):
    with connect() as connection:
        # select statement
        row = connection.execute(
            """
            SELECT
                id,
                datetime(created_at, 'localtime') AS created_at_local,
                input_type,
                original_language,
                transcript_original,
                transcript,
                text_score,
                audio_score,
                vision_score,
                strain_score,
                wellbeing_score,
                summary,
                explanation,
                recommendation,
                image_name,
                blink_rate,
                head_position,
                speech_rate,
                disfluency_rate,
                lexical_variety
            FROM check_ins
            WHERE user_id = ?
            AND date(created_at, 'localtime') = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user_id, date_text)
        ).fetchone()
    # return row
    return dict(row) if row else None

# Delete account and let linked check ins be removed with it
def delete_user(user_id):
    with connect() as connection:
        # delete users
        cursor = connection.execute(
            """
            DELETE FROM users
            WHERE id = ?
            """,
            (user_id,)
        )
        # Report whether one account was deleted
        return cursor.rowcount == 1

# profile fields shown in account settings
def get_user_profile(user_id):
    with connect() as connection:
        # profile fields
        row = connection.execute(
            "SELECT id, full_name, username, email, profession, address, consent_accepted FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
    return dict(row) if row else None


# Validate and save profile edits and optional password changes
def update_user_profile(user_id, username, full_name='', email='', profession='', address='', current_password='', new_password=''):
    import re
    # trim username and require a non empty value
    username = username.strip()
    if not username:
        raise ValueError('profile_username_required')
    # Require at least eight characters with uppercase, lowercase, a number and a symbol
    if new_password and not (len(new_password) >= 8 and re.search(r'[A-Z]', new_password)
            # re search
            and re.search(r'[a-z]', new_password) and re.search(r'[0-9]', new_password)
            and re.search(r'[^A-Za-z0-9]', new_password)):
        # error
        raise ValueError('password_weak')
    with connect() as connection:
        row = connection.execute('SELECT username, password_hash FROM users WHERE id = ?', (user_id,)).fetchone()
        # Stop if account can no longer be found
        if row is None:
            raise ValueError('profile_account_missing')
        # Require current password before changing login details
        credentials_changed = username != row['username'] or bool(new_password)
        if credentials_changed and not verify_password(current_password, row['password_hash']):
            # error if profile password incorrect
            raise ValueError('profile_password_incorrect')
        try:
            # Save profile fields and use the username if the name is blank
            connection.execute(
                'UPDATE users SET username=?, full_name=?, email=?, profession=?, address=? WHERE id=?',
                (username, full_name.strip() or username, email.strip(), profession.strip(), address.strip(), user_id))
            # Hash and save a new password only when one was supplied
            if new_password:
                connection.execute('UPDATE users SET password_hash=? WHERE id=?', (hash_password(new_password), user_id))
        # username that conflicts with an existing account
        except sqlite3.IntegrityError as error:
            raise ValueError('username_exists') from error
    return get_user_profile(user_id)

# save one questionnaire per user per day
def save_questionnaire(user_id, answer_labels, personal, work, overall):
    with connect() as connection:
        # look for questionnaire already saved today for this user
        existing = connection.execute(
            """
            SELECT id
            FROM questionnaire_responses
            WHERE user_id = ?
            AND date(created_at, 'localtime') = date('now', 'localtime')
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()
        answers = json.dumps(answer_labels)
        # overwrite today questionnaire instead of adding another
        if existing:
            connection.execute(
                """
                UPDATE questionnaire_responses
                SET created_at = CURRENT_TIMESTAMP,
                    answers_json = ?,
                    personal_burnout = ?,
                    work_burnout = ?,
                    cbi_score = ?
                WHERE id = ?
                """,
                (answers, personal, work, overall, existing['id'])
            )
        # insert the first questionnaire for today
        else:
            connection.execute(
                """
                INSERT INTO questionnaire_responses (user_id, answers_json, personal_burnout, work_burnout, cbi_score)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, answers, personal, work, overall)
            )

        # Refresh comparisons for check ins saved today
        check_ins = connection.execute(
            """
            SELECT id, wellbeing_score
            FROM check_ins
            WHERE user_id = ?
            AND date(created_at, 'localtime') = date('now', 'localtime')
            """, (user_id,)
        ).fetchall()

        # check in
        for check_in in check_ins:
            _record_cbi_comparison(connection,user_id,check_in["id"],check_in["wellbeing_score"])

    # notebook ready CSV up to date after every submission
    export_questionnaire_csv()

# store user weekly reminder choice
def set_questionnaire_reminders(user_id, enabled):
    with connect() as connection:
        # insert preference or update it if one already exists
        connection.execute(
            """
            INSERT INTO questionnaire_prefs (user_id, reminders_enabled) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET reminders_enabled = excluded.reminders_enabled
            """,
            (user_id, 1 if enabled else 0)
        )


# whether reminder is due
def questionnaire_reminder_due(user_id, days=7):
    with connect() as connection:
        # no reminder unless the user opted in
        pref = connection.execute(
            "SELECT reminders_enabled FROM questionnaire_prefs WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not pref or not pref['reminders_enabled']:
            return False
        # days elapsed since the most recent completed questionnaire
        row = connection.execute(
            """
            SELECT julianday('now') - julianday(MAX(created_at)) AS days
            FROM questionnaire_responses
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()
    return bool(row and row['days'] is not None and row['days'] >= days)


# saved response to CSV
def export_questionnaire_csv(path=None):
    # export in its own folder under data
    QUESTIONNAIRE_EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
    path = Path(path) if path else QUESTIONNAIRE_EXPORT_FOLDER / 'app_questionnaire_responses.csv'
    with connect() as connection:
        # select statement
        rows = connection.execute("SELECT user_id, created_at, answers_json FROM questionnaire_responses ORDER BY created_at").fetchall()
    # match columns
    header = ['Timestamp', 'Participant number'] + QUESTION_HEADERS
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            #  13 verbal English answers in item order
            answers = json.loads(row['answers_json'])
            writer.writerow([row['created_at'], row['user_id']] + answers)
    return path

# feedback card is due
def experience_feedback_due(user_id, interval_days):
    if interval_days == 0:
        return True
    # select user for the feedback
    with connect() as connection:
        # select statement
        row = connection.execute(
            """
            SELECT julianday('now') - julianday(
                COALESCE(p.last_shown_at, u.consent_accepted_at, CURRENT_TIMESTAMP)
            ) AS elapsed_days
            FROM users u
            LEFT JOIN experience_feedback_prompts p ON p.user_id = u.id
            WHERE u.id = ?
            """,(user_id,)
        ).fetchone()
    # return
    return (row is not None and row["elapsed_days"] is not None and row["elapsed_days"] >= interval_days)


# prompt even when user skips it
def mark_experience_feedback_shown(user_id):
    with connect() as connection:
        # insert feedback
        connection.execute(
            """
            INSERT INTO experience_feedback_prompts (user_id, last_shown_at)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE
            SET last_shown_at = CURRENT_TIMESTAMP
            """, (user_id,)
        )

# Save rating and optional comment
def save_experience_feedback(user_id, rating, comment):
    if rating not in range(1, 6):
        raise ValueError("Choose a rating from 1 to 5")
    # feedback length
    comment = comment.strip()
    if len(comment) > 500:
        raise ValueError("Keep feedback within 500 characters")
    # insert feedback to database for future improvements
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO experience_feedback (user_id, rating, comment)
            VALUES (?, ?, ?)
            """, (user_id, rating, comment)
        )