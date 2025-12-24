import os

import flet as ft
from pathlib import Path
from content.functions import load_decrypted_credentials, get_or_generate_key, try_to_build_connection
import json
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet


class Settings(ft.Column):
    def __init__(self, page: ft.Page, content_manager):
        super().__init__(
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,

        )
        self.page = page
        self.content_manager = content_manager
        self.env_file_path = Path(__file__).parent / ".env"

        self.ENCRYPTION_KEY_STR = None
        self.db_credentials = None
        self.DB_DRIVER = None
        self.DB_USER = None
        self.DB_PASSWORD = None
        self.DB_SYSTEM = None


        self.list_container = ft.Column()
        self.input_card = self.list_container

        # Start initialization
        self.page.run_task(self.async_init)
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.page.update()


    async def async_init(self):
        await self._load_modals()
        self.list_container.controls.append(
            ft.Container(ft.ListTile(
                leading=None,
                title=ft.Text("IBMi Server Settings"),
                on_click=lambda e:self.page.open(self.add_server_modal),
                is_three_line=True,
                #subtitle=ft.Text(f"Description: {item["TEXT"]} \nCreated: {item['OBJCREATED']}"),
                bgcolor=ft.Colors.INVERSE_PRIMARY,
            ),
                border_radius=8,
            )
        )
        self.list_container.controls.append(
            ft.Container(ft.ListTile(
                leading=None,
                title=ft.Text("Switch Thema Mode"),
                on_click=lambda e: self.page.open(self.switch_shema_modal),
                is_three_line=True,
                bgcolor=ft.Colors.INVERSE_PRIMARY,
            ),
                border_radius=8,
            )
        )
        await self._create_app_bar()
        self.controls.append(self.list_container)
        self.page.update()

    async def _create_app_bar(self):
        self.page.appbar = ft.AppBar(
            title=ft.Text("Settings"),
            # actions=[
            #     # Reference the instance variable here
            #     ft.Container(content=ft.Text(value=None, badge=self.badge_server_status)),
            #     ft.Container(width=60)
            # ]
        )
        self.page.update()

    async def _save_credentials_and_reload(self, driver, system, user, password):
        credentials = {
            "driver": driver,
            "system": system,
            "user": user,
            "password": password,
        }

        self.encrypt_credentials(**credentials)

    def encrypt_credentials(self, **credentials):
        fernet = Fernet(self.ENCRYPTION_KEY_STR.encode())
        token = fernet.encrypt(json.dumps(credentials).encode())

        set_key(
            dotenv_path=self.env_file_path,
            key_to_set="ENCRYPTED_DB_CREDENTIALS",
            value_to_set=token.decode(),
        )

    async def _load_modals (self):
        self.switch_shema_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Switching Thema"),
            content=ft.RadioGroup(
            content=ft.Column(
                [
                    ft.ListTile(
                    ft.Row(
                        [
                            ft.Container(content=ft.Text("System"), padding=ft.padding.only(left=15)),
                            ft.Radio(value="system"),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    toggle_inputs=True,),
                    ft.ListTile(
                    ft.Row(
                        [
                            ft.Container(content=ft.Text("Light"), padding=ft.padding.only(left=15)),
                            ft.Radio(value="light"),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    toggle_inputs=True,),
                    ft.ListTile(
                    ft.Row(
                        [
                            ft.Container(content=ft.Text("Dark"), padding=ft.padding.only(left=15)),
                            ft.Radio(value="dark"),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    toggle_inputs=True,),

                ],

            ),

                on_change=self._handle_theme_mode,
        ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(self.switch_shema_modal)),
                ft.TextButton(
                    text="Save",
                    style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY),
                    on_click=lambda e: (
                        self.page.run_task(
                            self._handle_theme_mode

                        ),
                    ),
                ),
            ],
        )



        self.ENCRYPTION_KEY_STR = get_or_generate_key(self.env_file_path)
        load_dotenv(self.env_file_path, override=True)

        if os.getenv("ENCRYPTED_DB_CREDENTIALS"):
            self.db_credentials = load_decrypted_credentials(
                key=self.ENCRYPTION_KEY_STR,
                env_file_path=self.env_file_path,
            )



        driver = ft.TextField(
            label="ODBC Driver",
            value="{IBM i Access ODBC Driver}",
            border_color=ft.Colors.PRIMARY,
        )
        system = ft.TextField(
            label="IBMi Hostname",
            border_color=ft.Colors.PRIMARY,
        )
        user = ft.TextField(
            label="Username",
            border_color=ft.Colors.PRIMARY,
        )
        password = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            border_color=ft.Colors.PRIMARY,
        )

        if self.db_credentials:
            driver.value = self.db_credentials["driver"]
            user.value = self.db_credentials["user"]
            password.value = self.db_credentials["password"]
            system.value = self.db_credentials["system"]

        self.error_field = ft.Text("", visible=False, color=ft.Colors.RED)

        self.add_server_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Database credentials"),
            content=ft.Column([driver, system, user, password, self.error_field]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(self.add_server_modal)),
                ft.TextButton(
                    text="Save",
                    style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY),
                    on_click=lambda e: (
                        self.page.run_task(
                            self._try_connection, driver.value,  system.value, user.value, password.value

                        ),
                    ),
                ),
            ],
        )
    async def _try_connection(self, driver:str, system:str, user:str, password:str):
        password = password
        user = user
        system = system
        driver = driver

        if try_to_build_connection(driver, system, user, password):
            await self._save_credentials_and_reload(driver, system, user, password)
            self.error_field.visible = False
            self.error_field.update()
            self.page.close(self.add_server_modal)
        else:
            self.error_field.value = "Server connection failed."
            self.error_field.visible = True
            self.error_field.weight = ft.FontWeight.BOLD
            self.error_field.alignment = ft.MainAxisAlignment.CENTER
            self.error_field.size = 15
            self.error_field.update()



    async def _handle_theme_mode(self, e):
        """Updates the application's theme mode and persistence."""
        self.switch_shema_modal.open = False
        selected_theme = e.control.value

        if selected_theme == "system":
            await self.page.client_storage.set_async("theme_mode", selected_theme)
            self.page.theme_mode = ft.ThemeMode.SYSTEM
        elif selected_theme == "light":
            await self.page.client_storage.set_async("theme_mode", selected_theme)
            self.page.theme_mode = ft.ThemeMode.LIGHT
        elif selected_theme == "dark":
            await self.page.client_storage.set_async("theme_mode", selected_theme)
            self.page.theme_mode = ft.ThemeMode.DARK

        await self.page.client_storage.set_async("theme_mode", selected_theme)

        self.page.update()

