"""
Riot API Endpoints
Match details, player info, ranks vb.
"""
import requests
import time
from typing import Optional, Dict, List
from config.settings import REGION, SHARD, VANDAL_UUID, VANDAL_SOCKET_ID
from utils.cache import cache

# urllib3 uyarılarını devre dışı bırak
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except (ImportError, AttributeError):
    pass


class RiotAPI:
    """Riot API ile iletişim için sınıf"""

    def __init__(self, access_token: str, entitlements_token: str, client_version: str):
        """
        Args:
            access_token: Bearer token
            entitlements_token: Entitlements JWT
            client_version: Client version
        """
        self.region = REGION
        self.shard = SHARD

        self.client_platform = "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjIyNjMxLjIyODgiLA0KCSJwbGF0Zm9ybUNoaXBzZXQiOiAiVW5rbm93biINCn0="

        self.headers = {
            "X-Riot-ClientPlatform": self.client_platform,
            "X-Riot-ClientVersion": client_version,
            "X-Riot-Entitlements-JWT": entitlements_token,
            "Authorization": f"Bearer {access_token}"
        }

    def get_match_id(self, puuid: str) -> Optional[str]:
        """
        Oyuncunun aktif maç ID'sini alır
        Valapidocs: GET /core-game/v1/players/{puuid}
        Args:
            puuid: Player PUUID
        Returns:
            str: Match ID veya None (oyunda değilse)
        """
        try:
            response = requests.get(
                f'https://glz-{self.region}-1.{self.shard}.a.pvp.net/core-game/v1/players/{puuid}',
                headers=self.headers,
                verify=False,
                timeout=5
            )

            response.raise_for_status()
            data = response.json()
            match_id = data.get("MatchID")

            return match_id

        except requests.exceptions.HTTPError:
            return None
        except Exception:
            return None

    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """
        Maç detaylarını alır
        Args:
            match_id: Match ID
        Returns:
            dict: Match details veya None
        """
        try:
            response = requests.get(
                f'https://glz-{self.region}-1.{self.shard}.a.pvp.net/core-game/v1/matches/{match_id}',
                headers=self.headers,
                verify=False
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"Maç detayları alma hatası: {e}")
            return None

    def get_match_loadouts(self, match_id: str) -> Optional[Dict]:
        """
        Maç loadout bilgilerini alır (agent, skin vb.)
        Args:
            match_id: Match ID
        Returns:
            dict: Loadouts veya None
        """
        try:
            response = requests.get(
                f'https://glz-{self.region}-1.{self.shard}.a.pvp.net/core-game/v1/matches/{match_id}/loadouts',
                headers=self.headers,
                verify=False
            )
            response.raise_for_status()
            loadouts_data = response.json()

            player_skins = {}
            player_agents = {}

            for loadout in loadouts_data.get("Loadouts", []):
                player_id = loadout.get("Loadout", {}).get("Subject", "")
                items = loadout.get("Loadout", {}).get("Items", {})

                # Ajan bilgisi (küçük harfe çevir - case-insensitive)
                agent_id = loadout.get("CharacterID", "")
                if agent_id:
                    player_agents[player_id] = agent_id.lower()

                # Vandal skin bilgisi - case-insensitive UUID kontrolü
                # Items dictionary'de key'ler büyük/küçük harf farklı olabilir
                vandal_data = None
                for item_key, item_value in items.items():
                    if item_key.lower() == VANDAL_UUID.lower():
                        vandal_data = item_value
                        break

                if vandal_data:
                    sockets = vandal_data.get("Sockets", {})

                    # Socket ID de case-insensitive kontrol et
                    socket_data = None
                    for socket_key, socket_value in sockets.items():
                        if socket_key.lower() == VANDAL_SOCKET_ID.lower():
                            socket_data = socket_value
                            break

                    if socket_data and "Item" in socket_data and "ID" in socket_data["Item"]:
                        skin_id = socket_data["Item"]["ID"]
                        player_skins[player_id] = skin_id.lower() if skin_id else ""

            loadouts_data["PlayerSkins"] = player_skins
            loadouts_data["PlayerAgents"] = player_agents

            return loadouts_data

        except Exception as e:
            print(f"Loadout bilgileri alma hatası: {e}")
            return None

    def get_player_names(self, puuids: List[str]) -> Optional[List[Dict]]:
        """
        Oyuncu isimlerini alır
        Args:
            puuids: Player PUUID listesi
        Returns:
            list: Oyuncu isimleri veya None
        """
        try:
            response = requests.put(
                f'https://pd.{self.shard}.a.pvp.net/name-service/v2/players',
                headers=self.headers,
                json=puuids,
                verify=False
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"Oyuncu isimleri alma hatası: {e}")
            return None

    def get_player_rank(self, puuid: str) -> Optional[Dict]:
        """
        Oyuncu rank bilgisini alır (cache kullanır)
        Args:
            puuid: Player PUUID
        Returns:
            dict: Rank bilgisi veya None
        """
        cached_rank = cache.get('ranks', puuid)
        if cached_rank:
            return cached_rank

        try:
            response = requests.get(
                f'https://pd.{self.shard}.a.pvp.net/mmr/v1/players/{puuid}',
                headers=self.headers,
                verify=False,
                timeout=10
            )

            if response.status_code == 429:
                print(f"⚠️ Rate limit! Oyuncu: {puuid[:8]}...")
                return None

            response.raise_for_status()
            rank_data = response.json()

            cache.set('ranks', puuid, rank_data)

            return rank_data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"⚠️ Too many requests - rate limit aşıldı")
            return None
        except Exception as e:
            print(f"Rank bilgisi alma hatası: {e}")
            return None

    def get_current_season(self) -> Optional[str]:
        """
        Aktif sezon ID'sini alır (cache kullanır)
        Returns:
            str: Season ID veya None
        """
        cached_season = cache.get('season_info', self.shard)
        if cached_season:
            return cached_season

        try:
            response = requests.get(
                f'https://shared.{self.shard}.a.pvp.net/content-service/v3/content',
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            content_data = response.json()

            season_id = None
            for season in content_data.get("Seasons", []):
                if season.get("IsActive") and season.get("Type") == "act":
                    season_id = season.get("ID")
                    break

            if season_id:
                cache.set('season_info', self.shard, season_id)

            return season_id

        except Exception as e:
            print(f"Sezon bilgisi alma hatası: {e}")
            return None

    def get_match_history(self, puuid: str, start_index: int = 0, end_index: int = 5, queue: str = "competitive") -> Optional[Dict]:
        """
        Oyuncunun maç geçmişini alır (cache kullanır)
        Args:
            puuid: Player PUUID
            start_index: Başlangıç indeksi (varsayılan 0)
            end_index: Bitiş indeksi (varsayılan 5)
            queue: Kuyruk tipi (varsayılan competitive)
        Returns:
            dict: Match history veya None
        """
        # Cache key oluştur
        cache_key = f"{puuid}_{start_index}_{end_index}_{queue}"
        cached_history = cache.get('match_history', cache_key)
        if cached_history:
            return cached_history

        try:
            response = requests.get(
                f'https://pd.{self.shard}.a.pvp.net/match-history/v1/history/{puuid}',
                params={
                    'startIndex': start_index,
                    'endIndex': end_index,
                    'queue': queue
                },
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            history_data = response.json()

            # Cache'e kaydet
            cache.set('match_history', cache_key, history_data)

            return history_data

        except Exception as e:
            print(f"Maç geçmişi alma hatası: {e}")
            return None

    def get_completed_match_details(self, match_id: str) -> Optional[Dict]:
        """
        Tamamlanmış maç detaylarını alır (istatistikler dahil, cache kullanır)
        Args:
            match_id: Match ID
        Returns:
            dict: Match details veya None
        """
        # Cache'de var mı kontrol et
        cached_details = cache.get('completed_match_details', match_id)
        if cached_details:
            return cached_details

        try:
            response = requests.get(
                f'https://pd.{self.shard}.a.pvp.net/match-details/v1/matches/{match_id}',
                headers=self.headers,
                verify=False,
                timeout=10
            )

            if response.status_code == 429:
                print(f"⚠️ Rate limit - maç detayları atlanıyor")
                return None

            response.raise_for_status()
            match_data = response.json()

            # Cache'e kaydet
            cache.set('completed_match_details', match_id, match_data)

            return match_data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"⚠️ Rate limit - maç detayları atlanıyor")
            return None
        except Exception as e:
            print(f"Tamamlanmış maç detayları alma hatası: {e}")
            return None
