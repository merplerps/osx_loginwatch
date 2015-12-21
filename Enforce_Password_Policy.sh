#!/bin/sh

#Set password policy

pwpolicy -n /Local/Default -setglobalpolicy "minChars=12 requiresAlpha=1 requiresNumeric=1 requiresSymbol=1 usingHistory=10 passwordCannotBeName=1 maxFailedLoginAttempts=7 notGuessablePattern=1 maxMinutesUntilChangePassword=86400"

# Unload LaunchDaemon, if exists, in the event of re-running failed policy
launchctl unload /Library/LaunchDaemons/com.company.pwatcher.plist

# Load LaunchDaemon
launchctl load /Library/LaunchDaemons/com.company.pwatcher.plist