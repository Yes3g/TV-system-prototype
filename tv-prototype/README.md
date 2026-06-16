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

This opens the prototype directly as a local file. The server is not required.

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

The Local Archive TV channel uses copyright-free MP4 files from:

```text
/Users/Yes3g/Downloads
```

Those videos are not copied into the ZIP because they are very large. Keep them in Downloads, or update `data/db.json` and `data/db.js` if you move them.
