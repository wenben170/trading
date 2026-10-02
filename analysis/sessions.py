from datetime import datetime, timezone

class SessionEngine:
    @staticmethod
    def get_current_session(dt: datetime = None) -> str:
        if dt is None:
            dt = datetime.now(timezone.utc)
        hour = dt.hour

        if 0 <= hour < 7:
            return "ASIAN"
        elif 7 <= hour < 13:
            return "LONDON"
        elif 13 <= hour < 21:
            return "NEW_YORK"
        else:
            return "ASIAN"