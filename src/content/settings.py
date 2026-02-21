import os

import flet as ft
from pathlib import Path
from content.functions import load_decrypted_credentials, get_or_generate_key, try_to_build_connection, load_app_info, run_query_after_settings
import json
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet
from flet import control
from typing_extensions import overload


class Settings(ft.Column):
    def __init__(self, page: ft.Page, content_manager):
        super().__init__(
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,

        )
        self.current_page = page
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
        self.current_page.run_task(self.async_init)
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.current_page.update()


    async def async_init(self):
        await self._load_modals()
        self.list_container.controls.extend([
            ft.Container(ft.ListTile(
                leading=None,
                title=ft.Text("IBMi Server Settings"),
                on_click=lambda e:self.current_page.show_dialog(self.add_server_modal),
                is_three_line=True,
                #subtitle=ft.Text(f"Description: {item["TEXT"]} \nCreated: {item['OBJCREATED']}"),
                bgcolor=ft.Colors.INVERSE_PRIMARY,
            ),
                border_radius=8,
            ),

            ft.Container(ft.ListTile(
                leading=None,
                title=ft.Text("Switch Thema Mode"),
                on_click=lambda e: self.current_page.show_dialog(self.switch_shema_modal),
                is_three_line=True,
                bgcolor=ft.Colors.INVERSE_PRIMARY,
            ),
                border_radius=8,
            ),
            ft.Container(ft.ListTile(
                leading=None,
                title=ft.Text("iLibrary App Info"),
                on_click=lambda e: self.current_page.run_task(self._about_app),
                is_three_line=True,
                bgcolor=ft.Colors.INVERSE_PRIMARY,
            ),
                border_radius=8,
            ),
            ft.Container(ft.ListTile(
                leading=None,
                title=ft.Text("Clear iLibrary App"),
                on_click=lambda e: self.current_page.show_dialog(self.clear_app_data_modal),
                is_three_line=True,
                bgcolor=ft.Colors.INVERSE_PRIMARY,
            ),
                border_radius=8,
            )
            ]
        )
        await self._create_app_bar()
        self.controls.append(self.list_container)
        self.current_page.update()

    async def _create_app_bar(self):
        self.current_page.appbar = ft.AppBar(
            title=ft.Text("Settings"),
            # actions=[
            #     # Reference the instance variable here
            #     ft.Container(content=ft.Text(value=None, badge=self.badge_server_status)),
            #     ft.Container(width=60)
            # ]
        )
        self.current_page.update()

    async def _save_credentials_and_reload(self, driver, system, port, user, password):
        credentials = {
            "driver": driver,
            "system": system,
            "port": port,
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

        self.clear_app_data_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Clearing iLibrary", color=ft.Colors.RED),
            content=ft.Text("Are you sure you want to clear and close the iLibrary App?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.current_page.pop_dialog()),
                ft.TextButton(
                    "Clear",
                    style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.RED),
                    on_click=lambda e: (
                        self.current_page.run_task(self._clear_app_data, e),
                    )
                )
            ]
        )
        self.switch_shema_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Switching Thema"),
            content=ft.RadioGroup(
                content=ft.Column(
                    [
                        ft.ListTile(
                            ft.Row(
                                [
                                    ft.Container(content=ft.Text("System"), padding=ft.Padding.only(left=15)),
                                    ft.Radio(value="system"),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            toggle_inputs=True,),
                        ft.ListTile(
                            ft.Row(
                                [
                                    ft.Container(content=ft.Text("Light"), padding=ft.Padding.only(left=15)),
                                    ft.Radio(value="light"),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            toggle_inputs=True,),
                        ft.ListTile(
                            ft.Row(
                                [
                                    ft.Container(content=ft.Text("Dark"), padding=ft.Padding.only(left=15)),
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
                ft.TextButton("Cancel", on_click=lambda e: self.current_page.pop_dialog()),
                ft.TextButton(
                    "Save",
                    style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY),
                    on_click=lambda e: (
                        self.current_page.run_task(
                            self._handle_theme_mode, e

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

        def check_port(e: ft.Event[ft.TextField]):
            """
                check the port number entered by the user, from the IBMi Server Connection Modal
            """

            if not e.control.value.isdigit():
                return
            if not e.control.value:
                value:int = 0
            else:
                value:int = int(e.control.value)

            if 0 < value <= 65535:
                port.helper = None
                port.border_color = ft.Colors.PRIMARY
                port.label_style = ft.TextStyle(color=ft.Colors.PRIMARY)
                self.current_page.update()
                return

            port.helper = ft.Text(f"Port must be between 0 and 65535", color=ft.Colors.RED)
            port.label_style = ft.TextStyle(color=ft.Colors.RED)
            port.border_color = ft.Colors.RED
            self.current_page.update()


        port = ft.TextField(
            label="Port",
            value="22",
            input_filter = ft.InputFilter(allow=True, regex_string=r"^[0-9]*$", replacement_string=""),
            on_change=check_port,  # Pass the function name only
            keyboard_type=ft.KeyboardType.NUMBER,
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
            port.value = self.db_credentials["port"]

        self.error_field = ft.Text("", visible=False, color=ft.Colors.RED)

        self.add_server_modal = ft.AlertDialog(
            modal=True,

            title=ft.Text("Database credentials"),
            content=ft.Column([driver, system, port, user, password, self.error_field]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.current_page.pop_dialog()),
                ft.TextButton(
                    "Save",
                    style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY),
                    on_click=lambda e: (
                        self.current_page.run_task(
                            self._try_connection, driver.value,  system.value, int(port.value), user.value, password.value

                        ),
                    ),
                ),
            ],

        )
    async def _try_connection(self, driver:str, system:str, port:int, user:str, password:str):
        password = password
        user = user
        system = system
        port:int = port
        driver = driver

        if try_to_build_connection(driver, system, port, user, password):
            await self._save_credentials_and_reload(driver, system,port, user, password)
            await run_query_after_settings(self.current_page, self.content_manager)
            self.error_field.visible = False
            self.error_field.update()
            self.current_page.pop_dialog()
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
            await ft.SharedPreferences().set("theme_mode", selected_theme)
            self.current_page.theme_mode = ft.ThemeMode.SYSTEM
        elif selected_theme == "light":
            await ft.SharedPreferences().set("theme_mode", selected_theme)
            self.current_page.theme_mode = ft.ThemeMode.LIGHT
        elif selected_theme == "dark":
            await ft.SharedPreferences().set("theme_mode", selected_theme)
            self.current_page.theme_mode = ft.ThemeMode.DARK

        await ft.SharedPreferences().set("theme_mode", selected_theme)

        self.current_page.update()

    async def _clear_app_data(self, e):
        """Clears persistent data then closes application window"""
        await ft.SharedPreferences().clear()
        self.clear_app_data_modal.open = False
        if os.path.isfile(self.env_file_path):
            os.remove(self.env_file_path)
        if os.path.exists(Path(__file__).parent.parent / ".auth"/ "libraries_metadata.db"):
            os.remove(Path(__file__).parent.parent / ".auth"/ "libraries_metadata.db")
        await self.current_page.window.close()
        self.current_page.update()

    async def _about_app(self):
        data = load_app_info()
        self.current_page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("About iLibrary"),
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text("App Name: ", size=15, weight=ft.FontWeight.BOLD),
                                ft.Text(data["project"]["name"]),
                        ]),
                        ft.Row(
                            controls=[
                                ft.Text("Version: ", size=15, weight=ft.FontWeight.BOLD),
                                ft.Text(data["project"]["version"]),
                            ]),
                        ft.Row(
                            controls=[
                                ft.Text("Author: ", size=15, weight=ft.FontWeight.BOLD),
                                ft.Text(data["project"]["authors"][0]["name"]),
                            ]),
                        ft.Row(
                            controls=[
                                ft.Text("Email: ", size=15, weight=ft.FontWeight.BOLD),
                                ft.Text(data["project"]["authors"][0]["email"]),
                            ]),
                        ft.Row(
                            spacing=10,
                            controls=[
                            ]),
                        ft.Row(
                            controls=[
                                ft.Text(data["tool"]["flet"]["copyright"]),
                            ]),
                    ],

                )
                ,
                actions=[ft.TextButton("Close", on_click=lambda e: self.current_page.pop_dialog())],
            )
        )

