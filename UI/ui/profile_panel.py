# Import required libraries
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QLineEdit,QPushButton,QFrame
from UI.ui.account_widgets import AvatarButton, PasswordEdit, PasswordRequirementsBar
from UI.ui.translations import ENGLISH_TEXT,get_text

# Add profile labels and messages to shared wording
ENGLISH_TEXT.update({
 'profile_username_required':'Enter a username.',
 'profile_account_missing':'This account no longer exists. Please sign in again.',
 'profile_password_incorrect':'Enter your correct current password to change your username or password.',
 'profile_saved':'Your profile has been saved.',
 'profile_failed':'Your profile could not be saved. Please try again.',
 'profile_optional':'Optional details',
 'profile_details_note':'Only your username and password are required. Add other details if you wish.',
 'profile_full_name':'Full name (optional)', 'profile_email':'Email (optional)',
 'profile_profession':'Profession (optional)', 'profile_address':'Address (optional)',
 'profile_current_password':'Current password', 'profile_new_password':'New password (optional)',
 'profile_confirm_password':'Confirm new password',
 'profile_password_note':'Leave these fields blank to keep your password. Your current password is required when changing your username or password.',
 'profile_save':'Save profile', 'profile_tab':'Profile', 'preferences_tab':'Preferences',
 'profile_load_failed':'Your profile could not be loaded. Reopen settings to try again.',
 'delete_failed':'Your account could not be deleted. Please try again.',
 'account_busy':'Wait for the current recording or analysis to finish before changing your account.',
 'register_name_optional':'Full name (optional)',
})

# edit account details and request profile updates
class ProfilePanel(QWidget):
    # entered profile details to the main window for saving
    save_requested=Signal(dict)
    def __init__(self):
        super().__init__()
        self.setObjectName('profilePanel')
        self.setAttribute(Qt.WA_StyledBackground,True)

        # Track unsaved edits and account currently loaded
        self.is_dirty=False
        self._loading=False
        self.loaded_user_id=None
        self.current_language='English'
        self.labels=[]
        self.fields={}
        
        # main form layout
        layout=QVBoxLayout(self);layout.setContentsMargins(20,16,20,16);layout.setSpacing(12)

        # temporary success message above profile
        self.saved_notice = QLabel()
        self.saved_notice.setObjectName('profileSavedNotice')
        self.saved_notice.setWordWrap(False)
        self.saved_notice.hide()

        # Hide message after four seconds
        self.saved_timer = QTimer(self)
        self.saved_timer.setSingleShot(True)
        self.saved_timer.setInterval(4000)
        self.saved_timer.timeout.connect(self.saved_notice.hide)

        # profile avatar and account name together
        row=QHBoxLayout();self.avatar=AvatarButton();self.name=QLabel();self.name.setObjectName('sectionTitle')
        row.addWidget(self.avatar)
        row.addWidget(self.name)
        row.addStretch()

        # feedback at the top right
        row.addWidget(self.saved_notice)
        layout.addLayout(row)
        self.note=QLabel();self.note.setWordWrap(True);self.note.setObjectName('featureDescription');layout.addWidget(self.note)
        grid=QGridLayout();grid.setHorizontalSpacing(24);grid.setVerticalSpacing(8)
        for i,(key,text) in enumerate([('username','username'),('full_name','profile_full_name'),('email','profile_email'),('profession','profile_profession'),('address','profile_address')]):
            label=QLabel();field=QLineEdit();field.setMinimumHeight(38);label.setBuddy(field)
            self.labels.append((label,text));self.fields[key]=field
            # label above its field in a two-column grid
            row,col=divmod(i,2);grid.addWidget(label,row*2,col);grid.addWidget(field,row*2+1,col)
        layout.addLayout(grid)

        # password fields
        self.password_note=QLabel();self.password_note.setWordWrap(True);self.password_note.setObjectName('privacyNote');layout.addWidget(self.password_note)
        passwords=QGridLayout();passwords.setHorizontalSpacing(16)

        # three password fields
        for col,(key,text) in enumerate([('current_password','profile_current_password'),('new_password','profile_new_password'),('confirm_password','profile_confirm_password')]):
            label=QLabel();field=PasswordEdit();field.setMinimumHeight(40);label.setBuddy(field)
            self.labels.append((label,text));self.fields[key]=field;passwords.addWidget(label,0,col);passwords.addWidget(field,1,col)
        layout.addLayout(passwords)

        # requirements for new password
        self.password_bar = PasswordRequirementsBar(self.fields['new_password'])
        passwords.addWidget(self.password_bar, 2, 1)

        # existing password guidance visible
        self.password_hint = QLabel()
        self.password_hint.setObjectName('privacyNote')
        self.password_hint.setWordWrap(True)
        passwords.addWidget(self.password_hint, 3, 1)

        # save results and validation messages
        self.status=QLabel();self.status.setWordWrap(True);self.status.setObjectName('profileStatus');layout.addWidget(self.status)

        # button used to save profile
        self.save_button=QPushButton();self.save_button.setObjectName('primaryButton');self.save_button.setMinimumHeight(44)
        self.save_button.clicked.connect(self.submit);layout.addWidget(self.save_button);layout.addStretch()

        # Track changes made in any profile field
        for field in self.fields.values():
            field.textChanged.connect(self.mark_dirty)
        self.set_language('English')

    # Update page for selected language
    def set_language(self,language):
        self.current_language=language

        # Translate field labels and guidance text
        t=lambda key:get_text(language,key)
        for label,key in self.labels:label.setText(t(key))
        self.note.setText(t('profile_details_note'));self.password_note.setText(t('profile_password_note'))
        self.save_button.setText(t('profile_save'))
        self.password_bar.set_language(language)
        self.password_hint.setText(t('password_requirements_hint'))

        # refresh password visibility hints after language change
        for field in self.fields.values():
            if isinstance(field,PasswordEdit):field.refresh_eye()

    # account details into profile fields
    def set_profile(self,profile):
        # Mark start of loading profile
        self._loading=True
        self.saved_timer.stop()
        self.saved_notice.hide()
        self.loaded_user_id=profile.get("id")

        # Clear password fields
        self.clear_sensitive()

        # Go through saved profile details
        for key in ('username','full_name','email','profession','address'):
            self.fields[key].setText(str(profile.get(key) or ''))
        self.name.setText(profile.get('username',''))
        self.avatar.set_identity(profile.get('username',''))
        self.status.clear()

        # finish loading without marking
        self._loading=False
        self.is_dirty=False

    # profile password fields
    def clear_sensitive(self):
        for key in ('current_password','new_password','confirm_password'):self.fields[key].clear()

    # Check passwords and request a profile update
    def submit(self):
        # previous success message before saving again
        self.saved_timer.stop()
        self.saved_notice.hide()
        # current values from all fields
        values={key:field.text() for key,field in self.fields.items()}

        # new passwords differ
        if values['new_password']!=values.pop('confirm_password'):
            self.show_profile_notice(get_text(self.current_language, 'password_mismatch'))
            return
        
        # profile values for saving
        self.save_requested.emit(values)

    # success or error feedback
    def show_profile_notice(self, message, success=False):
        self.saved_timer.stop()
        self.status.clear()
        self.saved_notice.setText(message)
        self.saved_notice.setProperty('success', success)
        self.saved_notice.style().unpolish(self.saved_notice)
        self.saved_notice.style().polish(self.saved_notice)
        self.saved_notice.show()

        # message after four seconds
        self.saved_timer.start()

    # profile unsaved changes
    def mark_dirty(self):
        # mark changes made outside profile loading
        if not self._loading:
            self.is_dirty=True
