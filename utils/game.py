import json
import base64
import asyncio
import time
import requests
from .api import (
    get_version_and_platform,
    get_region_and_shard,
    get_coregame_token,
    get_match_id,
    get_match_details,
    get_match_loadouts,
    get_player_names,
    get_player_party_info,
    get_player_level
)
from .ranks import get_player_ranks
from .stats import get_headshot_percentage
from .colors import Colors

def check_game_status(port, headers, target_puuid):
    try:
        response = requests.get(
            f'https://127.0.0.1:{port}/chat/v4/presences',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        presences = response.json().get('presences', [])
        
        for presence in presences:
            if presence.get('puuid') == target_puuid:
                private_data = json.loads(base64.b64decode(presence.get('private', '')))
                session_state = private_data.get('sessionLoopState')
                return session_state == "INGAME"
                
        return False
    except Exception as e:
        print(f"Oyun durumu kontrol hatası: {e}")
        return False

async def get_game_info(port, auth_headers, puuid):
    try:
        # API istekleri için gerekli bilgileri al
        client_platform, client_version = get_version_and_platform()
        region, shard = get_region_and_shard()
        access_token, entitlements_token = get_coregame_token(port, auth_headers)
        
        if not all([client_platform, client_version, access_token, entitlements_token]):
            print(f"{Colors.ERROR}Gerekli bilgiler alınamadı!{Colors.RESET}")
            return None
        
        # API Headers
        headers = {
            "X-Riot-ClientPlatform": client_platform,
            "X-Riot-ClientVersion": client_version,
            "X-Riot-Entitlements-JWT": entitlements_token,
            "Authorization": f"Bearer {access_token}"
        }
        
        # Match ID al
        match_id = get_match_id(puuid, region, shard, headers)
        if not match_id:
            return None
        
        # Maç detaylarını al
        match_details = get_match_details(match_id, region, shard, headers)
        if not match_details:
            return None
        
        # Loadout bilgilerini al
        loadouts = get_match_loadouts(match_id, region, shard, headers)
        
        # Oyuncu PUUID'lerini topla
        player_puuids = [player["Subject"] for player in match_details.get("Players", [])]
        
        # Oyuncu isimlerini al
        player_names = get_player_names(player_puuids, shard, headers)
        if not player_names:
            return None
            
        # Parti bilgilerini al
        player_parties = get_player_party_info(puuid, region, shard, headers)
        match_details["PlayerParties"] = player_parties
            
        # Oyuncu ranklarını, HS oranlarını, winrate'leri ve seviyelerini al
        player_ranks = {}
        player_peak_ranks = {}
        player_hs_percentages = {}
        player_winrates = {}
        player_levels = {}
        
        # Önce core-game'den gelen seviye bilgilerini kontrol et
        core_game_levels = match_details.get("PlayerLevels", {})
        
        for i, player_puuid in enumerate(player_puuids):
            if i > 0:  # İlk istek hariç her istekten önce bekle
                await asyncio.sleep(2.0)  # 2 saniye bekle (artırıldı)
            try:
                current_rank, peak_rank, winrate = get_player_ranks(player_puuid, shard, headers)
                player_ranks[player_puuid] = current_rank
                player_peak_ranks[player_puuid] = peak_rank
                player_winrates[player_puuid] = winrate
                
                # HS oranını al
                try:
                    hs_percentage = get_headshot_percentage(player_puuid, shard, headers)
                    player_hs_percentages[player_puuid] = hs_percentage
                except Exception as hs_error:
                    print(f"HS oranı alınamadı ({player_puuid}): {hs_error}")
                    player_hs_percentages[player_puuid] = "?"  # HS oranını "?" olarak ayarla
                
                # Seviye bilgisini al - önce core-game'den gelen veriyi kontrol et
                level = core_game_levels.get(player_puuid, 0)
                if level == 0 or level == "?":
                    # Eğer core-game'den alınamazsa API'den çek
                    try:
                        level = get_player_level(player_puuid, shard, headers)
                    except Exception as level_error:
                        print(f"Seviye bilgisi alınamadı ({player_puuid}): {level_error}")
                        level = "?"
                player_levels[player_puuid] = level
                
            except Exception as e:
                print(f"Oyuncu verisi alınamadı ({player_puuid}): {e}")
                player_ranks[player_puuid] = "?"
                player_peak_ranks[player_puuid] = "?"
                player_hs_percentages[player_puuid] = "?"
                player_winrates[player_puuid] = "?"
                player_levels[player_puuid] = core_game_levels.get(player_puuid, "?")
        
        match_details["PlayerRanks"] = player_ranks
        match_details["PlayerPeakRanks"] = player_peak_ranks
        match_details["PlayerHSPercentages"] = player_hs_percentages
        match_details["PlayerWinrates"] = player_winrates
        match_details["PlayerLevels"] = player_levels
        
        return match_details, player_names, loadouts
        
    except Exception as e:
        print(f"{Colors.ERROR}Oyun bilgileri alınırken hata oluştu: {e}{Colors.RESET}")
        return None