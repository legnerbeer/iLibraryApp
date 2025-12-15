import os
import json
from pathlib import Path

import flet as ft
from dotenv import load_dotenv

from content.functions import load_decrypted_credentials, get_or_generate_key
from iLibrary import Library

#Information about Library: <NAME>
class Info(ft.Column):
    def __init__(self, page: ft.Page, library:str):
        super().__init__(
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,

        )
        self.DOWNLOAD_PATH = Path.home() / "Downloads"
        self.page = page
        self.library = library
        self.env_file_path = Path(__file__).parent / ".env"
        self.ENCRYPTION_KEY_STR = None
        self.db_credentials = None
        self.DB_DRIVER = None
        self.DB_USER = None
        self.DB_PASSWORD = None
        self.DB_SYSTEM = None

        self.list_container = ft.Column()
        self.input_card = self.list_container
        self._create_app_bar()
        self.progress_bar = ft.ProgressRing()
        self.progress_bar_container = ft.Container(self.progress_bar, alignment=ft.alignment.center)
        self.controls.append(self.progress_bar_container)

        # Start initialization
        self.page.run_task(self.async_init)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress_bar.visible = True
        self.progress_bar_container.visible = True
        self.page.update()
        self.lib.conn.close()

    def _create_app_bar(self):
        self.page.appbar = ft.AppBar(
            title=ft.Text(f"Library Info: {self.library}"),
        )
        self.page.update()
    async def async_init(self):
        self.ENCRYPTION_KEY_STR = get_or_generate_key(self.env_file_path)
        load_dotenv(self.env_file_path, override=True)

        if os.getenv("ENCRYPTED_DB_CREDENTIALS"):
            self.db_credentials = load_decrypted_credentials(
                key=self.ENCRYPTION_KEY_STR,
                env_file_path=self.env_file_path,
            )

            if self.db_credentials:
                self.DB_DRIVER = self.db_credentials["driver"]
                self.DB_USER = self.db_credentials["user"]
                self.DB_PASSWORD = self.db_credentials["password"]
                self.DB_SYSTEM = self.db_credentials["system"]
                self.input_card.visible = True
                self.list_container.visible = True

                if self.input_card not in self.controls:
                    self.controls.extend([self.input_card])
                await self._get_info_about_library()
            else:
                pass
                #await self._show_setup_modal()
        else:
            pass
            #await self._show_setup_modal()

        self.update()

    async def _get_info_about_library(self):
        try:
            with Library(self.DB_USER, self.DB_PASSWORD, self.DB_SYSTEM, self.DB_DRIVER) as self.lib:
                result = self.lib.getLibraryInfo(library=self.library, wantJson=True)
                test = ft.Container(
                    content=ft.Stack([
                        ft.CircleAvatar(
                            content=ft.Text(self.library[0:2]),
                        ),
                    ])

                )
                self.input_card.controls.append(test)
                print(result)
        except Exception as e:
            self.input_card.controls.clear()
            self.input_card.controls.append(
                ft.Text(f"Connection Error: {e}")
        )
        self.progress_bar.visible = False
        self.progress_bar_container.visible = False
        self.update()