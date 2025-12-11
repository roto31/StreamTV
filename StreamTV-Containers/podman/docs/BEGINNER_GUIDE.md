# StreamTV Beginner Guide

**For Novice Users - No Technical Experience Required**

## Table of Contents
1. [What is StreamTV?](#what-is-streamtv)
2. [Basic Concepts](#basic-concepts)
3. [Installation](#installation)
4. [First Steps](#first-steps)
5. [Using the Web Interface](#using-the-web-interface)
6. [Common Tasks](#common-tasks)
7. [Basic Troubleshooting](#basic-troubleshooting)

---

## What is StreamTV?

StreamTV is a platform that creates TV channels from online video sources like YouTube and Archive.org. Think of it as your own personal TV network that you can watch in apps like Plex, Emby, or Jellyfin.

### What Can You Do With StreamTV?

- **Create TV Channels**: Turn YouTube playlists or Archive.org collections into continuous TV channels
- **Watch in Plex**: Add StreamTV as a "tuner" in Plex and watch channels like regular TV
- **Schedule Content**: Set up schedules so different shows play at different times
- **No Downloads Required**: Everything streams directly from the internet

### Simple Analogy

Imagine you have a TV remote that can tune to channels. StreamTV creates those channels for you, and each channel plays videos from YouTube or Archive.org continuously, just like a regular TV station.

---

## Basic Concepts

### Channel
A **channel** is like a TV station. It has a number (like "1980" or "1992") and a name (like "1980 Winter Olympics"). You tune to a channel to watch its content.

### Media Item
A **media item** is a single video. It could be a YouTube video or an Archive.org video. Each media item has:
- A title (what it's called)
- A URL (where to find it online)
- A duration (how long it is)

### Playlist
A **playlist** is a list of media items in a specific order. When a channel plays, it goes through the playlist from start to finish, then starts over.

### Schedule
A **schedule** is a more advanced way to organize content. It can include:
- Main content (the shows)
- Commercials (filler content)
- Specific times for things to play

### Collection
A **collection** is a group of related media items. For example, "1980 Olympics Opening Ceremony" might be a collection with multiple videos.

---

## Installation

### macOS Installation (Easiest Method)

1. **Download the Installation Script**
   - Open Terminal (Applications > Utilities > Terminal)
   - Navigate to the StreamTV folder

2. **Run the Installer**
   ```bash
   bash install_macos.sh
   ```
   - The script will:
     - Install Python and required tools
     - Set up StreamTV
     - Create a service that runs automatically
     - Start StreamTV

3. **Verify Installation**
   - Open a web browser
   - Go to: `http://localhost:8410`
   - You should see the StreamTV dashboard

### What Gets Installed?

- **StreamTV Server**: The main program that runs in the background
- **Web Interface**: A website you can access to manage StreamTV
- **Database**: Stores your channels, playlists, and settings
- **Background Service**: Keeps StreamTV running automatically

---

## First Steps

### Step 1: Access the Web Interface

1. Open your web browser
2. Go to: `http://localhost:8410`
3. You'll see the StreamTV dashboard

### Step 2: Check the Dashboard

The dashboard shows:
- **Total Channels**: How many channels you have
- **Total Media**: How many videos are available
- **Enabled Channels**: Channels that are currently active

### Step 3: View Existing Channels

1. Click **"Channels"** in the sidebar
2. You'll see a list of all your channels
3. Each channel shows:
   - Channel number
   - Channel name
   - Status (Enabled/Disabled)

---

## Using the Web Interface

### Navigation Sidebar

The sidebar on the left has these options:

- **Dashboard**: Overview of your system
- **Channels**: Manage TV channels
- **Player**: Watch channels in your browser
- **Import**: Add new channels from YAML files
- **Schedules**: View schedule files
- **Playouts**: See what's currently playing
- **Playlists**: Manage playlists
- **Collections**: Manage collections
- **Media Items**: View all videos
- **Settings**: Configure StreamTV

### Common Actions

#### View a Channel
1. Go to **Channels**
2. Click on a channel name
3. See details about that channel

#### Watch a Channel
1. Go to **Player**
2. Select a channel from the list
3. The video will start playing

#### Enable/Disable a Channel
1. Go to **Channels**
2. Find the channel
3. Click the toggle switch to enable or disable

---

## Common Tasks

### Task 1: Watch a Channel in Your Browser

1. Open StreamTV: `http://localhost:8410`
2. Click **"Player"** in the sidebar
3. Click on a channel card
4. The video will start playing automatically

### Task 2: Add a Channel from a YAML File

1. Go to **"Import"** in the sidebar
2. Click **"Choose File"** or drag a YAML file into the drop zone
3. Click **"Import Channel"**
4. Wait for the import to complete
5. The new channel will appear in your channels list

### Task 3: View What's Currently Playing

1. Go to **"Playouts"** in the sidebar
2. You'll see all channels and what's currently playing on each
3. Click on a channel to see more details

### Task 4: Check Channel Status

1. Go to **"Channels"**
2. Look at the status badges:
   - **Green "Enabled"**: Channel is active and streaming
   - **Red "Disabled"**: Channel is turned off

---

## Basic Troubleshooting

### Problem: Can't Access the Web Interface

**Symptoms**: Browser shows "Can't connect" or "Site can't be reached"

**Solutions**:
1. **Check if StreamTV is Running**
   - Open Terminal
   - Type: `ps aux | grep streamtv`
   - If you don't see StreamTV running, start it:
     ```bash
     cd "/path/to/StreamTV"
     source venv/bin/activate
     python -m streamtv.main
     ```

2. **Check the URL**
   - Make sure you're using: `http://localhost:8410`
   - Not `https://` (StreamTV uses HTTP, not HTTPS)

3. **Check the Port**
   - Make sure nothing else is using port 8410
   - Try restarting StreamTV

### Problem: Channel Won't Play

**Symptoms**: Channel shows but video doesn't start

**Solutions**:
1. **Check Channel Status**
   - Go to Channels
   - Make sure the channel is "Enabled"

2. **Check if Channel Has Content**
   - Go to Playouts
   - Click on the channel
   - See if it shows any schedule items

3. **Try Another Channel**
   - If other channels work, the problem is specific to that channel

### Problem: Videos Keep Buffering

**Symptoms**: Video plays but stops frequently to load

**Solutions**:
1. **Check Your Internet Connection**
   - StreamTV streams from the internet
   - Slow internet = buffering

2. **Check the Source**
   - YouTube videos usually work well
   - Archive.org videos might be slower

3. **Wait a Moment**
   - Sometimes the first video takes time to start
   - Subsequent videos should load faster

### Problem: Can't Add Plex Tuner

**Symptoms**: Plex can't find or connect to StreamTV

**Solutions**:
1. **Check HDHomeRun Settings**
   - Go to Settings in StreamTV
   - Make sure HDHomeRun is enabled

2. **Get the Discovery URL**
   - In StreamTV, go to the HDHomeRun section
   - Copy the discovery URL
   - Use this in Plex: `http://YOUR_COMPUTER_IP:8410/hdhomerun/discover.json`

3. **Check Firewall**
   - Make sure port 8410 is open
   - macOS: System Settings > Network > Firewall

### Problem: Import Failed

**Symptoms**: YAML file import shows an error

**Solutions**:
1. **Check File Format**
   - Make sure it's a valid YAML file
   - Check for typos or formatting errors

2. **Check File Location**
   - Make sure the file exists
   - Check file permissions

3. **Look at Error Message**
   - The error message usually tells you what's wrong
   - Common issues: missing fields, invalid URLs

---

## Getting More Help

### Next Steps

- **Ready for More?** → Read the [Intermediate Guide](./INTERMEDIATE_GUIDE.md)
- **Need Technical Details?** → Read the [Expert Guide](./EXPERT_GUIDE.md)
- **Having Problems?** → Use the [Troubleshooting Scripts](./TROUBLESHOOTING_SCRIPTS.md)

### Additional Resources

- [Quick Start Guide](./QUICKSTART.md) - Get up and running fast
- [API Documentation](./API.md) - For developers
- [Installation Guide](./INSTALLATION.md) - Detailed installation steps

---

## Glossary

- **API**: Application Programming Interface - how programs talk to each other
- **EPG**: Electronic Program Guide - the TV schedule you see in Plex
- **HLS**: HTTP Live Streaming - the technology used for video streaming
- **IPTV**: Internet Protocol Television - watching TV over the internet
- **M3U**: A file format for playlists
- **MPEG-TS**: A video format used for TV broadcasting
- **YAML**: Yet Another Markup Language - a file format for configuration
- **XMLTV**: A format for TV program guides

---

*Last Updated: 2025-01-28*

