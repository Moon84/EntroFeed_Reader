import requests
from typing import ClassVar

from src.constants import USER_AGENT
from src.handlers import ContentRetrievalHandler
from src.models import EntryContent, FeedEntry


class RequestsContentRetriever(ContentRetrievalHandler):
    id: ClassVar[str] = "requests"
    headers: ClassVar[dict] = {"User-Agent": USER_AGENT}

    # requests does not implement the use_script option so we'll just ignore it
    async def get_html(self, url: str, use_script: bool = False) -> str:
        try:
            page = requests.get(url, headers=self.headers)
            if page.text == "":
                return
            else:
                return page.text
        except:
            return
