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

        self.error_banner = ft.Banner(
            bgcolor=ft.Colors.ERROR_CONTAINER,
            open=True,
            leading=ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.ERROR, size=40),
            content=ft.Text(
                value="Oops, no Connection to the Database. Please setup the Database Credentials in the Settings",
                color=ft.Colors.ON_ERROR_CONTAINER,
            ),
            actions=[
                ft.TextButton(
                    text="Go to Settings",
                    style=ft.ButtonStyle(color=ft.Colors.ON_ERROR_CONTAINER),
                    on_click=lambda e: self.page.run_task(self._go_to_settings),
                ),
            ],
        )


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

        if await self.page.client_storage.contains_key_async('all_libraries'):
            self.error_banner.open = False
            self.input_card.visible = True
            self.list_container.visible = True

            self.controls.append(self.searchbar)
            if self.input_card not in self.controls:
                self.controls.extend([self.input_card])
            await self._rebuild_libraries()


            # else:
            #     self.page.open(self.error_banner)
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
        """
            Creating the App Bar
        """
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
        """
        rebuild the list of libraries
        """
        result = await self.page.client_storage.get_async('all_libraries')
        if isinstance(result, str):

            data = json.loads(result)

            for item in data:
                new_library_image: str = item["OBJNAME"]

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
                                on_click=lambda e, name=item["OBJNAME"]: self.page.run_task(
                                    self._show_single_library_info, name)
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
        """
        Going to the library info page
        :param name:
        """
        from content.single_library_info import Info
        await self.content_manager(Info(self.page, name, self.content_manager))

    # --------------------------------------------------------
    async def _show_setup_modal(self):
        """
        showing up the modal for the database credentials
        :return:
        """

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

    async def _get_single_savefile(self, name: str):
        """Get the Single Savefile of a Library """

        def download_save_file(library_name: str, savefile_name: str, description: str, version: str, authority: str,
                               download_path: str):
            try:
                self.page.close(self.download_modal)

                with Library(self.DB_USER, self.DB_PASSWORD, self.DB_SYSTEM, self.DB_DRIVER) as lib:
                    try:
                        lib.saveLibrary(
                            library=library_name,
                            saveFileName=savefile_name,
                            description=description,
                            localPath=download_path,
                            remPath=f'/home/{self.DB_USER.upper()}/',
                            authority=authority,
                            version=version,
                            remSavf=True,
                            getZip=True
                        )
                        self.page.run_task(self.page.client_storage.set_async, 'download_path', download_path)
                    except Exception as e:
                        self.page.open(ft.SnackBar(
                            content=ft.Text(f"Failed: {e}", color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.RED_ACCENT_400))
                        return

                    self.page.open(ft.SnackBar(
                        content=ft.Text(f"Success, saved to: {download_path}", color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.GREEN_ACCENT_400))

            except Exception as e:
                if hasattr(self, "input_card"):
                    self.input_card.controls.clear()
                    self.input_card.controls.append(ft.Text(f"Connection Error: {e}"))
                    self.page.update()

        # Ref fields for the download modal
        save_file_description_text_field_ref = ft.Ref[ft.TextField]()
        save_file_version_text_field_ref = ft.Ref[ft.TextField]()
        save_file_authority_text_field_ref = ft.Ref[ft.TextField]()
        save_file_download_path_text_field_ref = ft.Ref[ft.TextField]()
        save_file_name_text_field_ref = ft.Ref[ft.TextField]()

        # text fields for the download modal

        self.download_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Create Savefile from Library: {name}"),
            content=ft.Column([
                ft.TextField(
                    ref=save_file_name_text_field_ref,
                    label="Savefile name",
                    value=name,
                    border_color=ft.Colors.PRIMARY,
                ),
                ft.Container(height=5),
                ft.TextField(
                    ref=save_file_description_text_field_ref,
                    label="Description",
                    value="Saved by iLibrary",
                    border_color=ft.Colors.PRIMARY,
                ),
                ft.Container(height=5),
                ft.TextField(
                    ref=save_file_version_text_field_ref,
                    label="Version",
                    value="*CURRENT",
                    border_color=ft.Colors.PRIMARY,
                    helper_text="V7R1M0, V7R2M0, V7R3M0, V7R4M0, V7R5M0, V7R6M0 ..."
                ),
                ft.Container(height=5),
                ft.TextField(
                    ref=save_file_authority_text_field_ref,
                    label="Authority",
                    border_color=ft.Colors.PRIMARY,
                    value="*ALL",
                    helper_text="*EXCLUDE, *ALL, *CHANGE, *LIBCRTAUT, *USE"
                ),
                ft.Container(height=5),
                ft.TextField(
                    ref=save_file_download_path_text_field_ref,
                    label="Download Path",
                    value=str(self.DOWNLOAD_PATH),
                    border_color=ft.Colors.PRIMARY,
                ),
            ],
                expand=False
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self.page.close(self.download_modal)),
                ft.TextButton(
                    text="Download",
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PRIMARY,
                        color=ft.Colors.ON_PRIMARY),
                    on_click=lambda e: download_save_file(
                        library_name=name,
                        savefile_name=save_file_name_text_field_ref.current.value,
                        description=save_file_description_text_field_ref.current.value,
                        version=save_file_version_text_field_ref.current.value,
                        authority=save_file_authority_text_field_ref.current.value,
                        download_path=save_file_download_path_text_field_ref.current.value
                    ), )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: print("Modal dialog dismissed!"),
        )
        self.page.open(self.download_modal)

    async def _go_to_settings(self):
        self.error_banner.open = False
        self.page.update()
        from content.settings import Settings
        await self.content_manager(Settings(self.page, self.content_manager))