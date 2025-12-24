import os
import json
from pathlib import Path
import asyncio
import flet as ft
import content.config as config
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet
from content.functions import load_decrypted_credentials, get_or_generate_key
from iLibrary import Library
from pycparser.c_ast import While


class AllLibraries(ft.Column):
    def __init__(self, page: ft.Page, content_manager):
        super().__init__(
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,

        )
        self.page = page
        self.content_manager = content_manager
        self.env_file_path = Path(__file__).parent / ".env"
        self.badge_server_status = ft.Badge()

        self.ENCRYPTION_KEY_STR = None
        self.db_credentials = None
        self.DB_DRIVER = None
        self.DB_USER = None
        self.DB_PASSWORD = None
        self.DB_SYSTEM = None


        self.list_container = ft.Column()
        self.input_card = self.list_container
        self.progress_bar = ft.ProgressRing()
        self.progress_bar_container = ft.Container(self.progress_bar, alignment=ft.alignment.center)
        self.controls.append(self.progress_bar_container)

        # Start initialization
        self.page.run_task(self.async_init)
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress_bar.visible = True
        self.progress_bar_container.visible = True
        self.page.update()
    # --------------------------------------------------------

    async def async_init(self):
        #self.page.run_task(self._load_server_status)
        await self._create_app_bar()
        #SEARCHBAR
        library_list = await self.page.client_storage.get_async('library_names')

        def open_searchbar(e):
            self.searchbar.open_view()


        def handle_change(e):
            list_to_show = [library for library in library_list if e.data.upper() in library]
            lv.controls.clear()
            for i in list_to_show:
                lv.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"{i}"),
                        on_click=lambda e, name=i: self.page.run_task(
                            self._show_single_library_info, name
                            ),
                        data=i))
            self.searchbar.update()

        lv = ft.ListView()
        self.searchbar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.Colors.PRIMARY,
            bar_hint_text="Search for Library...",
            view_hint_text="Suggestions...",
            on_change=handle_change,
            on_tap=open_searchbar,
            controls=[



                lv
            ],
        )



        if not await self.page.client_storage.contains_key_async('download_path'):
            self.DOWNLOAD_PATH = Path.home() / "Downloads"
            await self.page.client_storage.set_async('download_path', str(self.DOWNLOAD_PATH))
        else:
            self.DOWNLOAD_PATH = Path(await self.page.client_storage.get_async('download_path'))


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

                self.controls.append(self.searchbar)
                if self.input_card not in self.controls:
                    self.controls.extend([self.input_card])
                await self._rebuild_libraries()
            else:
                await self._show_setup_modal()
        else:
            await self._show_setup_modal()

        self.update()

    async def _load_server_status(self):
        # Initialize the badge once
        self.badge_server_status = ft.Badge()

        while True:
            if not config.SERVER_STATUS:
                self.badge_server_status.text = 'Offline'
                self.badge_server_status.bgcolor = ft.Colors.ERROR
            else:
                self.badge_server_status.text = 'Online'
                self.badge_server_status.bgcolor = ft.Colors.GREEN_ACCENT_400

            # In Flet, you must update the page to see changes
            self.update()
            self.page.update()
            await asyncio.sleep(10.0)

    async def _create_app_bar(self):
        self.page.appbar = ft.AppBar(
            title=ft.Text("All Libraries"),
            # actions=[
            #     # Reference the instance variable here
            #     ft.Container(content=ft.Text(value=None, badge=self.badge_server_status)),
            #     ft.Container(width=60)
            # ]
        )
        self.page.update()

    async def _rebuild_libraries(self):

        result = await self.page.client_storage.get_async('all_libraries')
        if isinstance(result, str):

            data = json.loads(result)

            for item in data:

                new_library_image:str = item["OBJNAME"]


                new_library_tile = ft.Container(ft.ListTile(
                                leading=ft.CircleAvatar(

                                        content=ft.Text(new_library_image[0:2], bgcolor="#00ffe5", color="black"),
                                        bgcolor="#00ffe5"
                                    ),
                                title=ft.Text(item["OBJNAME"]),
                                trailing=ft.PopupMenuButton(
                                    icon=ft.Icons.MORE_VERT,
                                    items=[
                                        ft.PopupMenuItem(
                                            text="Show Details",
                                            on_click=lambda e, name=item["OBJNAME"]: self.page.run_task(self._show_single_library_info, name, self.content_manager)
                                        ),
                                        ft.PopupMenuItem(
                                            text="Get SaveFile",
                                            on_click=lambda e, name=item["OBJNAME"]: self.page.run_task(
                                                self._get_single_savefile, name)
                                        ),
                                    ],
                                ),
                                on_click=lambda e, name=item["OBJNAME"]: self.page.run_task(self._show_single_library_info, name),
                                is_three_line=True,
                                subtitle=ft.Text(f"Description: {item["TEXT"]} \nCreated: {item['OBJCREATED']}"),
                                bgcolor=ft.Colors.INVERSE_PRIMARY,
                            ),
                    border_radius=8,
                )
                self.list_container.controls.append(new_library_tile)

            self.input_card.visible = True
            self.list_container.visible = True


        self.progress_bar.visible = False
        self.progress_bar_container.visible = False

        self.update()

    # --------------------------------------------------------
    async def _show_single_library_info(self, name):
        from content.single_library_info import Info
        await self.content_manager(Info(self.page, name, self.content_manager))

    # --------------------------------------------------------
    async def _show_setup_modal(self):
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

        self.add_server_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Database credentials"),
            content=ft.Column([driver, system, user, password]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(self.add_server_modal)),
                ft.TextButton(
                    "Save",
                    style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY),
                    on_click=lambda e: (
                        self.page.close(self.add_server_modal),
                        self.page.run_task(
                            self._save_credentials_and_reload, driver, system, user, password
                        ),
                    ),
                ),
            ],
        )

        self.page.open(self.add_server_modal)


    # --------------------------------------------------------

    async def _save_credentials_and_reload(self, driver, system, user, password):
        credentials = {
            "driver": driver.value,
            "system": system.value,
            "user": user.value,
            "password": password.value,
        }

        self.encrypt_credentials(**credentials)
        await self.async_init()

    # --------------------------------------------------------

    def encrypt_credentials(self, **credentials):
        fernet = Fernet(self.ENCRYPTION_KEY_STR.encode())
        token = fernet.encrypt(json.dumps(credentials).encode())

        set_key(
            dotenv_path=self.env_file_path,
            key_to_set="ENCRYPTED_DB_CREDENTIALS",
            value_to_set=token.decode(),
        )

    async def _get_single_savefile(self, name:str):

        try:
            with Library(self.DB_USER, self.DB_PASSWORD, self.DB_SYSTEM, self.DB_DRIVER) as lib:
                try:
                    lib.saveLibrary(
                    library=name,
                    saveFileName=name,
                    description='Backup',
                    localPath=str(self.DOWNLOAD_PATH),
                    remPath=f'/home/{self.DB_USER.upper()}/',
                    authority='*ALL',
                    remSavf=True,
                    getZip=True
                )
                except Exception as e:
                    self.page.open(ft.SnackBar(content=ft.Text(f"Failed: Could not download the save file: {name}", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_ACCENT_400 ))
                    return

                self.page.open(ft.SnackBar(content=ft.Text(f"Success, saved to: {self.DOWNLOAD_PATH / name}.savf", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_ACCENT_400 ))
        except Exception as e:
            self.input_card.controls.clear()
            self.input_card.controls.append(
                ft.Text(f"Connection Error: {e}")
        )
            self.page.update()
