import asyncio
import os
import types
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import flet as ft
from content.sync_worker import SyncWorker
from content.functions import get_or_generate_key
from content.LibraryStuff.all_libraries import AllLibraries
from content.UserStuff.all_users import AllUsers
from content.settings import Settings
import logging

# --- Helper: Unified Navigation Content Manager ---
async def clear_and_add_control(page_content: ft.Container, control):
    """Replaces the content of the main container and updates the UI."""
    page_content.content = control
    page_content.update()


def setup_logger():
    # 1. Define the directory: ~/Library/Logs/iLibraryApp
    log_dir = Path.home() / "Library" / "Logs" / "iLibraryApp"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 2. Generate a unique filename based on the current start time
    start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"build_session_{start_time}.log"

    # 3. Configure the logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Write to the new file
            logging.StreamHandler()  # Also print to Terminal/Console
        ]
    )

    logging.info(f"--- New Session Started: {log_file} ---")


# --- Main Application Entry Point ---
async def main(page: ft.Page):
    setup_logger()


    #Shutdown
    def handle_cleanup(e):
        print("Application closing. Signaling worker to stop...")
        if os.path.exists('worker.pid'):
            os.unlink('worker.pid')
        # Tell the worker to stop its loop
        worker.running = False

        # Attach the cleanup function to the window close event

    page.on_close = handle_cleanup
    page.title = "iLibrary App"

    page.theme = ft.Theme(use_material3=True, color_scheme_seed="#006E7C")
    #00ffe5
    # Load Theme Mode from storage
    theme_val = await ft.SharedPreferences().get("theme_mode")
    page.theme_mode = (
        ft.ThemeMode.LIGHT if theme_val == "light"
        else ft.ThemeMode.DARK if theme_val == "dark"
        else ft.ThemeMode.SYSTEM
    )

    # Main Dynamic Content Area
    page_content = ft.Container(expand=True)

    # Navigation Helper Wrapper
    async def route_to(control):
        await clear_and_add_control(page_content, control)

    # Navigation Bar Handler
    async def navigation_bar_changed(e):

        idx = e.control.selected_index

        if idx == 0:  # Libraries
            page.title = "Libraries"
            await route_to(AllLibraries(page, content_manager=route_to))
        elif idx == 1:  # Users
            page.title = "Users"
            await route_to(AllUsers(page, content_manager=route_to))
        elif idx == 2:  # Settings
            page.title = "Settings"
            await route_to(Settings(page, content_manager=route_to))
        elif idx == 3:  # Exit
            dlg = ft.AlertDialog(
                title=ft.Text("Close App"),
                content=ft.Text("Are you sure you want to leave?"),
                actions=[
                    ft.TextButton("No", on_click=lambda _: page.pop_dialog()),
                    ft.Button(
                        content="Yes",
                        on_click=lambda _: page.run_task(page.window.close),
                        style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR)
                    )
                ]
            )
            page.show_dialog(dlg)

        page.update()

    # Sidebar UI
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.LIBRARY_BOOKS_OUTLINED, selected_icon=ft.Icons.LIBRARY_BOOKS,
                                         label="Libraries"),
            ft.NavigationRailDestination(icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED, selected_icon=ft.Icons.ACCOUNT_CIRCLE,
                                         label="Users"),
            ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS,
                                         label="Settings"),
            ft.NavigationRailDestination(icon=ft.Icons.EXIT_TO_APP_OUTLINED, selected_icon=ft.Icons.EXIT_TO_APP,
                                         label="Close App"),
        ],
        on_change=navigation_bar_changed,
    )

    # Initial Layout Construction
    env_file_path = Path(__file__).parent / "content" / ".env"
    ENCRYPTION_KEY_STR = get_or_generate_key(env_file_path)
    load_dotenv(env_file_path, override=True)
    credentials_str = os.getenv("ENCRYPTED_DB_CREDENTIALS")


    async def _go_to_settings_page_from_error():
        rail.selected_index = 2
        page.update()
        await route_to(Settings(page, content_manager=route_to))


    if not credentials_str:

        error_banner = ft.Banner(
            #bgcolor = ft.Colors.SURFACE,
            leading=ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.ON_ERROR_CONTAINER, size=40),
            content=ft.Text(
                value="No Database Connection. Please check Credentials in Settings.",
                # color=ft.Colors.ON_ERROR_CONTAINER,
            ),
            actions=[
                ft.OutlinedButton(
                    "Go to Settings",
                    on_click=lambda e: page.run_task(_go_to_settings_page_from_error),
                ),
            ],
        )

        page.update()
        page.show_dialog(error_banner)
    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1),
                ft.Column(
                    [page_content],
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                    scroll=ft.ScrollMode.ADAPTIVE
                )
            ],
            expand=True,
        )
    )

    # Start Background Sync Task
    #page.run_task(run_sync, page)

    # Load Default View (Libraries)

    await navigation_bar_changed(types.SimpleNamespace(control=rail))


    page.update()

    await asyncio.sleep(0.1)
    worker = SyncWorker(page=page)

    page.run_task(worker.main_loop)

if __name__ == "__main__":
    ft.run(main)