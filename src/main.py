import asyncio
import os
import json
import types
from pathlib import Path
from dotenv import load_dotenv

import flet as ft
from iLibrary import Library, User

import content.config as config
from content.functions import load_decrypted_credentials, get_or_generate_key
from content.all_libraries import AllLibraries
from content.all_users import AllUsers
from content.settings import Settings


# --- Helper: Unified Navigation Content Manager ---
async def clear_and_add_control(page_content: ft.Container, control):
    """Replaces the content of the main container and updates the UI."""
    page_content.content = control
    page_content.update()


# --- Background Task: Sync and Banner Management ---
async def run_sync(page: ft.Page, page_content: ft.Container):
    env_file_path = Path(__file__).parent / "content" / ".env"

    # Navigation logic for the Banner action
    async def _handle_settings_click(e):
        from content.settings import Settings
        page.pop_dialog()
        # Helper to route inside the background task
        settings_view = Settings(
            page,
            content_manager=lambda c: clear_and_add_control(page_content, c)
        )
        await clear_and_add_control(page_content, settings_view)

    # Define the persistent Banner
    error_banner = ft.Banner(
        bgcolor=ft.Colors.ERROR_CONTAINER,
        leading=ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.ERROR, size=40),
        content=ft.Text(
            value="No Database Connection. Please check Credentials in Settings.",
            color=ft.Colors.ON_ERROR_CONTAINER,
        ),
        actions=[
            ft.TextButton(
                "Go to Settings",
                style=ft.ButtonStyle(color=ft.Colors.ON_ERROR_CONTAINER),
                on_click=_handle_settings_click,
            ),
        ],
    )

    # Initialize the overlay
    page.overlay.append(error_banner)
    page.update()

    # Periodically syncs library and user data; handles missing credentials
    while True:
        ENCRYPTION_KEY_STR = get_or_generate_key(env_file_path)
        load_dotenv(env_file_path, override=True)
        credentials_str = os.getenv("ENCRYPTED_DB_CREDENTIALS")


        if credentials_str:
            db_credentials = load_decrypted_credentials(ENCRYPTION_KEY_STR, env_file_path)

            if db_credentials:
                await ft.SharedPreferences().set('server', str(db_credentials["system"]))
                page.pop_dialog()
                try:
                    with Library(db_credentials["user"], db_credentials["password"],
                                 db_credentials["system"], db_credentials["driver"]) as lib:

                        # 1. Ensure result is a valid string
                        raw_result = lib.getAllLibraries()
                        result_str = str(raw_result) if raw_result is not None else "[]"

                        # Save the raw string
                        await ft.SharedPreferences().set('all_libraries', str(result_str))

                        # 2. Parse and validate the list
                        data = json.loads(result_str)
                        # Ensure every item is a string and handle missing keys
                        lib_names = [str(item.get("OBJNAME", "")) for item in data if item.get("OBJNAME")]

                        await ft.SharedPreferences().set('library_names', str(lib_names))
                        config.SERVER_STATUS = True

                except Exception as e:
                    config.SERVER_STATUS = False
                    print(f"Library Sync Error: {e}")

                    # --- Sync Users ---
                try:
                    with User(db_credentials["user"], db_credentials["password"],
                              db_credentials["system"], db_credentials["driver"]) as user:

                        # 1. Fetch result
                        raw_user_result = user.getAllUsers(wantJson=True)
                        user_result_str = str(raw_user_result) if raw_user_result is not None else "[]"

                        await ft.SharedPreferences().set('all_users', str(user_result_str))

                        # 2. Parse and validate names
                        user_data = json.loads(user_result_str)
                        # Use .get() to prevent KeyErrors and str() to prevent type mismatches
                        user_names = [str(item.get("AUTHORIZATION_NAME", "")) for item in user_data if
                                      item.get("AUTHORIZATION_NAME")]

                        await ft.SharedPreferences().set('user_names', str(user_names))

                except Exception as e:
                    print(f"User Sync Error: {e}")
        else:
            # Show banner if credentials missing
            if not error_banner.open:
                page.show_dialog(error_banner)

        page.update()
        await asyncio.sleep(60.0)


# --- Main Application Entry Point ---
async def main(page: ft.Page):

    # Setup Page Properties
    page.title = "iLibrary App"
    page.theme = ft.Theme(use_material3=True, color_scheme_seed="#00ffe5")

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
                    ft.TextButton(
                        content="Yes",
                        on_click=lambda _: page.run_task(page.window.close),
                        style=ft.ButtonStyle(bgcolor=ft.Colors.RED)
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
    page.run_task(run_sync, page, page_content)

    # Load Default View (Libraries)
    await navigation_bar_changed(types.SimpleNamespace(control=rail))


if __name__ == "__main__":
    ft.run(main)