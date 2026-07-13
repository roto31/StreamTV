"""macOS-specific credential input using AppleScript dialogs"""

import platform
import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def is_macos() -> bool:
    """Check if running on macOS"""
    return platform.system() == "Darwin"


def show_credentials_dialog(title: str, message: str) -> Optional[Tuple[str, str]]:
    """
    Show AppleScript dialog to get username and password.
    Returns (username, password) tuple or None if cancelled.
    """
    if not is_macos():
        logger.warning("AppleScript dialogs are only available on macOS")
        return None
    
    # AppleScript to show username/password dialog
    applescript = f'''
    tell application "System Events"
        activate
        set theResponse to display dialog "{message}" ¬
            with title "{title}" ¬
            with icon note ¬
            default answer "" ¬
            buttons {{"Cancel", "OK"}} ¬
            default button "OK" ¬
            with hidden answer
        set thePassword to text returned of theResponse
    end tell
    return thePassword
    '''
    
    try:
        # First, get username
        username_script = f'''
        tell application "System Events"
            activate
            set theResponse to display dialog "Enter your {title} username:" ¬
                with title "{title} - Username" ¬
                with icon note ¬
                default answer "" ¬
                buttons {{"Cancel", "OK"}} ¬
                default button "OK"
            set theUsername to text returned of theResponse
        end tell
        return theUsername
        '''
        
        result = subprocess.run(
            ['osascript', '-e', username_script],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.info("User cancelled username dialog")
            return None
        
        username = result.stdout.strip()
        if not username:
            logger.warning("Empty username provided")
            return None
        
        # Then, get password
        password_script = f'''
        tell application "System Events"
            activate
            set theResponse to display dialog "Enter your {title} password:" ¬
                with title "{title} - Password" ¬
                with icon note ¬
                default answer "" ¬
                buttons {{"Cancel", "OK"}} ¬
                default button "OK" ¬
                with hidden answer
            set thePassword to text returned of theResponse
        end tell
        return thePassword
        '''
        
        result = subprocess.run(
            ['osascript', '-e', password_script],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.info("User cancelled password dialog")
            return None
        
        password = result.stdout.strip()
        if not password:
            logger.warning("Empty password provided")
            return None
        
        return (username, password)
        
    except subprocess.TimeoutExpired:
        logger.error("Dialog timeout - user took too long to respond")
        return None
    except Exception as e:
        logger.error(f"Error showing credentials dialog: {e}")
        return None


def get_archive_org_credentials() -> Optional[Tuple[str, str]]:
    """
    Prompt user for Archive.org credentials using AppleScript dialog.
    Returns (username, password) tuple or None if cancelled/not macOS.
    """
    if not is_macos():
        logger.debug("Not running on macOS, skipping AppleScript dialog")
        return None
    
    message = (
        "Some Archive.org media requires authentication to view.\n\n"
        "Please enter your Archive.org credentials.\n\n"
        "These will be used to access restricted content."
    )
    
    credentials = show_credentials_dialog(
        title="Archive.org Authentication",
        message=message
    )
    
    if credentials:
        logger.info("Archive.org credentials obtained via AppleScript dialog")
        return credentials
    else:
        logger.info("Archive.org credentials not provided or dialog cancelled")
        return None


def store_credentials_in_keychain(service: str, username: str, password: str) -> bool:
    """
    Store credentials in macOS Keychain using security command.
    Returns True if successful, False otherwise.
    """
    if not is_macos():
        return False
    
    try:
        # Use security command to add to keychain
        # This will update if it already exists
        subprocess.run(
            [
                'security', 'add-internet-password',
                '-a', username,
                '-s', service,
                '-w', password,
                '-U'  # Update if exists
            ],
            capture_output=True,
            check=True,
            timeout=10
        )
        logger.info(f"Stored credentials in Keychain for {service}")
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to store credentials in Keychain: {e}")
        return False
    except Exception as e:
        logger.error(f"Error storing credentials in Keychain: {e}")
        return False


def get_credentials_from_keychain(
    service: str,
    account: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """
    Retrieve credentials from macOS Keychain.
    Returns (username, password) tuple or None if not found.

    When ``account`` is set, looks up that specific internet-password item
    (e.g. ``-a user@example.com -s archive.org``). Otherwise returns the
    first matching item for ``service``.
    """
    if not is_macos():
        return None

    find_args = ["security", "find-internet-password", "-s", service]
    if account:
        find_args[2:2] = ["-a", account]

    try:
        result = subprocess.run(
            [*find_args, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        password = result.stdout.strip()
        if not password:
            return None

        account_result = subprocess.run(
            [*find_args, "-g"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        username = account
        for line in account_result.stdout.split("\n"):
            if "acct" in line and "=" in line:
                parts = line.split("=")
                if len(parts) > 1:
                    username = parts[1].strip().strip('"')
                    break

        if username and password:
            return (username, password)

        return None

    except subprocess.CalledProcessError:
        return None
    except Exception as e:
        logger.error(f"Error retrieving credentials from Keychain: {e}")
        return None


def resolve_archive_org_login_email(
    keychain_username: Optional[str],
    preferred_email: Optional[str],
) -> Optional[str]:
    """
    Archive.org xauthn login requires the account email, not the screen name.
    Keychain often stores the screen name in ``acct``; prefer an explicit email.
    """
    if preferred_email and "@" in preferred_email:
        return preferred_email
    if keychain_username and "@" in keychain_username:
        return keychain_username
    return preferred_email or keychain_username

