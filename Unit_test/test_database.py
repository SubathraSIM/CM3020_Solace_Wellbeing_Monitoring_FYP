# Import required libraries
import tempfile
from datetime import datetime
from pathlib import Path
import UI.database.database as database

# Temporary database used only for unit testing
TEST_DATABASE_FOLDER = (Path(tempfile.gettempdir()) / "solace_database_tests")
# Set the path to the temporary database file
TEST_DATABASE_PATH = (TEST_DATABASE_FOLDER / "test_wellbeing_system.db")

# Create a test database before every test
def setup_function():
    # Create the test folder if needed
    TEST_DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)
    # Check whether the test database exists
    if TEST_DATABASE_PATH.exists():
        TEST_DATABASE_PATH.unlink()

    # temporary folder for these tests
    database.DATABASE_FOLDER = (TEST_DATABASE_FOLDER)
    # temporary database file
    database.DATABASE_PATH = (TEST_DATABASE_PATH)
    database.create_database()

# Delete temporary database after every test
def teardown_function():
    if TEST_DATABASE_PATH.exists():
        TEST_DATABASE_PATH.unlink()

# Helper function to create a sample audio check-in
def audio_result(score=60.0):
    # Return the sample check-in details
    return {
        "recording_type": "audio",
        "language": "English",
        "transcript": "I feel tired after my shift.",
        "transcript_english": "I feel tired after my shift.",
        "text_score": 40.0,
        "audio_score": 50.0,
        "vision_score": None,
        "strain_score": 40.0,
        "wellbeing_score": score,
        "phrase_english": "Today feels mixed",
        "explanation_english": "Your signals suggest a moderate wellbeing range.",
        "recommendation_english":
            "1. Take a short break.\n"
            "2. Drink some water.\n"
            "3. Rest after your shift.",
        "image_name": "wellbeing_mid.png",
        "blink_rate": None,
        "head_position": None,
        "speech_rate": 120.0,
        "disfluency_rate": 0.05,
        "lexical_variety": 0.72
    }

# Helper function to create a sample video check-in
def video_result(score=75.0):
    # Return the sample check-in details
    return {
        "recording_type": "video",
        "language": "English",
        "transcript": "My shift was busy but I feel okay.",
        "transcript_english": "My shift was busy but I feel okay.",
        "text_score": 30.0,
        "audio_score": 40.0,
        "vision_score": 35.0,
        "strain_score": 25.0,
        "wellbeing_score": score,
        "phrase_english": "Today feels steady",
        "explanation_english": "Your signals suggest a higher wellbeing range.",
        "recommendation_english":
            "1. Continue taking regular breaks.\n"
            "2. Stay hydrated.\n"
            "3. Make time to rest.",
        "image_name": "wellbeing_high.png",
        "blink_rate": 18.5,
        "head_position": "Centred",
        "speech_rate": 130.0,
        "disfluency_rate": 0.03,
        "lexical_variety": 0.78
    }

# Test case 1: Check that the database and required tables are created
def test_create_database():
    # database file was created
    assert TEST_DATABASE_PATH.exists()
    # Open connection to the test database
    with database.connect() as connection:
        # Collect database table names
        tables = {
            # Keep name from each returned row
            row["name"]
            # Run a query and read each matching row
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }
    assert "users" in tables
    assert "check_ins" in tables

# Test case 2: Check that all five supporting signal columns exist
def test_supporting_signal_columns():
    # Open connection to the test database
    with database.connect() as connection:
        # Collect the check-in column names
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(check_ins)")
        }

    assert "blink_rate" in columns
    assert "head_position" in columns
    assert "speech_rate" in columns
    assert "disfluency_rate" in columns
    assert "lexical_variety" in columns

# Test case 3: Check that passwords are hashed and verified correctly
def test_password_hashing():
    # sample password
    password = "StrongPassword1!"
    # Hash sample password
    stored_password = (database.hash_password(password))
    assert stored_password != password
    assert database.verify_password(password, stored_password)
    assert not database.verify_password("WrongPassword1!", stored_password)

# Test case 4: Check that a user can be created and duplicate usernames are rejected
def test_create_user_and_duplicate_username():
    # creating the first user
    first_result = database.create_user("Test User", "testuser", "StrongPassword1!")
    # creating another user with the same username
    duplicate_result = database.create_user("Another User", "testuser", "AnotherPassword1!")
    assert first_result is True
    assert duplicate_result is False

# Test case 5: Check correct and incorrect login details
def test_authenticate_user():
    # Create sample user for this test
    database.create_user("Test User", "testuser", "StrongPassword1!")
    # signing in with the correct details
    correct_user = database.authenticate_user("testuser", "StrongPassword1!")
    # signing in with the wrong password
    wrong_password = database.authenticate_user("testuser", "WrongPassword1!")
    # signing in with an unknown username
    unknown_user = database.authenticate_user("unknown", "StrongPassword1!")
    assert correct_user is not None
    assert correct_user["full_name"] == "Test User"
    assert correct_user["username"] == "testuser"
    assert wrong_password is None
    assert unknown_user is None

# Test case 6: Check that user consent is saved correctly
def test_save_consent():
    # Create sample user for this test
    database.create_user("Test User", "testuser", "StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser", "StrongPassword1!")
    assert user["consent_accepted"] is False
    # Save the user's consent
    database.save_consent(user["id"])
    # Read the user again after saving consent
    updated_user = database.authenticate_user("testuser", "StrongPassword1!")
    assert updated_user["consent_accepted"] is True

# Test case 7: Check that an audio check-in is saved and retrieved correctly
def test_save_audio_check_in():
    # Create sample user for this test
    database.create_user("Test User", "testuser", "StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser", "StrongPassword1!")
    # Save an audio check-in and keep its ID
    check_in_id = database.save_check_in(user["id"], audio_result())
    # Get today date in the saved date format
    today = datetime.now().strftime("%Y-%m-%d")
    # Read the user saved check-in for today
    saved = database.get_check_in_for_date(user["id"], today)
    assert check_in_id > 0
    assert saved is not None
    assert saved["input_type"] == "audio"
    assert saved["transcript"] == ("I feel tired after my shift.")
    assert saved["wellbeing_score"] == 60.0
    assert saved["vision_score"] is None
    assert saved["blink_rate"] is None
    assert saved["head_position"] is None
    assert saved["speech_rate"] == 120.0
    assert saved["disfluency_rate"] == 0.05
    assert saved["lexical_variety"] == 0.72

# Test case 8: Check that a video check-in stores all five supporting signals
def test_save_video_supporting_signals():
    # Create a sample user for this test
    database.create_user("Test User", "testuser", "StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser", "StrongPassword1!")
    # Save a video check-in for the test user
    database.save_check_in(user["id"], video_result())
    # Get today date in the saved date format
    today = datetime.now().strftime("%Y-%m-%d")
    # Read the user saved check-in for today
    saved = database.get_check_in_for_date(user["id"], today)
    assert saved["input_type"] == "video"
    assert saved["blink_rate"] == 18.5
    assert saved["head_position"] == "Centred"
    assert saved["speech_rate"] == 130.0
    assert saved["disfluency_rate"] == 0.03
    assert saved["lexical_variety"] == 0.78

# Test case 9: Check that the number of saved check-ins is correct
def test_check_in_count():
    # Create sample user for this test
    database.create_user("Test User","testuser","StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser","StrongPassword1!")
    assert database.get_check_in_count(user["id"]) == 0
    # Save an audio check-in with a score of 60
    database.save_check_in(user["id"],audio_result(60.0))
    # Save a video check-in with a score of 70
    database.save_check_in(user["id"], video_result(70.0))
    assert database.get_check_in_count(user["id"]) == 1

# Test case 10: Check that recent wellbeing scores are returned in the correct order
def test_recent_scores():
    # Create a sample user for this test
    database.create_user("Test User", "testuser", "StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser", "StrongPassword1!")
    # All three saves are on the same day, so they update the same record
    database.save_check_in(user["id"], audio_result(50.0))
    # Update today audio check-in with a score of 60
    database.save_check_in(user["id"], audio_result(60.0))
    # Update today audio check-in with a score of 70
    database.save_check_in(user["id"], audio_result(70.0))
    # Request up to two recent wellbeing scores
    scores = database.get_recent_scores(user["id"],limit=2)
    assert scores == [70.0]

# Test case 11: Check that the monthly history keeps the latest check-in for the day
def test_month_history():
    # Create sample user for this test
    database.create_user("Test User", "testuser", "StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser", "StrongPassword1!")
    # Save an audio check-in with a score of 55
    database.save_check_in(user["id"], audio_result(55.0))
    # Update today check-in with a video score of 75
    database.save_check_in(user["id"], video_result(75.0))
    # Read the user monthly check-in history
    history = database.get_month_check_ins(user["id"])
    assert len(history) == 1
    assert history[0]["score"] == 75.0
    assert history[0]["phrase"] == ("Today feels steady")

# Test case 12: Check that saved check-in dates are returned for the current month
def test_check_in_dates():
    # Create sample user for this test
    database.create_user("Test User", "testuser", "StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser", "StrongPassword1!")
    # Save a sample audio check-in
    database.save_check_in(user["id"], audio_result())
    # Get the current date and time
    now = datetime.now()
    # Read the check-in dates for this month
    dates = database.get_check_in_dates(user["id"], now.year, now.month)
    # Format today date to match the saved dates
    today = now.strftime("%Y-%m-%d")
    assert today in dates

# Test case 13: Check that users can only retrieve their own check-ins
def test_user_data_is_separate():
    # Create the first test user
    database.create_user("First User", "firstuser", "StrongPassword1!")
    # Create the second test user
    database.create_user("Second User", "seconduser", "StrongPassword2!")
    # Sign in as the first user
    first_user = database.authenticate_user("firstuser", "StrongPassword1!")
    # Sign in as the second user
    second_user = database.authenticate_user("seconduser", "StrongPassword2!")
    # Save a check-in for the first user only
    database.save_check_in(first_user["id"], audio_result())
    assert database.get_check_in_count(first_user["id"]) == 1
    assert database.get_check_in_count(second_user["id"]) == 0
    assert database.get_recent_scores(second_user["id"]) == []

# Test case 14: Check that a date with no check-in returns no result
def test_missing_check_in_date():
    # Create a sample user for this test
    database.create_user("Test User","testuser","StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser","StrongPassword1!")
    # check-in on a date with no saved record
    result = database.get_check_in_for_date(user["id"],"2000-01-01")
    assert result is None

# Test case 15: Check that previous strain (combined indicator) scores are returned oldest first, for the personal baseline calculation
def test_previous_strain_scores():
    # Create sample user for this test
    database.create_user("Test User","testuser","StrongPassword1!")
    # Sign in and get the test user's details
    user = database.authenticate_user("testuser","StrongPassword1!")
    # Same-day saves update the existing row, so the latest strain wins.
    database.save_check_in(user["id"], audio_result(50.0))
    # Save a video check-in with a score of 70
    database.save_check_in(user["id"], video_result(70.0))
    # user previous strain scores
    strain_scores = database.get_previous_strain_scores(user["id"])
    assert strain_scores == [25.0]