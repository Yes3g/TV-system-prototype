# NetVision Prototype

## Start

Best option, double-click:

```text
NetVision.app
```

This starts the local server in the background and opens the prototype in your browser.

Always-works option, double-click:

```text
index.html
```

This opens the prototype directly as a local file. The server is not required. This is also the recommended option for iOS.

Terminal option, double-click:

```text
Start NetVision.command
```

The terminal launcher starts a local server, chooses an available port, and opens the prototype in your browser.

Keep the terminal window open while using NetVision. Close it or press `Ctrl+C` to stop the server.

## Manual Start

From this folder:

```bash
python3 start_server.py
```

## Data

The prototype uses a JSON database:

```text
data/db.json
```

It contains users, channels, programs, episodes, media assets, schedule items, genres, and watch history.

## Local Video Files

For a fully portable package, put the copyright-free MP4 files into:

```text
tv-prototype/media/
```

Use the exact filenames listed in `media/PUT_VIDEOS_HERE.txt`.

For a clearer source overview, see:

```text
VIDEO_SOURCES.md
```

The videos are not copied into the ZIP because they are very large. If the media files are missing, NetVision will still load and use sample fallback videos.

## iOS

Use `index.html`. It is a standalone file with the app, styling, database, and subtitle data embedded inside it.

For the copyright-free MP4 files, keep the same structure:

```text
tv-prototype/
  index.html
  media/
    service-mbrs-ntscrm-00021068-00021068.mp4
    movio-moviola-176-r1.mp4
    ...
```

Some iOS apps restrict local video access. If that happens, the app still works and uses sample fallback videos.
