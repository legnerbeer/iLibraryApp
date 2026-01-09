import os
import json
from pathlib import Path
import asyncio
import flet as ft
from content.functions import load_decrypted_credentials, get_or_generate_key
from iLibrary import Library


class AllLibraries(ft.Column):
    def __init__(self, page: ft.Page, content_manager):
        super().__init__(
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,

        )
        self.current_page = page
        self.content_manager = content_manager
        self.env_file_path = Path(__file__).parent / ".env"
        self.badge_server_status = ft.Badge()

        self.ENCRYPTION_KEY_STR = None
        self.db_credentials = None
        self.DB_DRIVER = None
        self.DB_USER = None
        self.DB_PASSWORD = None
        self.DB_SYSTEM = None
        self.DB_PORT = None

        self.list_container = ft.Column()
        self.input_card = self.list_container
        self.progress_bar = ft.ProgressRing()
        self.progress_bar_container = ft.Container(self.progress_bar, alignment=ft.Alignment.CENTER)
        self.controls.append(self.progress_bar_container)

        # Start initialization

        self.current_page.run_task(self.async_init)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress_bar.visible = True
        self.progress_bar_container.visible = True
        self.current_page.update()

    # --------------------------------------------------------

    def open_searchbar(self, e):
        self.current_page.run_task( self.searchbar.open_view)

    async def load_library_names(self):
        # # 1. Get the data from SharedPreferences
        # raw_data = await ft.SharedPreferences().get(key='library_names')
        raw_data = await ft.SharedPreferences().get(key='library_names')

        try:
            if isinstance(raw_data, list):
                # If it's a list of one string that looks like a list: ["['A', 'B']"]
                if len(raw_data) == 1 and isinstance(raw_data[0], str) and raw_data[0].startswith("["):
                    # Clean the string and parse it properly
                    # We replace single quotes with double quotes for valid JSON
                    valid_json_string = raw_data[0].replace("'", '"')
                    self.library_list = json.loads(valid_json_string)
                else:
                    self.library_list = raw_data
            elif isinstance(raw_data, str):
                # If it's just the string: "['A', 'B']"
                valid_json_string = raw_data.replace("'", '"')
                self.library_list = json.loads(valid_json_string)
            else:
                self.library_list = []
        except Exception as e:
            print(f"Error parsing user_names: {e}")
            self.library_list = []

        # Clean up any extra whitespace or quotes left over
        self.library_list = [str(u).strip() for u in self.library_list]

    def handle_change(self, e):
        # 3. Get the search query
        query = e.data.upper().strip()

        # 4. Filter: Ensure 'library' is treated as a string
        # We check if 'query' is inside the 'library' name
        list_to_show = [
            lib for lib in self.library_list
            if query in str(lib).upper()
        ]

        # 5. Clear and Repopulate
        self.lv.controls.clear()

        for library_name in list_to_show:
            self.lv.controls.append(
                ft.ListTile(
                    title=ft.Text(library_name),  # Force to string
                    on_click=lambda _, name=str(library_name).replace("'", ""): self.current_page.run_task(
                        self._show_single_library_info, name
                    )
                )
            )

        # update the UI

    async def async_init(self):
        await self._create_app_bar()
        # Load library names before using them
        await self.load_library_names()

        # Create ListView and SearchBar
        self.lv = ft.ListView()
        self.searchbar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.Colors.PRIMARY,
            bar_hint_text="Search for Library...",
            view_hint_text="Suggestions...",
            on_change=self.handle_change,  # use method, not function
            on_tap=self.open_searchbar,  # open searchbar when tapped
            controls=[self.lv],  # ListView inside the SearchBar
        )

        # Download path and SharedPreferences logic
        if not await ft.SharedPreferences().contains_key('download_path'):
            self.DOWNLOAD_PATH = Path.home() / "Downloads"
            await ft.SharedPreferences().set('download_path', str(self.DOWNLOAD_PATH))
        else:
            self.DOWNLOAD_PATH = Path(await ft.SharedPreferences().get('download_path'))

        self.ENCRYPTION_KEY_STR = get_or_generate_key(self.env_file_path)

        if await ft.SharedPreferences().contains_key('all_libraries'):
            self.input_card.visible = True
            self.list_container.visible = True

            self.controls.append(self.searchbar)
            if self.input_card not in self.controls:
                self.controls.extend([self.input_card])

            await self._rebuild_libraries()
        else:
            # Uncomment if you want to show an error banner when no libraries are found
            # self.current_page.open(self.error_banner)
            pass

        self.update()

    async def _create_app_bar(self):
        """
            Creating the App Bar
        """
        self.current_page.appbar = ft.AppBar(
            title=ft.Text("All Libraries"),
            # actions=[
            #     # Reference the instance variable here
            #     ft.Container(content=ft.Text(value=None, badge=self.badge_server_status)),
            #     ft.Container(width=60)
            # ]
        )
        self.current_page.update()

    async def _rebuild_libraries(self):
        """
        rebuild the list of libraries
        """
        result = await ft.SharedPreferences().get('all_libraries')
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
                                "Show Details",
                                on_click=lambda e, name=item["OBJNAME"]: self.current_page.run_task(
                                    self._show_single_library_info, name)
                            ),
                            ft.PopupMenuItem(
                                "Get SaveFile",
                                on_click=lambda e, name=item["OBJNAME"]: self.current_page.run_task(
                                    self._get_single_savefile, name)
                            ),
                        ],
                    ),
                    on_click=lambda e, name=item["OBJNAME"]: self.current_page.run_task(self._show_single_library_info, name),
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
        await self.content_manager(Info(self.current_page, name, self.content_manager))



    async def _get_single_savefile(self, name: str):
        """Get the Single Savefile of a Library """

        def download_save_file(library_name: str, savefile_name: str, description: str, version: str, authority: str,
                               download_path: str):


            try:
                credentials = load_decrypted_credentials(self.ENCRYPTION_KEY_STR, self.env_file_path)
                self.DB_USER = credentials["user"]
                self.DB_PASSWORD = credentials["password"]
                self.DB_SYSTEM = credentials["system"]
                self.DB_DRIVER = credentials["driver"]
                self.DB_PORT = credentials["port"]
                self.current_page.pop_dialog()
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
                            getZip=True,
                            port=self.DB_PORT
                        )
                        self.current_page.run_task(ft.SharedPreferences().set, 'download_path', download_path)
                    except Exception as e:
                        self.current_page.show_dialog(ft.SnackBar(
                            content=ft.Text(f"Failed: {e}", color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.RED_ACCENT_400))
                        return

                    self.current_page.show_dialog(ft.SnackBar(
                        content=ft.Text(f"Success, saved to: {download_path}", color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.GREEN_ACCENT_400))

            except Exception as e:
                if hasattr(self, "input_card"):
                    self.input_card.controls.clear()
                    self.input_card.controls.append(ft.Text(f"Connection Error: {e}"))
                    self.current_page.update()

        self.DB_USER = None
        self.DB_PASSWORD = None
        self.DB_SYSTEM = None
        self.DB_DRIVER = None
        self.DB_PORT = None

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

                    helper="V7R1M0, V7R2M0, V7R3M0, V7R4M0, V7R5M0, V7R6M0 ..."
                ),
                ft.Container(height=5),
                ft.TextField(
                    ref=save_file_authority_text_field_ref,
                    label="Authority",
                    border_color=ft.Colors.PRIMARY,
                    value="*ALL",
                    helper="*EXCLUDE, *ALL, *CHANGE, *LIBCRTAUT, *USE"
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
                ft.TextButton("Close", on_click=lambda e: self.current_page.pop_dialog()),
                ft.TextButton(
                    "Download",
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
        self.current_page.show_dialog(self.download_modal)

    async def _go_to_settings(self):
        self.current_page.update()
        from content.settings import Settings
        await self.content_manager(Settings(self.current_page, self.content_manager))