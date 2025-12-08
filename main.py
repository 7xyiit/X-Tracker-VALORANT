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
                # Flask loglarını kapat (sadece önemli hatalar)
                log = logging.getLogger('werkzeug')
                log.setLevel(logging.ERROR)
                
                app.run(host='0.0.0.0', port=WEB_SERVER_PORT, debug=False, use_reloader=False)
            except Exception as e:
                print_status(f"⚠️ Web sunucusu başlatılamadı: {e}", status_type="error")
        
        self.web_server_thread = threading.Thread(target=run_server, daemon=True)
        self.web_server_thread.start()
        print_status(f"🌐 Web sunucusu başlatıldı: http://localhost:{WEB_SERVER_PORT}", status_type="success")

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
        print_status("🔍 Valorant kontrol ediliyor...", status_type="info")

        if not self.local_client.read_lockfile():
            print_status("❌ Valorant çalışmıyor! Lütfen oyunu başlatın.", status_type="error")
            return False

        print_status("✅ Lockfile başarıyla okundu!", status_type="success")

        puuid = self.local_client.get_puuid()
        if not puuid:
            print_status("❌ PUUID alınamadı!", status_type="error")
            return False

        print_status(f"🆔 PUUID: {puuid[:8]}...", status_type="success")

        access_token, entitlements_token = self.local_client.get_tokens()
        if not access_token or not entitlements_token:
            print_status("❌ Token alınamadı!", status_type="error")
            return False

        client_version = self.valorant_api.get_client_version()
        if not client_version:
            print_status("❌ Client version alınamadı!", status_type="error")
            return False

        print_status(f"🔧 Client Version: {client_version}", status_type="info")

        self.riot_api = RiotAPI(access_token, entitlements_token, client_version)
        self.game_service = GameService(self.riot_api, self.valorant_api)

        print_status("✅ Tracker başlatıldı!", status_type="success")
        return True

    async def websocket_message_handler(self, data: dict):
        """
        WebSocket mesajlarını işler
        Args:
            data: WebSocket mesajı
        """
        if data.get("eventType") == "Update":
            print_status("🔄 Oyun durumu güncellendi!", status_type="info")

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

                            print_status("🎮 Yeni oyun tespit edildi!", clear_screen=True, status_type="success")
                            print_status("📊 Oyuncu bilgileri yükleniyor...", status_type="info")
                            print_status("✨ Tablo hazırlanıyor...\n", status_type="info")

                            console.print(create_player_table(game_info))
                            
                            # Web sunucusuna gönder
                            self.send_to_web(game_info)

                            self.previous_match_id = current_match_id

                            self.websocket_task = asyncio.create_task(
                                self.local_client.connect_websocket(self.websocket_message_handler)
                            )
                    else:
                        if self.previous_match_id:
                            print_status("🏁 Oyun bitti! Yeni oyun bekleniyor...", clear_screen=True, status_type="warning")
                            if self.websocket_task and not self.websocket_task.done():
                                self.websocket_task.cancel()
                            self.previous_match_id = None
                        else:
                            print_status("🔍 Oyun bekleniyor...", clear_screen=True, status_type="info")
                            print_status("💡 Valorant'ı açıp bir oyuna girdiğinizde bilgiler otomatik görüntülenecek.", status_type="info")

                    await asyncio.sleep(25)

                except Exception as e:
                    print_status(f"⚠️ Hata oluştu: {e}", status_type="error")
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
        print_status("🎯 VALORANT TRACKER BAŞLATILIYOR...", clear_screen=True, status_type="info")

        if await self.initialize():
            # Web sunucusunu başlat
            self.start_web_server()
            time.sleep(2)
            await self.monitor_game()
        else:
            print_status("❌ Tracker başlatılamadı!", status_type="error")


def main():
    tracker = ValorantTracker()

    try:
        asyncio.run(tracker.run())
    except KeyboardInterrupt:
        print_status("👋 Program kapatılıyor...", clear_screen=True, status_type="warning")
        print_status("✨ İyi oyunlar!", status_type="success")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)


if __name__ == "__main__":
    main()
