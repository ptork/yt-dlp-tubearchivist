# yt-dlp-tubearchivist

[yt-dlp](https://github.com/yt-dlp/yt-dlp) plugin for [tubearchivist](https://github.com/tubearchivist/tubearchivist).

## Installation

You can install this package with pip:

```
python3 -m pip install -U https://github.com/ptork/yt-dlp-tubearchivist/archive/main.zip
```

See [installing yt-dlp plugins](https://github.com/yt-dlp/yt-dlp#installing-plugins) for the other methods this plugin package can be installed.

## Usage

Supports downloading videos, channels and playlists.

Create a `tubearchivist.json` config file containing your tubearchivist hostnames and access tokens.

```json
[
  {
    "hostname": "tubearchivist.my-domain1.com",
    "access_token": "foiajh2398quy2a"
  },
  {
    "hostname": "tubearchivist.my-domain2.com",
    "access_token": "foiawjhf9oiwjhfaw"
  }
]
```

There are 2 ways to pass the config to the extractor. Either way make sure the file permissions are read only.

```sh
chmod 600 tubearchivist.json
```

### Method 1: environment variable

Set the `YT_DLP_TUBEARCHIVIST_CONFIG` environment variable. Then run the command:

```sh
YT_DLP_TUBEARCHIVIST_CONFIG=/path/to/config.json yt-dlp https://tubearchivist.my-domain1.com/video/123
```

### Method 2: standard locations

Place a `tubearchivist.json` in 1 of the following locations:

- Same location as `tubearchivist.py`
- `XDG_CONFIG_HOME/yt-dlp/tubearchivist.json`
- `/etc/yt-dlp/tubearchivist.json`

Then run the command:

```sh
yt-dlp https://tubearchivist.my-domain1.com/video/123
```

# License

MIT
