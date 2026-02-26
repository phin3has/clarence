import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class ProfileManager:
    """Manages user profiles for personalized trading."""

    def __init__(self, profile_dir: str = ".clarence"):
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.profile_path = self.profile_dir / "profile.json"

    def load_or_create_profile(self) -> dict:
        if self.profile_path.exists():
            with open(self.profile_path, "r") as f:
                profile = json.load(f)
            print(f"\nWelcome back, {profile.get('name', 'trader')}!\n")
            return profile
        return self._create_default_profile()

    def _create_default_profile(self) -> dict:
        return {
            "user_id": str(uuid.uuid4()),
            "name": None,
            "risk_appetite": "medium",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "session_count": 0,
        }

    def save_profile(self, profile: dict):
        profile["updated_at"] = datetime.now().isoformat()
        with open(self.profile_path, "w") as f:
            json.dump(profile, f, indent=2)
