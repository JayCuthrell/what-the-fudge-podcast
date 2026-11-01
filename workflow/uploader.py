import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import PipelineConfig

class YouTubeUploader:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.token_path = Path("token.json")

    def authenticate(self):
        creds = None
        # Load cached token if available
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), self.cfg.youtube_scopes)

        # Refresh or perform new handshake
        if not creds or not creds.valid:
            if not self.cfg.client_secrets_path.exists():
                raise FileNotFoundError(f"Missing OAuth secret file: {self.cfg.client_secrets_path}")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.cfg.client_secrets_path),
                self.cfg.youtube_scopes
            )
            creds = flow.run_local_server(port=0)
            
            # Save token for subsequent runs
            self.token_path.write_text(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    def upload(self, video_path: Path, title: str, description: str, privacy: str = "unlisted") -> str:
        youtube = self.authenticate()
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": privacy
            }
        }
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        return response["id"]

    def update_markdown_placeholder(self, filepath: Path, video_id: str) -> None:
        """Finds PLACEHOLDER strings in the 11ty markdown file and replaces them with the live YouTube ID."""
        if not filepath.exists():
            print(f"⚠ Could not find markdown file to update: {filepath}")
            return

        content = filepath.read_text(encoding="utf-8")
        
        # Target the specific shortcode and link structures
        updated_content = content.replace('slug="PLACEHOLDER"', f'slug="{video_id}"')
        updated_content = updated_content.replace('youtu.be/PLACEHOLDER', f'youtu.be/{video_id}')
        
        if content != updated_content:
            filepath.write_text(updated_content, encoding="utf-8")
            print(f"✓ Successfully updated 11ty markdown with YouTube ID: {video_id}")
        else:
            print("⚠ 'PLACEHOLDER' string not found in the markdown file. No changes made.")