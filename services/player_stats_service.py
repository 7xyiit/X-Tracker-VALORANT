"""
Player Statistics Service
Son 5 maçtan istatistikleri hesaplar
"""
import time
from typing import Dict, List, Optional
from api.riot_api import RiotAPI
from utils.cache import cache


class PlayerStatsService:
    """Oyuncu istatistiklerini hesaplayan servis"""

    def __init__(self, riot_api: RiotAPI):
        self.riot_api = riot_api

    def get_player_stats(self, puuid: str, current_map_id: str = "") -> Optional[Dict]:
        """
        Oyuncunun o haritadaki son 5 rekabetçi maçından istatistiklerini hesaplar
        Args:
            puuid: Player PUUID
            current_map_id: O anki haritanın ID'si (harita bazlı winrate için)
        Returns:
            dict: İstatistikler veya None
        """
        # Son maçları al (o haritadan 5 maç bulmak için geniş arama)
        match_history = self.riot_api.get_match_history(puuid, start_index=0, end_index=15, queue="competitive")
        if not match_history:
            return None

        matches = match_history.get("History", [])
        if not matches:
            return None

        # Harita bazlı roundları topla
        map_specific_rounds = []
        map_match_count = 0

        for idx, match in enumerate(matches):
            match_id = match.get("MatchID")
            if not match_id:
                continue

            # Rate limit önlemi: Her maç detayı arasında delay
            if idx > 0:
                time.sleep(0.5)

            match_details = self.riot_api.get_completed_match_details(match_id)
            if not match_details:
                continue

            # Harita bilgisini al - API'den matchInfo.mapId field'ı
            match_map_path = match_details.get("matchInfo", {}).get("mapId", "")

            # MapID path formatında geliyor: /Game/Maps/Pitt/Pitt
            # Path'ten harita ismini çıkar: pitt
            if match_map_path and "/" in match_map_path:
                match_map_id = match_map_path.split("/")[-1].lower()
            else:
                match_map_id = match_map_path.lower() if match_map_path else ""

            # Sadece aynı haritadaki maçları al
            if current_map_id and match_map_id != current_map_id:
                continue

            # Harita eşleşti, maç sayısını artır
            map_match_count += 1
            if map_match_count > 5:
                break  # İlk 5 maç yeterli

            round_results = match_details.get("roundResults", [])

            # Oyuncunun hangi takımda olduğunu bul
            players = match_details.get("players", [])
            player_team = None

            for player in players:
                if player.get("subject") == puuid:
                    player_team = player.get("teamId")
                    break

            if not player_team:
                continue

            # Round results'lara oyuncu bilgisini ekle
            for round_data in round_results:
                round_data["playerTeam"] = player_team
                map_specific_rounds.append(round_data)

        # Eğer harita bazlı round yoksa boş stats dön
        if not map_specific_rounds:
            return {
                "site_push_winrate": {
                    "A": {"winrate": 0.0, "wins": 0, "total": 0},
                    "B": {"winrate": 0.0, "wins": 0, "total": 0},
                    "C": {"winrate": 0.0, "wins": 0, "total": 0}
                },
                "retake_winrate": {"winrate": 0.0, "wins": 0, "total": 0},
                "save_rate": {"rate": 0.0, "survived": 0, "total": 0}
            }

        # İstatistikleri hesapla (harita bazlı roundlardan)
        stats = {
            "site_push_winrate": self._calculate_site_push_winrate(map_specific_rounds),
            "retake_winrate": self._calculate_retake_winrate(map_specific_rounds),
            "save_rate": self._calculate_save_rate(map_specific_rounds, puuid)
        }

        return stats

    def _calculate_site_push_winrate(self, rounds: List[Dict]) -> Dict:
        """
        A/B site push winrate hesaplar
        Args:
            rounds: Round results listesi
        Returns:
            dict: Site bazlı kazanma oranları
        """
        site_stats = {
            "A": {"wins": 0, "total": 0},
            "B": {"wins": 0, "total": 0},
            "C": {"wins": 0, "total": 0}
        }

        for round_data in rounds:
            plant_site = round_data.get("plantSite", "")
            if not plant_site or plant_site not in ["A", "B", "C"]:
                continue

            winning_team = round_data.get("winningTeam", "")
            player_team = round_data.get("playerTeam", "")

            site_stats[plant_site]["total"] += 1

            # Eğer oyuncunun takımı kazandıysa
            if winning_team == player_team:
                site_stats[plant_site]["wins"] += 1

        # Winrate hesapla
        winrates = {}
        for site, stats in site_stats.items():
            if stats["total"] > 0:
                winrate = (stats["wins"] / stats["total"]) * 100
                winrates[site] = {
                    "winrate": round(winrate, 1),
                    "wins": stats["wins"],
                    "total": stats["total"]
                }
            else:
                winrates[site] = {
                    "winrate": 0.0,
                    "wins": 0,
                    "total": 0
                }

        return winrates

    def _calculate_retake_winrate(self, rounds: List[Dict]) -> Dict:
        """
        Retake winrate hesaplar (plantSite + winningTeam + roundResultCode)
        Args:
            rounds: Round results listesi
        Returns:
            dict: Retake kazanma oranı
        """
        retake_wins = 0
        retake_total = 0

        for round_data in rounds:
            plant_site = round_data.get("plantSite", "")
            round_result_code = round_data.get("roundResultCode", "")

            # Bomb plant edilmiş VE defuse ile bitmiş roundlar (retake durumu)
            if plant_site and round_result_code == "Defused":
                retake_total += 1

                winning_team = round_data.get("winningTeam", "")
                player_team = round_data.get("playerTeam", "")

                # Oyuncunun takımı defuse yaparak kazandıysa
                if winning_team == player_team:
                    retake_wins += 1

        if retake_total > 0:
            winrate = (retake_wins / retake_total) * 100
            return {
                "winrate": round(winrate, 1),
                "wins": retake_wins,
                "total": retake_total
            }
        else:
            return {
                "winrate": 0.0,
                "wins": 0,
                "total": 0
            }

    def _calculate_save_rate(self, rounds: List[Dict], puuid: str) -> Dict:
        """
        Save oranı hesaplar (kills[] ile round sonunda hayatta kalma kontrolü)
        Args:
            rounds: Round results listesi
            puuid: Player PUUID
        Returns:
            dict: Save oranı
        """
        survived_rounds = 0
        total_rounds = 0

        for round_data in rounds:
            # playerStats'da bu oyuncu var mı kontrol et
            player_stats = round_data.get("playerStats", [])
            player_in_round = False

            for player_stat in player_stats:
                if player_stat.get("subject") == puuid:
                    player_in_round = True
                    break

            # Oyuncu bu roundda yoksa atla
            if not player_in_round:
                continue

            total_rounds += 1

            # Kills listesinde bu oyuncu victim olarak var mı?
            kills = round_data.get("kills", [])
            player_died = False

            for kill in kills:
                if kill.get("victim") == puuid:
                    player_died = True
                    break

            # Eğer ölen listesinde yoksa hayatta kalmış demektir
            if not player_died:
                survived_rounds += 1

        if total_rounds > 0:
            save_rate = (survived_rounds / total_rounds) * 100
            return {
                "rate": round(save_rate, 1),
                "survived": survived_rounds,
                "total": total_rounds
            }
        else:
            return {
                "rate": 0.0,
                "survived": 0,
                "total": 0
            }

    def get_kd_hs_stats(self, puuid: str, match_count: int = 5) -> Optional[Dict]:
        """
        Son N maçtan KD ve HS% hesaplar (cache kullanır)
        Args:
            puuid: Player PUUID
            match_count: Kaç maç incelenecek (varsayılan 5)
        Returns:
            dict: KD ve HS istatistikleri veya None
        """
        # Cache'de var mı kontrol et
        cached_stats = cache.get('player_stats', puuid)
        if cached_stats:
            return cached_stats

        # Son maçları al
        match_history = self.riot_api.get_match_history(puuid, start_index=0, end_index=match_count, queue="competitive")
        if not match_history:
            return None

        matches = match_history.get("History", [])
        if not matches:
            return None

        total_kills = 0
        total_deaths = 0
        total_headshots = 0
        total_bodyshots = 0
        total_legshots = 0

        for idx, match in enumerate(matches[:match_count]):
            match_id = match.get("MatchID")
            if not match_id:
                continue

            # Rate limit önlemi - daha uzun delay
            if idx > 0:
                time.sleep(2)

            match_details = self.riot_api.get_completed_match_details(match_id)
            if not match_details:
                continue

            # Oyuncunun stats bilgilerini bul
            players = match_details.get("players", [])
            for player in players:
                if player.get("subject") == puuid:
                    stats = player.get("stats", {})
                    total_kills += stats.get("kills", 0)
                    total_deaths += stats.get("deaths", 0)
                    break

            # Round bazlı headshot verilerini topla
            round_results = match_details.get("roundResults", [])
            for round_data in round_results:
                player_stats = round_data.get("playerStats", [])

                for player_stat in player_stats:
                    if player_stat.get("subject") == puuid:
                        damage_list = player_stat.get("damage", [])

                        for damage in damage_list:
                            total_headshots += damage.get("headshots", 0)
                            total_bodyshots += damage.get("bodyshots", 0)
                            total_legshots += damage.get("legshots", 0)

        # KD hesapla
        kd_ratio = round(total_kills / total_deaths, 2) if total_deaths > 0 else total_kills

        # HS% hesapla
        total_shots = total_headshots + total_bodyshots + total_legshots
        hs_percentage = round((total_headshots / total_shots) * 100, 1) if total_shots > 0 else 0.0

        result = {
            "kd": kd_ratio,
            "hs_percentage": hs_percentage,
            "total_kills": total_kills,
            "total_deaths": total_deaths,
            "total_headshots": total_headshots,
            "total_shots": total_shots
        }

        # Cache'e kaydet (15 dakika saklanır)
        cache.set('player_stats', puuid, result)

        return result
