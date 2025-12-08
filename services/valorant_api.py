"""
Valorant-API.com Servisi
Ajan ve silah bilgilerini dinamik olarak çeker
"""
import requests
from typing import Dict, Optional
from config.settings import VALORANT_API_BASE, VALORANT_API_LANGUAGE, VANDAL_UUID


class ValorantAPIService:
    """Valorant-API.com ile iletişim için servis"""

    def __init__(self):
        self.base_url = VALORANT_API_BASE
        self.language = VALORANT_API_LANGUAGE

    def get_agents(self) -> Dict[str, str]:
        """
        Oynanabilir tüm ajanları çeker (dinamik)
        Returns:
            dict: {agent_uuid: colored_agent_name}
        """
        try:
            url = f"{self.base_url}/agents"
            params = {
                "language": self.language,
                "isPlayableCharacter": "true"
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            agents_data = response.json()["data"]

            # Ajan renkleri (rollere göre)
            # NOT: API'den BÜYÜK HARF geldiği için key'leri uppercase yapıyoruz
            agent_colors = {
                # Duelists
                "JETT": "\033[38;5;153m",      # Açık Mavi
                "PHOENIX": "\033[38;5;208m",   # Turuncu
                "RAZE": "\033[38;5;214m",      # Koyu Sarı
                "REYNA": "\033[38;5;165m",     # Mor
                "YORU": "\033[38;5;27m",       # Mavi
                "NEON": "\033[38;5;51m",       # Neon Mavi
                "ISO": "\033[38;5;147m",       # Açık Morumsu
                # Initiators
                "SOVA": "\033[38;5;75m",       # Açık Mavi
                "BREACH": "\033[38;5;166m",    # Turuncu-Kahve
                "SKYE": "\033[38;5;114m",      # Yeşil
                "KAY/O": "\033[38;5;87m",      # Turkuaz
                "FADE": "\033[38;5;61m",       # Açık Lacivert
                "GEKKO": "\033[38;5;84m",      # Açık Yeşil
                # Controllers
                "BRIMSTONE": "\033[38;5;130m", # Kahverengi
                "VIPER": "\033[38;5;40m",      # Yeşil
                "OMEN": "\033[38;5;91m",       # Mor
                "ASTRA": "\033[38;5;171m",     # Pembe
                "HARBOR": "\033[38;5;31m",     # Deniz Mavisi
                "CLOVE": "\033[38;5;218m",     # Tatlı Açık Pembe
                # Sentinels
                "KILLJOY": "\033[38;5;226m",   # Sarı
                "CYPHER": "\033[38;5;251m",    # Gümüş
                "SAGE": "\033[38;5;123m",      # Açık Turkuaz
                "CHAMBER": "\033[38;5;220m",   # Altın
                "DEADLOCK": "\033[38;5;117m",  # Buz Mavisi
                "VYSE": "\033[38;5;140m",      # Açık-Koyu Mor Arası
                # Yeni Ajanlar
                "TEJO": "\033[38;5;215m",      # Hafif Açık Turuncu
                "VETO": "\033[38;5;196m",      # Kırmızı
            }

            # UUID -> Renkli İsim mapping
            agent_dict = {}
            for agent in agents_data:
                agent_name = agent["displayName"]  # API'den BÜYÜK HARF geliyor (örn: "GEKKO")

                # Renk eşleştirmesi için BÜYÜK HARF kullan
                color = agent_colors.get(agent_name, "\033[0m")

                # Gösterimde capitalize et (Gekko, Kay/O gibi)
                # Özel durumlar için kontrol
                if agent_name == "KAY/O":
                    display_name = "Kay/O"
                else:
                    display_name = agent_name.capitalize()

                agent_uuid = agent["uuid"].lower()
                agent_dict[agent_uuid] = f"{color}{display_name}\033[0m"

            return agent_dict

        except Exception as e:
            print(f"Ajan bilgileri alınamadı: {e}")
            return {}

    def get_vandal_skins(self) -> Dict[str, str]:
        """
        Vandal skinlerini çeker (dinamik)
        Returns:
            dict: {skin_uuid: skin_name}
        """
        try:
            url = f"{self.base_url}/weapons/{VANDAL_UUID}"
            params = {"language": self.language}

            response = requests.get(url, params=params)
            response.raise_for_status()
            skins_data = response.json()["data"]["skins"]

            # UUID -> Skin İsmi mapping (case-insensitive)
            skin_dict = {}
            for skin in skins_data:
                skin_uuid = skin.get("uuid", "")
                display_name = skin.get("displayName", "")

                # İsim düzenleme - API'den hem BÜYÜK HARF hem normal gelebilir
                display_name_upper = display_name.upper()
                if display_name_upper == "VANDAL" or display_name == "Standard":
                    display_name = "Standart Vandal"
                else:
                    # Capitalize her kelimeyi
                    words = display_name.split()
                    display_name = " ".join(word.capitalize() for word in words)

                # UUID'yi küçük harfe çevir (case-insensitive lookup için)
                skin_dict[skin_uuid.lower()] = display_name

            return skin_dict

        except Exception as e:
            print(f"Vandal skinleri alınamadı: {e}")
            return {}

    def get_client_version(self) -> Optional[str]:
        """
        Güncel Valorant client versiyonunu çeker
        Returns:
            str: Client version veya None
        """
        try:
            url = f"{self.base_url}/version"
            response = requests.get(url)
            response.raise_for_status()
            version_data = response.json()
            return version_data["data"]["riotClientVersion"]

        except Exception as e:
            print(f"Version bilgisi alınamadı: {e}")
            return None
