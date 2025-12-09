import os
import sys
import time
import asyncio
import threading
import requests
from rich.console import Console

from api.local_client import LocalValorantClient
from api.riot_api import RiotAPI
from services.valorant_api import ValorantAPIService
from services.game_service import GameService
from utils.display import print_ascii_art, print_status, create_player_table
from utils.colors import Colors

console = Console()

# Web sunucusu ayarları
WEB_SERVER_ENABLED = True
WEB_SERVER_PORT = 5000


class ValorantTracker:
    def __init__(self):
        self.local_client = LocalValorantClient()
        self.riot_api = None
        self.valorant_api = ValorantAPIService()
        self.game_service = None
        self.previous_match_id = None
        self.websocket_task = None
        self.web_server_thread = None

    def start_web_server(self):
        """Web sunucusunu ayrı bir thread'de başlat"""
        if not WEB_SERVER_ENABLED:
            return
        
        def run_server():
            try:
                from web.app import app
                import logging
                log = logging.getLogger('werkzeug')
                log.setLevel(logging.ERROR)

                app.run(host='0.0.0.0', port=WEB_SERVER_PORT, debug=False, use_reloader=False)
            except Exception:
                pass
        
        self.web_server_thread = threading.Thread(target=run_server, daemon=True)
        self.web_server_thread.start()

    def send_to_web(self, game_info: dict):
        """Oyun bilgilerini web sunucusuna gönder"""
        if not WEB_SERVER_ENABLED:
            return
        
        try:
            requests.post(
                f'http://localhost:{WEB_SERVER_PORT}/api/game/update',
                json=game_info,
                timeout=2
            )
        except Exception:
            pass  # Web sunucusu henüz hazır değilse sessizce geç

    async def initialize(self) -> bool:
        if not self.local_client.read_lockfile():
            print_status("❌ Valorant çalışmıyor!", status_type="error")
            return False

        puuid = self.local_client.get_puuid()
        if not puuid:
            print_status("❌ Bağlantı hatası!", status_type="error")
            return False

        access_token, entitlements_token = self.local_client.get_tokens()
        if not access_token or not entitlements_token:
            print_status("❌ Bağlantı hatası!", status_type="error")
            return False

        client_version = self.valorant_api.get_client_version()
        if not client_version:
            print_status("❌ Bağlantı hatası!", status_type="error")
            return False

        self.riot_api = RiotAPI(access_token, entitlements_token, client_version)
        self.game_service = GameService(self.riot_api, self.valorant_api)

        return True

    async def websocket_message_handler(self, data: dict):
        """
        WebSocket mesajlarını işler
        Args:
            data: WebSocket mesajı
        """
        pass

    async def monitor_game(self):
        """Oyun durumunu sürekli kontrol eder"""
        try:
            while True:
                try:
                    game_info = self.game_service.get_full_game_info(self.local_client.puuid)

                    if game_info:
                        current_match_id = game_info["match_id"]

                        if current_match_id != self.previous_match_id:
                            if self.websocket_task and not self.websocket_task.done():
                                self.websocket_task.cancel()

                            print_status("🎮 Oyun bulundu!", clear_screen=True, status_type="success")
                            print()
                            console.print(create_player_table(game_info), justify="center")
                            
                            # Web sunucusuna gönder
                            self.send_to_web(game_info)

                            self.previous_match_id = current_match_id

                            self.websocket_task = asyncio.create_task(
                                self.local_client.connect_websocket(self.websocket_message_handler)
                            )
                    else:
                        if self.previous_match_id:
                            print_status("🏁 Oyun bitti!", clear_screen=True, status_type="warning")
                            if self.websocket_task and not self.websocket_task.done():
                                self.websocket_task.cancel()
                            self.previous_match_id = None
                        else:
                            print_status("🔍 Oyun bekleniyor...", clear_screen=True, status_type="info")

                    await asyncio.sleep(25)

                except Exception:
                    await asyncio.sleep(5)

        except KeyboardInterrupt:
            if self.websocket_task and not self.websocket_task.done():
                self.websocket_task.cancel()
            raise
        except asyncio.CancelledError:
            if self.websocket_task and not self.websocket_task.done():
                self.websocket_task.cancel()
            raise

    async def run(self):
        print("\033[H\033[J")
        print_ascii_art()

        if await self.initialize():
            self.start_web_server()
            await self.monitor_game()


def main():
    tracker = ValorantTracker()

    try:
        asyncio.run(tracker.run())
    except KeyboardInterrupt:
        print("\033[H\033[J")
        print_ascii_art()
        print_status("👋 İyi oyunlar!")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)


if __name__ == "__main__":
    main()
