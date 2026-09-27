# Import required libraies
from UI.ui.account_widgets import AvatarButton
from UI.ui.settings_page import DeleteAccountDialog, LogoutDialog, ExperienceFeedbackDialog
from UI.database.database import experience_feedback_due, mark_experience_feedback_shown
from UI.database.database import create_database, get_user_profile, update_user_profile, delete_user
from PySide6.QtWidgets import QMessageBox
from pathlib import Path
from PySide6.QtWidgets import QDialog, QMainWindow, QStackedWidget
from UI.ui.assistant_page import AssistantPage
from UI.database.database import authenticate_user,create_user,save_consent
from UI.ui.check_in_page import CheckInPage
from UI.ui.consent_dialog import ConsentDialog,ThankYouDialog
from UI.ui.home_page import HomePage
from UI.ui.questionnaire_page import QuestionnairePage
from UI.ui.login_page import LoginPage
from UI.ui.register_page import RegisterPage
from UI.ui.settings_page import SettingsPage
from UI.ui.trends_page import TrendsPage

# feedback 30 days after
FEEDBACK_INTERVAL_DAYS = 30

# connect pages and manage current account
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Solace Healthcare Wellbeing System")
        self.setMinimumSize(1080,720)

        # stylesheet before creating pages
        theme = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
        image_directory = (Path(__file__).resolve().parents[1] / "images").as_posix()

        # image path placeholder and apply theme
        self.setStyleSheet(theme.replace("__SOLACE_IMAGES__", image_directory))
        self.showMaximized()

        # Create database tables if needed
        create_database()

        # no signed in account and English selected
        self.current_user = None
        self.pending_username = ""
        self.current_language = "English"

        # page stack and each application page
        self.pages = QStackedWidget()
        self.login_page = LoginPage()
        self.register_page = RegisterPage()
        self.home_page = HomePage()
        self.check_in_page = CheckInPage()
        self.trends_page = TrendsPage()
        self.assistant_page = AssistantPage()
        self.questionnaire_page = QuestionnairePage()
        self.settings_page = SettingsPage()

        # Register pages in the main stack
        for page in (self.login_page,self.register_page,self.home_page,self.check_in_page,self.trends_page,self.assistant_page,self.questionnaire_page,self.settings_page):
            self.pages.addWidget(page)
        self.setCentralWidget(self.pages)
        self.connect_pages()

        # Connect privacy deletion and profile saving actions
        self.settings_page.privacy_requested.connect(self.view_privacy)
        self.settings_page.delete_account_requested.connect(self.confirm_delete_account)
        self.settings_page.profile_panel.save_requested.connect(self.save_profile)

        # profile avatar open the profile tab
        for avatar in self.findChildren(AvatarButton):
            avatar.clicked.connect(self.show_profile)

    # Connect page actions to the main window
    def connect_pages(self):
        # Connect the login and registration actions
        self.login_page.login_button.clicked.connect(self.login_user)
        self.login_page.register_button.clicked.connect(self.show_register_page)
        self.login_page.language_changed.connect(self.change_language)
        self.register_page.create_button.clicked.connect(self.register_user)
        self.register_page.back_button.clicked.connect(self.show_login_page)

        # Connect navigation from home page
        self.home_page.check_in_requested.connect(self.show_check_in_page)
        self.home_page.trends_requested.connect(self.show_trends_page)
        self.home_page.assistant_requested.connect(self.show_assistant_page)
        self.home_page.settings_requested.connect(self.show_settings_page)
        self.home_page.logout_requested.connect(self.logout_user)

        # Connect navigation from check-in page
        self.check_in_page.home_requested.connect(self.show_home_page)
        self.check_in_page.logout_requested.connect(self.logout_user)
        self.check_in_page.sidebar.trends_requested.connect(self.show_trends_page)
        self.check_in_page.sidebar.assistant_requested.connect(self.show_assistant_page)
        self.check_in_page.sidebar.settings_requested.connect(self.show_settings_page)

        # Connect navigation from trends page
        self.trends_page.home_requested.connect(self.show_home_page)
        self.trends_page.check_in_requested.connect(self.show_check_in_page)
        self.trends_page.logout_requested.connect(self.logout_user)
        self.trends_page.sidebar.assistant_requested.connect(self.show_assistant_page)
        self.trends_page.sidebar.settings_requested.connect(self.show_settings_page)

        # Connect navigation from assistant page
        self.assistant_page.home_requested.connect(self.show_home_page)
        self.assistant_page.check_in_requested.connect(self.show_check_in_page)
        self.assistant_page.trends_requested.connect(self.show_trends_page)
        self.assistant_page.settings_requested.connect(self.show_settings_page)
        self.assistant_page.logout_requested.connect(self.logout_user)
        self.assistant_page.sidebar.assistant_requested.connect(self.show_assistant_page)

        # Connect navigation and language changes from settings
        self.settings_page.home_requested.connect(self.show_home_page)
        self.settings_page.check_in_requested.connect(self.show_check_in_page)
        self.settings_page.trends_requested.connect(self.show_trends_page)
        self.settings_page.sidebar.assistant_requested.connect(self.show_assistant_page)
        self.settings_page.logout_requested.connect(self.logout_user)
        self.settings_page.language_changed.connect(self.change_language)

        # navigation from the questionnaire page
        self.questionnaire_page.home_requested.connect(self.show_home_page)
        self.questionnaire_page.check_in_requested.connect(self.show_check_in_page)
        self.questionnaire_page.trends_requested.connect(self.show_trends_page)
        self.questionnaire_page.assistant_requested.connect(self.show_assistant_page)
        self.questionnaire_page.settings_requested.connect(self.show_settings_page)
        self.questionnaire_page.logout_requested.connect(self.logout_user)
        # questionnaire from every page sidebar
        for page in (self.home_page, self.check_in_page, self.trends_page, self.assistant_page, self.settings_page):
            page.sidebar.questionnaire_requested.connect(self.show_questionnaire_page)

    # Open the login page
    def show_login_page(self):
        self.register_page.clear_status()
        self.login_page.clear_status()
        self.login_page.set_language(self.current_language)
        self.pages.setCurrentWidget(self.login_page)

    # Open the register page
    def show_register_page(self):
        self.login_page.clear_status()
        self.register_page.clear_status()
        self.register_page.set_language(self.current_language)
        self.pages.setCurrentWidget(self.register_page)

    # Open the home page
    def show_home_page(self):
        self.pages.setCurrentWidget(self.home_page)

    # Open the check-in page
    def show_check_in_page(self):
        # Require a signed in user
        if self.current_user is None:
            return

        self.check_in_page.set_user(self.current_user["full_name"],self.current_user["id"])
        # open check in when the page can be reset
        if self.check_in_page.resume_page():
            self.pages.setCurrentWidget(self.check_in_page)

    # Open trends page
    def show_trends_page(self):
        if self.current_user is None:
            return

        # Load current user saved trends before showing page
        self.trends_page.set_user(self.current_user["full_name"],self.current_user["id"])
        self.trends_page.refresh_page()
        self.pages.setCurrentWidget(self.trends_page)

    # Open assistant page
    def show_assistant_page(self):
        if self.current_user is None:
            return

        # Set assistant user and language before opening chat
        self.assistant_page.set_user(self.current_user["full_name"],self.current_user["id"])
        self.assistant_page.set_language(self.current_language)
        self.assistant_page.refresh_page()
        self.pages.setCurrentWidget(self.assistant_page)

    # Open questionnaire page
    def show_questionnaire_page(self):
        if self.current_user is None:
            return
        # questionnaire page
        self.questionnaire_page.set_user(self.current_user["full_name"], self.current_user["id"])
        self.questionnaire_page.set_language(self.current_language)
        self.pages.setCurrentWidget(self.questionnaire_page)

    # Open settings page
    def show_settings_page(self):
        if self.current_user is None:
            return
        try:
            # current account details
            profile=get_user_profile(self.current_user["id"])
            panel=self.settings_page.profile_panel
            if profile:
                # Reload only for a different user or an unchanged form
                if panel.loaded_user_id!=profile["id"] or not panel.is_dirty:
                    panel.set_profile(profile)
                self.settings_page.profile_panel.save_button.setEnabled(True)

        # clear message if saved profile cannot be loaded
        except Exception:
            self.settings_page.profile_panel.status.setText(self.settings_page.t("profile_load_failed"))
            self.settings_page.profile_panel.save_button.setEnabled(False)
        self.settings_page.set_language(self.current_language)
        self.pages.setCurrentWidget(self.settings_page)

    # chosen language across all pages
    def change_language(self,language,):
        self.current_language = (language)
        self.login_page.set_language(language)
        self.register_page.set_language(language)
        self.home_page.set_language(language)
        self.check_in_page.set_language(language)
        self.trends_page.set_language(language)
        self.assistant_page.set_language(language)
        self.questionnaire_page.set_language(language)
        self.settings_page.set_language(language)

    # registration details and create the account
    def register_user(self):
        page = self.register_page
        page.clear_status()

        # account details while keeping password characters unchanged
        full_name = (page.name_input.text().strip())
        username = (page.username_input.text().strip())
        password = (page.password_input.text())
        confirm = (page.confirm_password_input.text())

        # all required fields are filled
        if (not username or not password or not confirm):
            page.show_status(page.t("register_empty"),"error")
            return

        # password meets the rules
        if not page.valid_password(password):
            page.show_status(page.t("password_weak"),"error")
            return

        # two passwords differ
        if password != confirm:
            page.show_status(page.t("password_mismatch"),"error")

            return

        # create account and check whether it failed
        if not create_user(full_name or username, username, password):
            page.show_status(page.t("username_exists"),"error")
            return

        # new username and finish registration
        self.pending_username = (username)
        page.show_status(page.t("account_created"),"success")
        self.finish_registration()

    # login page for new account
    def finish_registration(self):
        self.register_page.clear_fields()
        self.show_login_page()
        # Fill the username without selecting a field
        self.login_page.username_input.setText(self.pending_username)
        self.login_page.setFocus()
        self.login_page.show_status(self.login_page.t("account_created_login"),"success")
        self.pending_username = ""

    # login details and open account
    def login_user(self):
        page = self.login_page
        page.clear_status()
        # username and keep password exactly as entered
        username = (page.username_input.text().strip())
        password = (page.password_input.text())
        if (not username or not password):
            page.show_status(page.t("login_empty"),"error")
            return

        # username and password against saved account
        user = authenticate_user(username,password)
        # incorrect login details and clear password field
        if user is None:
            page.show_status(page.t("login_incorrect"),"error")
            page.clear_password()

            return

        # Store signed in user and update account pages
        self.current_user = user
        self.refresh_avatars()
        page.clear_password()
        self.home_page.set_user(user["full_name"])
        self.check_in_page.set_user(user["full_name"],user["id"])
        self.trends_page.set_user(user["full_name"],user["id"])
        self.assistant_page.set_user(user["full_name"],user["id"])

        # consent if it has not been accepted
        if not user["consent_accepted"]:
            if not self.show_consent_dialog():
                return

        self.pages.setCurrentWidget(self.home_page)

    # accept consent information
    def show_consent_dialog(self):
        dialog = ConsentDialog(self,self.current_language)
        result = dialog.exec()
        self.change_language(dialog.selected_language)

        # save consent only after the user accepts
        if (result == QDialog.DialogCode.Accepted):
            save_consent(self.current_user["id"])
            self.current_user["consent_accepted"] = True

            return True

        # decline message before leaving account
        ThankYouDialog(self.current_language,self).exec()
        self.logout_user(confirm=False)
        return False

    # Confirm logout and clear current session
    def logout_user(self, *, confirm=True):
        # account task is still running
        if self.account_busy():
            QMessageBox.information(self, "Solace", self.settings_page.t("account_busy"))
            return
        
        # confirmation only during normal logout
        if confirm and LogoutDialog(self.current_language, self).exec() != QDialog.Accepted:
            return
        # Stop recording page cannot be reset
        if not self.check_in_page.reset_page():
            return

        # feedback only during normal confirmed logout
        if confirm and self.current_user is not None:
            user_id = self.current_user["id"]
            try:
                # show the feedback section
                show_feedback = experience_feedback_due(user_id, FEEDBACK_INTERVAL_DAYS)
                if show_feedback:
                    mark_experience_feedback_shown(user_id)
            except Exception:
                # logout available if database is unavailable
                show_feedback = False
            # if show feedback show the card
            if show_feedback:
                ExperienceFeedbackDialog(user_id, self.current_language, self).exec()

        # Clear profile details credentials and page data for logout
        self.settings_page.profile_panel.set_profile({})
        self.current_user = None
        self.refresh_avatars()
        self.login_page.username_input.clear()
        self.login_page.clear_password()
        self.login_page.clear_status()
        self.check_in_page.reset_page()
        self.trends_page.set_user("",None)
        self.assistant_page.set_user("",None)

        #  clear chat when the assistant is idle
        if not self.assistant_page.worker_running():
            self.assistant_page.clear_chat()
        self.pages.setCurrentWidget(self.login_page)
        self.login_page.set_language(self.current_language)
        self.login_page.setFocus()

    # Update profile buttons for signed in user
    def refresh_avatars(self):
        # current username when refreshing all profile avatars
        username = self.current_user['username'] if self.current_user else ''
        for avatar in self.findChildren(AvatarButton):
            avatar.set_identity(username)

    # profile tab in settings
    def show_profile(self):
        self.show_settings_page()
        self.settings_page.account_tabs.setCurrentIndex(0)

    # privacy information for reading
    def view_privacy(self):
        ConsentDialog(self, self.current_language, view_only=True).exec()

    # Check whether recording or background work is active
    def account_busy(self):
        p=self.check_in_page
        # Check recording and background worker before account changes
        return (p.video_recording or p.audio_recording
                or (p.analysis_worker is not None and p.analysis_worker.isRunning())
                or (p.transcription_worker is not None and p.transcription_worker.isRunning())
                or self.assistant_page.worker_running())

    # edited profile and refresh account details
    def save_profile(self, values):
        panel=self.settings_page.profile_panel
        # Require a signed in user before saving
        if self.current_user is None:
            return
        # wait until current account tasks finish
        if self.account_busy():
            panel.show_profile_notice(self.settings_page.t('account_busy'))
            return
        # prevent another save while the profile update is running
        panel.save_button.setEnabled(False)
        try:
            # save profile and refresh the displayed account details
            user=update_user_profile(self.current_user['id'], **values)
            self.current_user.update(user)
            panel.set_profile(user)
            self.home_page.set_user(user['full_name'])
            self.refresh_avatars()
            panel.show_profile_notice(self.settings_page.t('profile_saved'), success=True)
        # validation message when edited details are invalid
        except ValueError as error:
            panel.show_profile_notice(self.settings_page.t(str(error)))
        except Exception:
            panel.show_profile_notice(self.settings_page.t('profile_failed'))
        # clear password fields and restore save button
        finally:
            panel.clear_sensitive()
            panel.save_button.setEnabled(True)

    # confirm and delete current account
    def confirm_delete_account(self):
        # Require a signed in user before deleting
        if self.current_user is None:
            return
        # current account tasks finish
        if self.account_busy():
            QMessageBox.information(self, 'Solace', self.settings_page.t('account_busy'))
            return
        # account deletion confirmation dialog
        dialog=DeleteAccountDialog(self.current_language,self)
        # Stop unless deletion was confirmed
        if dialog.exec()!=QDialog.Accepted:
            return
        try:
            # delete confirmed account from local database
            deleted=delete_user(self.current_user['id'])
        except Exception:
            deleted=False
        # warning if the account was not deleted
        if not deleted:
            QMessageBox.warning(self,'Solace',self.settings_page.t('delete_failed'))
            return
        # Reset check in page after the account is deleted
        self.check_in_page.reset_page()
        self.logout_user(confirm=False)

    # app being closed
    def closeEvent(self, event):
        # Keep app open while a task is running
        if self.account_busy():
            QMessageBox.information(self, 'Solace', self.settings_page.t('account_busy'))
            event.ignore()
            return
        # Clear recording state and sensitive fields before closing
        self.check_in_page.reset_page()
        self.settings_page.profile_panel.clear_sensitive()
        super().closeEvent(event)