import os
import json
from pathlib import Path

import flet as ft
from dotenv import load_dotenv

from content.functions import load_decrypted_credentials, get_or_generate_key
from iLibrary import Library

#Information about Library: <NAME>
class Info(ft.Column):
    def __init__(self, page: ft.Page, library:str, content_manager):
        super().__init__(
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,


        )
        self.DOWNLOAD_PATH = Path.home() / "Downloads"
        self.page = page
        self.content_manager = content_manager
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
            leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: self.page.run_task(self._go_back) )
        )
        self.page.update()

    async def _go_back(self):
        try:
            from content.all_libraries import AllLibraries
            await self.content_manager(AllLibraries(
                self.page,
                content_manager=self.content_manager))
        except Exception as e:
            self.page.open(ft.SnackBar(
                content=ft.Text(
                    value=f"Failed to load library info: {e}",
                    color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED_ACCENT_400)
            )
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
                qFiles = self.lib.getFileInfo(library=self.library, qFiles=False)
                result_text = ft.Column()
                test = ft.Column(alignment=ft.MainAxisAlignment.START)
                key: str
                panel_list = ft.ExpansionPanelList(
                    expand_icon_color=ft.Colors.PRIMARY,
                    elevation=0,
                    divider_color=ft.Colors.PRIMARY,
                    controls=[],
                )

                data = json.loads(qFiles)
                print(data)
                for item in data:
                    # 1. Handle Errors immediately
                    if "error" in item:
                        self.page.open(ft.SnackBar(
                            content=ft.Text(item["error"], color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.RED_ACCENT_400
                        ))
                        continue
                    else:

                        # 2. Create a NEW ExpansionPanel for every item in the JSON list
                        new_exp_panel = ft.ExpansionPanel(
                            header=ft.ListTile(
                                title=ft.Text(item.get("OBJNAME"), weight=ft.FontWeight.BOLD
                                ),

                            ),
                            can_tap_header=True,
                            expand=True,
                            bgcolor=ft.Colors.TRANSPARENT,

                        )

                        # 3. Create a container or Column for the 'body' of the panel
                        content_column = ft.Column()

                        # 4. Loop through the keys to fill the panel content
                        for key, value in item.items():
                            # Skip the name since it's already in the header
                            if not value or value =="None":
                                continue
                            if key != "OBJNAME":
                                key_text = ft.Text(key.replace("_", " ").title(), weight=ft.FontWeight.BOLD)
                                value_text = ft.Text(value)
                                content_column.controls.append(
                                    ft.Row(controls=[key_text, value_text
                                                ]))

                    # Set the gathered text as the panel body
                    new_exp_panel.content = ft.Container(content=content_column, padding=10)

                    # 5. Add this specific panel to the list
                    panel_list.controls.append(new_exp_panel)

                for key, value in json.loads(result).items():
                    if key == "LIBRARY_SIZE":
                        mb:float = value / 1000000
                        value = f"{str(round(mb, 2))}Mb"
                    if value is not None:
                        result_text.controls.append(
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        value=f"{key.replace("_", " ").title()}: ",
                                        weight=ft.FontWeight.BOLD,
                                        size=15),
                                    ft.Text(
                                        value=value, )
                                ],
                                spacing=1
                            )
                        )
                img_icon = ft.Container(

                    content=ft.Stack(
                        controls=[

                            # 1. THE MAIN CARD (Positioned slightly lower to allow room for the circle)
                            ft.Container(
                                padding=ft.padding.only(top=75), # Space for the circle
                                content=ft.Card(
                                    elevation=10,
                                    content=ft.Container(
                                        padding=ft.padding.all(25),
                                        content=ft.Column(
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            controls=[

                                                ft.Container(height=40), # Spacer to move text below the circle
                                                ft.Text(
                                                    value= f"Library {self.library.upper()}",
                                                    size=20,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                ft.Text(
                                                    value=f"Viewing details for {self.library}",
                                                    text_align=ft.TextAlign.CENTER,
                                                ),

                                                ft.Container(height=10),
                                                result_text,
                                                ft.Container(height=10),
                                                ft.Text(
                                                    value="Files",
                                                    size=18,
                                                    weight=ft.FontWeight.BOLD,
                                                    style=ft.TextStyle(
                                                        decoration=ft.TextDecoration.UNDERLINE
                                                    ),
                                                    text_align=ft.TextAlign.LEFT,
                                                ),
                                                panel_list
                                            ],
                                        ),
                                    ),
                                ),
                            ),

                            # 2. THE FLOATING CIRCLE (Positioned at the top center)
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        padding=ft.padding.only(top=30),
                                        content=ft.IconButton(
                                            tooltip="Download SaveFile",
                                            bgcolor=ft.Colors.TRANSPARENT,
                                            icon_color=ft.Colors.TRANSPARENT,
                                            icon=ft.Icons.DOWNLOAD,
                                            on_click=lambda e, name=self.library: self.page.run_task(
                                                self._get_single_savefile, name)
                                        ),
                                    ),

                                    ft.Container(
                                        alignment=ft.alignment.top_center,
                                        content=ft.Container(
                                            width=130,
                                            height=130,
                                            bgcolor="#00ffe5",
                                            shape=ft.BoxShape.CIRCLE, # More robust than border_radius=100
                                            alignment=ft.alignment.center,
                                            opacity=0.8,
                                            shadow=ft.BoxShadow(
                                                spread_radius=1,
                                                blur_radius=8,
                                                color="#00ffe5",
                                                blur_style=ft.ShadowBlurStyle.OUTER
                                            ),
                                            content=ft.Text(
                                                self.library[0:2].upper(),
                                                color="black",
                                                weight=ft.FontWeight.BOLD,
                                                size=40
                                            ),
                                        ),
                                    ),
                                    ft.Container(
                                        padding=ft.padding.only(top=30),
                                        content=ft.IconButton(
                                            tooltip="Download SaveFile",
                                            bgcolor="#00ffe5",
                                            icon_color="black",
                                            icon=ft.Icons.DOWNLOAD,
                                            on_click = lambda e, name=self.library: self.page.run_task(
                                                    self._get_single_savefile, name)
                                        ),
                                            on_click=lambda e, name=self.library: self.page.run_task(
                                                        self._get_single_savefile, name)
                                    )

                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                            ),
                        ]
                    )
                )

                header_column = ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        img_icon,

                    ]
                )


                header_section = ft.Container(
                    content=header_column,
                    alignment=ft.alignment.top_center,
                    padding=ft.padding.only(top=40),
                    expand=False,

                )
                # Add it to your list container
                self.input_card.controls.append(header_section)

        except Exception as e:
            self.input_card.controls.clear()
            self.input_card.controls.append(ft.Text(f"Connection Error: {e}"))

        self.progress_bar.visible = False
        self.progress_bar_container.visible = False
        self.update()

    async def _get_single_savefile(self, name:str):
        print(name)
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