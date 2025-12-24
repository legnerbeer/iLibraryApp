import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from iLibrary import Library
import flet as ft
import json
import content.config as config
from content.functions import load_decrypted_credentials, get_or_generate_key
# Assuming content.all_libraries is available
from content.all_libraries import AllLibraries
from content.settings import Settings

async def run_sync(page):
    env_file_path = Path(__file__).parent /"content"/ ".env"
    ENCRYPTION_KEY_STR = get_or_generate_key(env_file_path)
    load_dotenv(env_file_path, override=True)
    while True:
        if os.getenv("ENCRYPTED_DB_CREDENTIALS"):
            db_credentials = load_decrypted_credentials(
                key=ENCRYPTION_KEY_STR,
                env_file_path=env_file_path,
            )

            if db_credentials:
                DB_DRIVER = db_credentials["driver"]
                DB_USER = db_credentials["user"]
                DB_PASSWORD = db_credentials["password"]
                DB_SYSTEM = db_credentials["system"]


                try:
                    with Library(DB_USER, DB_PASSWORD, DB_SYSTEM, DB_DRIVER) as lib:
                        result = lib.getAllLibraries()
                        await page.client_storage.set_async('all_libraries', result)
                        data = json.loads(result)
                        lib_names = []
                        for item in data:
                            lib_names.append(item["OBJNAME"])
                        await page.client_storage.set_async('library_names', lib_names)
                        lib.conn.close()
                        config.SERVER_STATUS = True
                except Exception as e:
                    config.SERVER_STATUS = False
                    print(e)

        await asyncio.sleep(60.0)

async def main(page: ft.Page):
    page.run_task(run_sync, page)
    #await page.client_storage.clear_async()
    page.theme = ft.Theme(
        use_material3=True,
        color_scheme_seed="#00ffe5"

    )
    try:
        theme_mode = await page.client_storage.get_async("theme_mode")
    except Exception:
        theme_mode=None
    page.theme_mode = (
        ft.ThemeMode.LIGHT if theme_mode == "light"
        else ft.ThemeMode.DARK if theme_mode == "dark"
        else ft.ThemeMode.SYSTEM
    )
    # ---------------------------------------------------
    # Container for dynamically changing content
    # ---------------------------------------------------
    # This control will hold the current view (e.g., AllLibraries, Settings)
    page_content = ft.Container(content=ft.Text("Initializing..."))

    # ---------------------------------------------------
    # Helper: replace content instantly
    # ---------------------------------------------------
    async def clear_and_add_control(control):
        # Instead of clearing all controls on the page, we update the content
        # of the dedicated page_content container.
        page_content.content = control
        page_content.update()  # Use update_async for controls

    # Attaching the helper to page is fine, but we'll use it directly in handlers.
    # page.clear_and_add_control = clear_and_add_control # Removed: using it directly is cleaner
    # ---------------------------------------------------
    # Navigation Bar Handler
    # ---------------------------------------------------
    async def navigation_bar_changed(e):
        idx = e.control.selected_index

        if idx == 0:  # ALL LISTS
            # Load the AllLibraries content
            await clear_and_add_control(AllLibraries(
                page,
                content_manager=clear_and_add_control))
            page.title = "Libraries"  # Update page title

        elif idx == 1:  # Users
            await clear_and_add_control(
                ft.Container(
                    content=ft.Text("This Content (Users) is in Development"),
                    alignment=ft.alignment.center
                )
            )
            page.title = "Users"  # Update page title
            # page.open(ft.SnackBar(ft.Text("This Content is in Development"), show_close_icon=True))

        elif idx == 2:  # SETTINGS
            page.title = "Settings"
            await clear_and_add_control(Settings(
                page,
                content_manager=clear_and_add_control))
        elif idx == 3:  # Leave the App
            dlg = ft.AlertDialog(
                title="Close App",
                content=ft.Text("Are you sure you want to leave the app?"),
                actions=[
                    ft.TextButton("No", on_click=lambda e: page.close(dlg)),
                    ft.TextButton("Yes", on_click=lambda e: page.window.close(), style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_ACCENT_400)),
                ]
            )
            page.open(dlg)


        # Ensure the entire page updates if necessary (e.g., if title changed)
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.LIBRARY_BOOKS_OUTLINED,
                selected_icon=ft.Icons.LIBRARY_BOOKS,
                label="All Libraries",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.ACCOUNT_CIRCLE_OUTLINED),
                selected_icon=ft.Icon(ft.Icons.ACCOUNT_CIRCLE),
                label="Users",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icon(ft.Icons.SETTINGS),
                label_content=ft.Text("Settings"),
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.EXIT_TO_APP_OUTLINED,
                selected_icon=ft.Icon(ft.Icons.EXIT_TO_APP),
                label_content=ft.Text("Close App"),

            ),
        ],
        on_change=navigation_bar_changed,
    )

    # ---------------------------------------------------
    # Initial Page Layout
    # ---------------------------------------------------
    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1),
                # Add the content container to the Row, expanding it to fill space
                ft.Column([page_content], expand=True, alignment=ft.MainAxisAlignment.START, scroll=ft.ScrollMode.ADAPTIVE)
            ],
            expand=True,
        )
    )

    # ---------------------------------------------------
    # Load default content (Index 0) on startup
    # ---------------------------------------------------
    # Call the handler with an event object reflecting the default index (0)
    import types
    await navigation_bar_changed(types.SimpleNamespace(control=rail))


ft.app(main)