"""
Local Valorant Client API
WebSocket bağlantısı ve lockfile yönetimi
"""
import os
import base64
import json
import ssl
import asyncio
import websockets
import requests
from typing import Optional, Dict, Tuple

# urllib3 uyarılarını devre dışı bırak
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except (ImportError, AttributeError):
    pass


class LocalValorantClient:
    """Local Valorant Client ile iletişim için sınıf"""

    def __init__(self):
        self.lockfile_data: Optional[Dict[str, str]] = None
        self.headers: Optional[Dict[str, str]] = None
        self.puuid: Optional[str] = None
        self.port: Optional[str] = None
        self.password: Optional[str] = None

    def read_lockfile(self) -> bool:
        """
        Valorant lockfile dosyasını okur
        Returns:
            bool: Başarılı ise True
        """
        try:
            localappdata = os.getenv('LOCALAPPDATA')
            if not localappdata:
                print("LOCALAPPDATA environment variable bulunamadı!")
                return False

            lockfile_path = os.path.join(localappdata, R'Riot Games\Riot Client\Config\lockfile')

            if not os.path.isfile(lockfile_path):
                print("Valorant çalışmıyor! Lütfen oyunu başlatın.")
                return False

            with open(lockfile_path, 'r') as file:
                data = file.read().split(':')
                keys = ['name', 'pid', 'port', 'password', 'protocol']
                self.lockfile_data = dict(zip(keys, data))
                self.port = self.lockfile_data['port']
                self.password = self.lockfile_data['password']

            auth = base64.b64encode(f'riot:{self.password}'.encode()).decode()
            self.headers = {
                'Authorization': f'Basic {auth}'
            }

            return True

        except Exception as e:
            print(f"Lockfile okuma hatası: {e}")
            return False

    def get_puuid(self) -> Optional[str]:
        """
        Oyuncunun PUUID'sini alır
        Returns:
            str: PUUID veya None
        """
        if not self.headers or not self.port:
            return None

        try:
            response = requests.get(
                f'https://127.0.0.1:{self.port}/entitlements/v1/token',
                headers=self.headers,
                verify=False
            )
            response.raise_for_status()
            self.puuid = response.json().get('subject')
            return self.puuid

        except Exception as e:
            print(f"PUUID alma hatası: {e}")
            return None

    def get_tokens(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Access token ve entitlements token alır
        Returns:
            Tuple[str, str]: (access_token, entitlements_token)
        """
        if not self.headers or not self.port:
            return None, None

        try:
            response = requests.get(
                f'https://127.0.0.1:{self.port}/entitlements/v1/token',
                headers=self.headers,
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            return data.get("accessToken"), data.get("token")

        except Exception as e:
            print(f"Token alma hatası: {e}")
            return None, None

    def check_game_status(self, debug: bool = False) -> bool:
        """
        Oyuncunun oyunda olup olmadığını kontrol eder
        Valapidocs: GET /core-game/v1/players/{puuid}
        Args:
            debug: Debug bilgisi yazdır
        Returns:
            bool: Oyunda ise True
        """
        if not self.headers or not self.port or not self.puuid:
            return False

        try:
            # Önce presence endpoint'ini dene (local)
            response = requests.get(
                f'https://127.0.0.1:{self.port}/chat/v4/presences',
                headers=self.headers,
                verify=False,
                timeout=5
            )
            response.raise_for_status()
            presences = response.json().get('presences', [])

            for presence in presences:
                if presence.get('puuid') == self.puuid:
                    private_str = presence.get('private', '')
                    if private_str:
                        try:
                            private_data = json.loads(base64.b64decode(private_str))
                            session_state = private_data.get('sessionLoopState', '')

                            if debug:
                                print(f"[DEBUG] sessionLoopState: {session_state}")
                                print(f"[DEBUG] private_data keys: {private_data.keys()}")

                            if session_state in ["INGAME", "PREGAME"]:
                                return True
                        except Exception as e:
                            if debug:
                                print(f"[DEBUG] Private data parse hatası: {e}")
                    else:
                        if debug:
                            print("[DEBUG] Private field boş!")

            return False

        except Exception as e:
            print(f"Oyun durumu kontrol hatası: {e}")
            return False

    async def connect_websocket(self, on_message_callback=None):
        """
        WebSocket bağlantısı kurar ve mesajları dinler
        Args:
            on_message_callback: Mesaj geldiğinde çağrılacak fonksiyon
        """
        if not self.port or not self.password:
            print("WebSocket için port veya password yok!")
            return

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        uri = f"wss://127.0.0.1:{self.port}"
        auth = base64.b64encode(f'riot:{self.password}'.encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}

        try:
            # Yeni websockets versiyonu için extra_headers
            try:
                async with websockets.connect(uri, ssl=ssl_context, extra_headers=headers) as websocket:
                    print("📡 WebSocket bağlantısı başarılı!")

                    while True:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)

                            if on_message_callback:
                                await on_message_callback(data)

                        except websockets.exceptions.ConnectionClosed:
                            print("❌ WebSocket bağlantısı kapandı!")
                            break

            except TypeError as e:
                if "extra_headers" in str(e):
                    # Eski websockets versiyonu için URI authentication
                    uri_with_auth = f"wss://riot:{self.password}@127.0.0.1:{self.port}"

                    async with websockets.connect(uri_with_auth, ssl=ssl_context) as websocket:
                        print("📡 WebSocket bağlantısı başarılı!")

                        while True:
                            try:
                                message = await websocket.recv()
                                data = json.loads(message)

                                if on_message_callback:
                                    await on_message_callback(data)

                            except websockets.exceptions.ConnectionClosed:
                                print("❌ WebSocket bağlantısı kapandı!")
                                break
                else:
                    raise e

        except Exception as e:
            print(f"⚠️ WebSocket bağlantı hatası: {e}")
