import time
import re
from rich.console import Console
from rich.table import Table
from rich.text import Text
from utils.colors import Colors

console = Console()


def ansi_to_rich(text: str) -> str:
    """ANSI renk kodlarını rich markup formatına çevirir"""
    if not text:
        return text

    if '\033' not in text and not hasattr(Colors, 'RESET'):
        return text

    result = text

    # ANSI 256 color: \033[38;5;{n}m -> color({n})
    ansi_256_pattern = r'\033\[38;5;(\d+)m'
    matches = list(re.finditer(ansi_256_pattern, result))
    for match in matches:
        color_num = match.group(1)
        result = result.replace(match.group(0), f'[color({color_num})]')

    # ANSI dim: \033[37;2m -> dim white
    result = result.replace('\033[37;2m', '[dim white]')

    # ANSI reset: \033[0m -> [/] (sadece renk kodu varsa)
    if len(matches) > 0 or '\033[37;2m' in text:
        result = result.replace('\033[0m', '[/]')
        if hasattr(Colors, 'RESET'):
            result = result.replace(Colors.RESET, '[/]')
    else:
        # Hiç renk kodu yoksa reset kodlarını temizle
        result = result.replace('\033[0m', '')
        if hasattr(Colors, 'RESET'):
            result = result.replace(Colors.RESET, '')

    # Başta yalnız kalan [/] tag'lerini temizle
    result = re.sub(r'^\[/\]', '', result)
    # Sonda birden fazla [/] varsa tek [/] yap
    result = re.sub(r'\[/\](\[/\])+$', '[/]', result)

    return result


def print_ascii_art():
    import shutil

    ascii_lines = [
        "██╗  ██╗    ████████╗██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗",
        "╚██╗██╔╝    ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗",
        " ╚███╔╝        ██║   ██████╔╝███████║██║     █████╔╝ █████╗  ██████╔╝",
        " ██╔██╗        ██║   ██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗",
        "██╔╝ ██╗       ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║",
        "╚═╝  ╚═╝       ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝",
        "                                                         by @yiitgven7x"
    ]

    terminal_width = shutil.get_terminal_size().columns
    print()
    for line in ascii_lines:
        padding = (terminal_width - len(line)) // 2
        print(f"\033[95m{' ' * padding}{line}\033[0m")
    print()


def print_status(message: str, clear_screen: bool = False, status_type: str = "info"):
    import shutil

    if clear_screen:
        print("\033[H\033[J")
        print_ascii_art()

    terminal_width = shutil.get_terminal_size().columns
    message_length = len(message)
    padding = (terminal_width - message_length) // 2

    print(f"{' ' * padding}{message}")


def create_player_table(game_info: dict) -> Table:
    players = game_info.get("players", [])

    team_blue = [p for p in players if p.get("team_id", "").lower() == "blue"]
    team_red = [p for p in players if p.get("team_id", "").lower() == "red"]

    table = Table(
        show_header=True,
        header_style="bold white",
        border_style="bright_white",
        expand=False,
        padding=(0, 1),
        show_lines=False
    )

    table.add_column("Oyuncu", style="white", no_wrap=False)
    table.add_column("Seviye", justify="left", style="cyan")
    table.add_column("Rank", style="white")
    table.add_column("Ajan", style="white")
    table.add_column("Vandal Skin", style="white")

    for player in team_blue:
        player_name = f"{player['game_name']}#{player['tag_line']}"
        level = str(player.get('level', '?')) if player.get('level') is not None else '?'
        rank = ansi_to_rich(player.get('rank', '?'))
        agent_name = ansi_to_rich(player['agent_name'])
        skin_name = player['vandal_skin']

        table.add_row(player_name, level, rank, agent_name, skin_name)

    table.add_row("", "", "", "", "", end_section=True)

    for player in team_red:
        player_name = f"{player['game_name']}#{player['tag_line']}"
        level = str(player.get('level', '?')) if player.get('level') is not None else '?'
        rank = ansi_to_rich(player.get('rank', '?'))
        agent_name = ansi_to_rich(player['agent_name'])
        skin_name = player['vandal_skin']

        table.add_row(player_name, level, rank, agent_name, skin_name)

    return table
