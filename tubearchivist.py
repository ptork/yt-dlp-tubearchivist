import os
import json
from pathlib import Path
from yt_dlp.extractor.common import InfoExtractor

DEFAULT_CONFIG_PATHS = [
  Path(os.path.dirname(__file__)) / "tubearchivist.json",
  Path.home() / ".config" / "yt-dlp" / "tubearchivist.json",
  Path("/etc/yt-dlp/tubearchivist.json")
]

config_path = os.getenv('YT_DLP_TUBEARCHIVIST_CONFIG')
if not config_path:
  try:
    config_path = next(path for path in DEFAULT_CONFIG_PATHS if path.exists())
  except StopIteration:
    raise ValueError(f"Config file not found in any of: {[str(p) for p in DEFAULT_CONFIG_PATHS]}")

try:
  config = json.loads(config_path.read_text())
except json.JSONDecodeError:
  raise ValueError(f"Invalid JSON in config file: {config_path}")

HOSTNAME_TO_TOKEN = {entry["hostname"]: entry["access_token"] for entry in config}
HOSTNAME_PATTERN = '|'.join(map(lambda h: h.replace('.', r'\.'), HOSTNAME_TO_TOKEN))

class TubeArchivistPluginIE(InfoExtractor):
  _WORKING = True
  _VALID_URL = rf"^(https?://(?:{HOSTNAME_PATTERN})(?::\d+)?)/(?P<type>video|channel|playlist)/(?P<id>[\w-]+)"
  
  #########################
  ######## Helpers ########
  #########################
  
  def _api_call(self, url, id, token, type):
    self.to_screen(f'Downloading {type} metadata from {url}')
    headers = {'Authorization': f'Token {token}', 'Accept': 'application/json'}
    json_data = self._download_json(
      url,
      id,
      headers=headers,
      note=f'Downloading {type} metadata'
    )
    return json_data

  def _parse_channel(self, base_url, json):
    result = {
      '_type': 'playlist',
      'id': json['channel_id'],
      'title': json['channel_name'],
      'channel': json['channel_name'],
      'channel_id': json['channel_id'],
      'channel_url': f"{base_url}/channel/{json['channel_id']}/",
      'description': json['channel_description'],
      'channel_follower_count': json['channel_subs'],
      'tags': json['channel_tags'],
      'modified_date': json['channel_last_refresh'].replace('-',''),
      'view_count': json['channel_views'],
      'thumbnail': f"{base_url}{json['channel_thumb_url']}",
      'channel_banner_url': f"{base_url}/{json['channel_banner_url']}",
      'channel_url': f"{base_url}/channel/{json['channel_id']}",
      'webpage_url': f"{base_url}/channel/{json['channel_id']}"
    }
    return result

  def _parse_video(self, base_url, json):
    channel_data = self._parse_channel(base_url, json['channel'])
    
    media_url = f"{base_url}{json['media_url']}"
  
    result = {
      '_type': 'video',
      'id': json['youtube_id'],
      'title': json['title'],
      'url': media_url,
      'ext': 'mp4',
      'format': 'mp4',
      'player_url': media_url,
      'duration': json['player']['duration'],
      'thumbnail': f"{base_url}{json['vid_thumb_url']}",
      'description': json['description'],
      'upload_date': json['published'].replace('-', ''),
      'view_count': json['stats']['view_count'],
      'like_count': json['stats']['like_count'],
      'dislike_count': json['stats']['dislike_count'],
      'tags': json['tags'],
      'categories': json['category'],
      'webpage_url': f"{base_url}/video/{json['youtube_id']}/",
      'filesize': json['media_size'],
      'channel': channel_data['channel'],
      'channel_id': channel_data['channel_id'],
      'channel_url': channel_data['channel_url'],
      'uploader': channel_data['channel'],
      'uploader_id': channel_data['channel_id'],
    }

    video_stream = next((s for s in json['streams'] if s['type'] == 'video'), None)
    audio_stream = next((s for s in json['streams'] if s['type'] == 'audio'), None)

    if video_stream:
      result.update({
        'width': video_stream['width'],
        'height': video_stream['height'],
        'resolution': f'{video_stream["width"]}x{video_stream["height"]}',
        'vcodec': video_stream['codec'],
        'vbr': video_stream['bitrate'] / 1000,
      })
  
    if audio_stream:
      result.update({
        'acodec': audio_stream['codec'],
        'abr': audio_stream['bitrate'] / 1000,
      })
    
    return result

  #########################
  ###### Extractors #######
  #########################

  def _extract_playlist(self, playlist_id, base_url, token):
    playlist_url = f"{base_url}/api/playlist/{playlist_id}/"
    playlist_json = self._api_call(playlist_url, playlist_id, token, 'playlist')
  
    channel_id = playlist_json['data']['playlist_channel_id']
  
    channel_url = f"{base_url}/api/channel/{channel_id}/"
    channel_json = self._api_call(channel_url, channel_id, token, 'channel')
    
    playlist_video = f"{base_url}/api/playlist/{playlist_id}/video/"
    playlist_video_json = self._api_call(playlist_video, playlist_id, token, 'playlist videos')

    entries = [
      self._extract_video(entry['youtube_id'], base_url, token)
      for entry in playlist_video_json['data']
    ]

    return {
      '_type': 'playlist',
      'id': playlist_id,
      'title': playlist_json['data']['playlist_name'],
      'description': playlist_json['data']['playlist_description'],
      'thumbnail': f"{base_url}{playlist_json['data']['playlist_thumbnail']}",
      **self._parse_channel(base_url, channel_json['data']),
      'entries': entries,
    }

  def _extract_channel(self, channel_id, base_url, token):
    self.to_screen('Extracting channel with ID "%s" from %s' % (channel_id, base_url))
    channel_url = f"{base_url}/api/channel/{channel_id}/"
    channel_videos_url = f"{base_url}/api/channel/{channel_id}/video/"
  
    channel_json = self._api_call(channel_url, channel_id, token, 'channel')
    videos_json = self._api_call(channel_videos_url, channel_id, token, 'channel videos')
  
    result = {
      **self._parse_channel(base_url, channel_json['data']),
      'entries': [self._parse_video(base_url, video) for video in videos_json['data']]
    }
    
    self.to_screen(f'Found {len(videos_json["data"])} videos in channel "{channel_json["data"]["channel_name"]}"')
    return result

  def _extract_video(self, video_id, base_url, token):
    self.to_screen('Extracting video with ID "%s" from %s' % (video_id, base_url))
    api_url = f"{base_url}/api/video/{video_id}/"
    json = self._api_call(api_url, video_id, token, 'video')
    return self._parse_video(base_url, json['data'])

  #########################
  ###### Entrypoint #######
  #########################
  
  def _real_extract(self, url):
    match = self._match_valid_url(url)
    url_type = match.group("type")
    id = match.group("id")
    base_url = match.group(1)  # Now captures http(s)://hostname(:port)
    hostname = base_url.split('://')[1].split(':')[0]  # Extract hostname for token lookup
    token = HOSTNAME_TO_TOKEN[hostname]

    self.to_screen(f'Parsed {url_type} with ID "{id}" from {base_url}')

    extract_methods = {
      'video': self._extract_video,
      'playlist': self._extract_playlist,
      'channel': self._extract_channel,
    }

    if url_type not in extract_methods:
      raise ValueError(f"Unknown URL type: {url_type}")

    return extract_methods[url_type](id, base_url, token)