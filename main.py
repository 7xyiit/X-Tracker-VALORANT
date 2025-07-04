import os
import sys
import time
import asyncio
import websockets
import ssl
import json
import base64
from utils import (
    Colors,
    get_lockfile,
    get_local_headers,
    get_player_puuid,
    check_game_status,
    get_game_info,
    create_player_table
)

def print_ascii_art():
    ascii_art = """
\033[95m
██╗  ██╗    ████████╗██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗ 
╚██╗██╔╝    ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
 ╚███╔╝        ██║   ██████╔╝███████║██║     █████╔╝ █████╗  ██████╔╝
 ██╔██╗        ██║   ██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
██╔╝ ██╗       ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║
╚═╝  ╚═╝       ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
                                                         by @yiitgven7x\033[0m
"""
    print(ascii_art)

def print_status(message, clear_screen=False, status_type="info"):
    if clear_screen:
        print("\033[H\033[J")  # Konsolu temizle
        print_ascii_art()
    
    timestamp = time.strftime("%H:%M:%S")
    
    if status_type == "error":
        prefix = f"{Colors.ERROR}[ERROR]{Colors.RESET}"
    elif status_type == "success":
        prefix = f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET}"
    elif status_type == "warning":
        prefix = f"{Colors.WARNING}[WARNING]{Colors.RESET}"
    else:
        prefix = f"{Colors.INFO}[INFO]{Colors.RESET}"
    
    print(f"{Colors.BOLD}[{timestamp}]{Colors.RESET} {prefix} {message}")

async def websocket_connect(port, auth):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        # Önce yeni websockets versiyonu için extra_headers ile dene
        uri = f"wss://127.0.0.1:{port}"
        headers = {
            "Authorization": f"Basic {auth}"
        }
        
        try:
            async with websockets.connect(uri, ssl=ssl_context, extra_headers=headers) as websocket:
                print_status("📡 Websocket bağlantısı başarılı!")
                
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if data.get("eventType") == "Update":
                            # Oyun güncellemesi algılandı
                            print_status("🔄 Oyun durumu güncellendi!")
                            
                    except websockets.exceptions.ConnectionClosed:
                        print_status("❌ Websocket bağlantısı kapandı!")
                        break
                        
        except TypeError as e:
            if "extra_headers" in str(e):
                # Eski websockets versiyonu için URI authentication
                password = base64.b64decode(auth).decode().split(':')[1]
                uri_with_auth = f"wss://riot:{password}@127.0.0.1:{port}"
                
                async with websockets.connect(uri_with_auth, ssl=ssl_context) as websocket:
                    print_status("📡 Websocket bağlantısı başarılı!")
                    
                    while True:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            
                            if data.get("eventType") == "Update":
                                # Oyun güncellemesi algılandı
                                print_status("🔄 Oyun durumu güncellendi!")
                                
                        except websockets.exceptions.ConnectionClosed:
                            print_status("❌ Websocket bağlantısı kapandı!")
                            break
            else:
                raise e
                
    except Exception as e:
        print_status(f"⚠️ Websocket bağlantı hatası: {e}")

async def monitor_game_status(port, headers, puuid):
    previous_match_id = None
    websocket_task = None
    
    try:
        while True:
            try:
                if check_game_status(port, headers, puuid):
                    game_info = await get_game_info(port, headers, puuid)
                    if game_info:
                        match_details, player_names, loadouts = game_info
                        current_match_id = match_details.get("MatchID")
                        
                        if current_match_id != previous_match_id:
                            if websocket_task and not websocket_task.done():
                                websocket_task.cancel()
                                
                            print_status("🎮 Yeni oyun tespit edildi!", True, "success")
                            print_status("📊 Oyuncu bilgileri yükleniyor...", status_type="info")
                            print_status("✨ Tablo hazırlanıyor...\n", status_type="info")
                            print(f"{Colors.BOLD}")  # Tabloyu kalın yap
                            print(create_player_table(match_details, player_names, loadouts))
                            print(f"{Colors.RESET}")  # Reset
                            previous_match_id = current_match_id
                            
                            auth = headers['Authorization'].split(' ')[1]
                            websocket_task = asyncio.create_task(websocket_connect(port, auth))
                else:
                    if previous_match_id:
                        print_status("🏁 Oyun bitti! Yeni oyun bekleniyor...", True, "warning")
                        if websocket_task and not websocket_task.done():
                            websocket_task.cancel()
                        previous_match_id = None
                    else:
                        print_status("🔍 Oyun bekleniyor...", True, "info")
                        print_status("💡 Valorant'ı açıp bir oyuna girdiğinizde bilgiler otomatik görüntülenecek.", status_type="info")
                
                await asyncio.sleep(25)
                
            except Exception as e:
                print_status(f"⚠️ Hata oluştu: {e}", status_type="error")
                await asyncio.sleep(5)
                
    except KeyboardInterrupt:
        if websocket_task and not websocket_task.done():
            websocket_task.cancel()
        raise
    except asyncio.CancelledError:
        if websocket_task and not websocket_task.done():
            websocket_task.cancel()
        raise

if __name__ == "__main__":
    try:
        print_status("🎯 VALORANT TRACKER BAŞLATILIYOR...", True, "info")
        print_status("🔍 Valorant kontrol ediliyor...", status_type="info")
        
        lockfile = get_lockfile()
        if lockfile:
            headers = get_local_headers(lockfile)
            print_status("✅ Lockfile başarıyla okundu!", status_type="success")
            
            puuid = get_player_puuid(lockfile['port'], headers)
            if puuid:
                print_status("🆔 PUUID bulundu!", status_type="success")
                time.sleep(3)
                asyncio.run(monitor_game_status(lockfile['port'], headers, puuid))
        else:
            print_status("❌ Valorant çalışmıyor! Lütfen oyunu başlatın.", status_type="error")
            
    except KeyboardInterrupt:
        print_status("👋 Program kapatılıyor...", True, "warning")
        print_status("✨ İyi oyunlar!", status_type="success")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0) 