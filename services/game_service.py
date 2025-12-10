"""
Game Service
Oyun bilgilerini toplar ve dinamik olarak ajan/skin isimlerini eşleştirir
"""
import time
from typing import Optional, Dict, List, Tuple
from api.riot_api import RiotAPI
from services.valorant_api import ValorantAPIService
from utils.colors import Colors


def parse_rank(rank_data: Dict, current_season: str) -> str:
    """
    Rank verisini parse eder ve renkli rank string'i döndürür
    Args:
        rank_data: MMR endpoint'inden gelen veri
        current_season: Aktif sezon ID
    Returns:
        str: Renkli rank string (örn: "Platin 2 (45 RR)")
    """
    try:
        rank_colors = {
            range(0, 3): (Colors.RESET, "Derecesiz"),
            range(3, 6): ("\033[37;2m", "Demir"),
            range(6, 9): ("\033[38;5;173m", "Bronz"),
            range(9, 12): ("\033[38;5;251m", "Gümüş"),
            range(12, 15): ("\033[38;5;220m", "Altın"),
            range(15, 18): ("\033[38;5;123m", "Platin"),
            range(18, 21): ("\033[38;5;183m", "Elmas"),
            range(21, 24): ("\033[38;5;120m", "Yücelik"),
            range(24, 27): ("\033[38;5;203m", "Ölümsüzlük"),
            range(27, 28): ("\033[38;5;227m", "Radyant"),
        }

        rank_names = {
            0: "", 1: "", 2: "",
            3: "1", 4: "2", 5: "3",
            6: "1", 7: "2", 8: "3",
            9: "1", 10: "2", 11: "3",
            12: "1", 13: "2", 14: "3",
            15: "1", 16: "2", 17: "3",
            18: "1", 19: "2", 20: "3",
            21: "1", 22: "2", 23: "3",
            24: "1", 25: "2", 26: "3",
            27: "",
        }

        queue_skills = {}
        for key, value in rank_data.items():
            if key.lower() == "queueskills":
                queue_skills = value if value is not None else {}
                break

        competitive = {}
        for key, value in queue_skills.items():
            if key.lower() == "competitive":
                competitive = value if value is not None else {}
                break

        seasonal_info = {}
        for key, value in competitive.items():
            if key.lower() == "seasonalinfobyseasonid":
                seasonal_info = value if value is not None else {}
                break

        current_season_data = seasonal_info.get(current_season, {})

        if not current_season_data:
            if seasonal_info:
                latest_season = max(seasonal_info.keys())
                current_season_data = seasonal_info.get(latest_season, {})

        tier = 0
        rr = 0
        for key, value in current_season_data.items():
            if key.lower() == "competitivetier":
                tier = value if isinstance(value, int) else 0
            elif key.lower() == "rankedrating":
                rr = value if isinstance(value, int) else 0

        color = Colors.RESET
        rank_base = "?"
        for tier_range, (tier_color, tier_name) in rank_colors.items():
            if tier in tier_range:
                color = tier_color
                rank_base = tier_name
                break

        if tier == 0:
            return f"{color}Derecesiz{Colors.RESET}"
        elif tier == 27:
            return f"{color}Radyant{Colors.RESET}" if rr == 0 else f"{color}Radyant{Colors.RESET} {rr}"
        else:
            rank_num = rank_names.get(tier, "")
            return f"{color}{rank_base} {rank_num}{Colors.RESET}"

    except Exception as e:
        print(f"⚠️ Parse rank hatası: {e}")
        import traceback
        traceback.print_exc()
        return "?"


class GameService:
    """Oyun bilgilerini yöneten servis"""

    def __init__(self, riot_api: RiotAPI, valorant_api: ValorantAPIService):
        """
        Args:
            riot_api: RiotAPI instance
            valorant_api: ValorantAPIService instance
        """
        self.riot_api = riot_api
        self.valorant_api = valorant_api

        # Cache için dinamik veriler
        self._agents: Optional[Dict[str, str]] = None
        self._skins: Optional[Dict[str, str]] = None

        # Player stats servisi
        from services.player_stats_service import PlayerStatsService
        self.player_stats_service = PlayerStatsService(riot_api)

    def load_dynamic_data(self):
        """Ajan ve skin verilerini Valorant-API'den dinamik olarak yükler"""
        print("📥 Ajan ve skin verileri yükleniyor...")
        self._agents = self.valorant_api.get_agents()
        self._skins = self.valorant_api.get_vandal_skins()
        print(f"✅ {len(self._agents)} ajan, {len(self._skins)} Vandal skini yüklendi")
        print("💾 Cache aktif - rank bilgileri 15 dakika saklanır (rate limit önlemi)")

    def get_full_game_info(self, puuid: str) -> Optional[Dict]:
        """
        Oyunun tüm bilgilerini toplar (match details, loadouts, player names, agents, skins)
        Args:
            puuid: Player PUUID
        Returns:
            dict: Tüm oyun bilgileri veya None
        """
        # Dinamik verileri yükle (ilk çağrıda)
        if self._agents is None or self._skins is None:
            self.load_dynamic_data()

        # Match ID al
        match_id = self.riot_api.get_match_id(puuid)
        if not match_id:
            return None

        # Match details al
        match_details = self.riot_api.get_match_details(match_id)
        if not match_details:
            return None

        # Loadouts al
        loadouts = self.riot_api.get_match_loadouts(match_id)
        if not loadouts:
            return None

        # Oyuncu PUUID'lerini topla
        player_puuids = [player["Subject"] for player in match_details.get("Players", [])]

        # Oyuncu isimlerini al
        player_names = self.riot_api.get_player_names(player_puuids)
        if not player_names:
            return None

        # Aktif sezonu al (rank için gerekli)
        current_season = self.riot_api.get_current_season()

        # Oyuncu bilgilerini zenginleştir
        enriched_players = []
        for idx, player in enumerate(match_details.get("Players", [])):
            if idx > 0:
                time.sleep(1)  # Rank API için delay

            player_puuid = player.get("Subject", "")
            team_id = player.get("TeamID", "").capitalize()

            player_name_data = next(
                (p for p in player_names if p.get("Subject", "") == player_puuid),
                None
            )
            game_name = player_name_data.get("GameName", "Unknown") if player_name_data else "Unknown"
            tag_line = player_name_data.get("TagLine", "") if player_name_data else ""

            player_identity = player.get("PlayerIdentity", {})
            account_level = player_identity.get("AccountLevel")
            
            # HideAccountLevel true ise "Gizli" yaz
            if player_identity.get("HideAccountLevel", False):
                account_level = "Gizli"

            agent_uuid = loadouts.get("PlayerAgents", {}).get(player_puuid, "")
            agent_name = self._agents.get(agent_uuid.lower() if agent_uuid else "", "Unknown Agent")

            skin_uuid = loadouts.get("PlayerSkins", {}).get(player_puuid, "")
            skin_name = self._skins.get(skin_uuid.lower() if skin_uuid else "", "Standart Vandal")

            rank = "?"
            if current_season:
                try:
                    rank_data = self.riot_api.get_player_rank(player_puuid)
                    if rank_data:
                        rank = parse_rank(rank_data, current_season)
                    else:
                        print(f"⚠️ Rank verisi yok: {game_name}#{tag_line}")
                except Exception as e:
                    if "429" in str(e) or "too many" in str(e).lower():
                        rank = "Rate Limit"
                        print(f"⚠️ Rate limit: {game_name}#{tag_line}")
                    else:
                        print(f"⚠️ Rank hatası ({game_name}#{tag_line}): {e}")
                        rank = "?"
            else:
                print(f"⚠️ Sezon bilgisi bulunamadı")

            # KD ve HS bilgilerini al (arka planda, hata varsa geç)
            kd = "?"
            hs_percentage = "?"
            try:
                stats = self.player_stats_service.get_kd_hs_stats(player_puuid, match_count=5)
                if stats:
                    kd = stats.get("kd", "?")
                    hs_percentage = stats.get("hs_percentage", "?")
            except Exception as e:
                print(f"⚠️ KD/HS hatası ({game_name}#{tag_line}): {e}")

            enriched_players.append({
                "puuid": player_puuid,
                "game_name": game_name,
                "tag_line": tag_line,
                "team_id": team_id,
                "agent_name": agent_name,
                "agent_uuid": agent_uuid,
                "vandal_skin": skin_name,
                "skin_uuid": skin_uuid,
                "level": account_level,
                "rank": rank,
                "kd": kd,
                "hs_percentage": hs_percentage
            })

        return {
            "match_id": match_id,
            "match_details": match_details,
            "players": enriched_players
        }

    def get_agent_name(self, agent_uuid: str) -> str:
        """
        Agent UUID'den agent ismini döndürür
        Args:
            agent_uuid: Agent UUID
        Returns:
            str: Agent ismi
        """
        if self._agents is None:
            self.load_dynamic_data()
        return self._agents.get(agent_uuid.lower(), "Unknown Agent")

    def get_skin_name(self, skin_uuid: str) -> str:
        """
        Skin UUID'den skin ismini döndürür
        Args:
            skin_uuid: Skin UUID
        Returns:
            str: Skin ismi
        """
        if self._skins is None:
            self.load_dynamic_data()
        return self._skins.get(skin_uuid, "Standart Vandal")
