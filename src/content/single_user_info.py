import os
import json
from pathlib import Path

import flet as ft
from dotenv import load_dotenv

from content.functions import load_decrypted_credentials, get_or_generate_key
from iLibrary import User

class SingleUserInfo(ft.Column):

    def __init__(self, page: ft.Page, user:str, content_manager):
        super().__init__(
            scroll=ft.ScrollMode.ADAPTIVE,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,


        )
        self.page = page
        self.content_manager = content_manager
        self.user = user
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
            title=ft.Text(f"User Info: {self.user}"),
            leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: self.page.run_task(self._go_back) )
        )
        self.page.update()

    async def _go_back(self):
        try:
            from content.all_users import AllUsers
            await self.content_manager(AllUsers(
                self.page,
                content_manager=self.content_manager))
        except Exception as e:
            self.page.open(ft.SnackBar(
                content=ft.Text(
                    value=f"Failed to load User info: {e}",
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
                await self._get_info_about_user()
            else:
                pass
                #await self._show_setup_modal()
        else:
            pass
            #await self._show_setup_modal()

        self.update()

    async def _get_info_about_user(self):
        try:
            # 1. Clear previous results and show progress
            self.input_card.controls.clear()
            self.progress_bar.visible = True
            self.progress_bar_container.visible = True
            self.update()

            with (User(self.DB_USER, self.DB_PASSWORD, self.DB_SYSTEM, self.DB_DRIVER) as self.User):
                # Fetch data
                result = self.User.getSingleUserInformation(username=str(self.user), wantJson=True)

                # --- ROBUST DATA PARSING ---
                # This handles the "Expecting value" error by checking types before loading
                def safe_parse(input_data):
                    if input_data is None:
                        return []
                    if isinstance(input_data, (list, dict)):
                        return input_data
                    if isinstance(input_data, str) and input_data.strip() == "":
                        return []
                    try:
                        return json.loads(input_data)
                    except Exception as e:
                        # If it's not JSON, return it as a list with an error message
                        return [{"error": f"Parse Error: {str(e)}", "raw": str(input_data)}]

                data = safe_parse(result)
               #for key, value in data.items():
                #
                # # --- UI CONSTRUCTION ---
                result_text = ft.Column()
                panel_list = ft.ExpansionPanelList(
                    expand_icon_color=ft.Colors.PRIMARY,
                    elevation=0,
                    divider_color=ft.Colors.PRIMARY,
                    controls=[],
                )
                #
                # # Process File Info
                for item in data:
                    if "error" in item:
                        self.page.open(ft.SnackBar(
                            content=ft.Text(f"Notice: {item['error']}", color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.RED_ACCENT_400
                        ))
                        # If it's a real error, show the raw output for debugging in the build
                        if "raw" in item:
                            panel_list.controls.append(ft.ExpansionPanel(
                                header=ft.ListTile(title=ft.Text("Raw Debug Data")),
                                content=ft.Container(content=ft.Text(item["raw"]))
                            ))
                        continue

                # # Process user Info
                # # Ensure user_info_data is a dict (if it was a list, take the first item)
                info_dict = data[0] if isinstance(data, list) else data

                for key, value in info_dict.items():
                    if key in ["MAXIMUM_ALLOWED_STORAGE", "STORAGE_USED"] and value:
                        try:
                            mb = float(value) / 1000
                            value = f"{round(mb, 2)} Mb"
                        except:
                            pass

                    if value is not None:
                        result_text.controls.append(
                            ft.Row(
                                controls=[
                                    ft.Text(f"{key.replace('_', ' ').title()}: ", weight=ft.FontWeight.BOLD, size=15),
                                    ft.Text(value=str(value))
                                ],
                                spacing=1
                            )
                        )

                # # --- ICON AND LAYOUT SECTION ---

                # -- Set User Class Name and Status Color--
                user_status = data["STATUS"]
                status_color = ft.Colors.GREEN
                if not user_status == "*ENABLED":
                    status_color = ft.Colors.RED

                user_class_name = data["USER_CLASS_NAME"]
                match user_class_name:
                    case "*USER":
                        user_class_name_color = ft.Colors.LIME
                    case "*PGMR":
                        user_class_name_color = ft.Colors.PINK
                    case "*SECADM":
                        user_class_name_color = ft.Colors.PURPLE
                    case "*SECOFR":
                        user_class_name_color = ft.Colors.INDIGO
                    case "*SYSOPR":
                        user_class_name_color = ft.Colors.RED

                user_badge = ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Container( #active Status
                            content=ft.Text(
                                value=user_status,
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD,
                                size=10
                            ),
                            bgcolor=status_color,
                            padding=ft.padding.only(left=4, right=4, top=2, bottom=2),  # Padding around the text
                            border_radius=ft.border_radius.all(10),  # Rounded corners for a pill/badge shape
                        ),
                        ft.Container(  #  Status Class Name
                            content=ft.Text(
                                value=user_class_name,
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD,
                                size=10
                            ),
                            bgcolor=user_class_name_color,
                            padding=ft.padding.only(left=4, right=4, top=2, bottom=2),  # Padding around the text
                            border_radius=ft.border_radius.all(10),  # Rounded corners for a pill/badge shape
                        )
                    ]
                )



                img_icon = ft.Container(
                    content=ft.Stack(
                        controls=[
                            ft.Container(
                                padding=ft.padding.only(top=75),
                                content=ft.Card(
                                    elevation=10,
                                    content=ft.Container(
                                        padding=ft.padding.all(25),
                                        content=ft.Column(
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            controls=[
                                                ft.Container(height=40),
                                                ft.Text(f"{self.user.upper()}", size=20,
                                                        weight=ft.FontWeight.BOLD),
                                                user_badge,
                                                ft.Container(height=10),
                                                result_text,
                                                ft.Container(height=10),

                                                panel_list
                                            ],
                                        ),
                                    ),
                                ),
                            ),
                            ft.Row(
                                [
                                    ft.Container(
                                        width=130, height=130,
                                        bgcolor="#00ffe5",
                                        shape=ft.BoxShape.CIRCLE,
                                        alignment=ft.alignment.center,
                                        shadow=ft.BoxShadow(blur_radius=8, color="#00ffe5"),
                                        content=ft.Text(self.user[0:2].upper(), color="black",
                                                        weight=ft.FontWeight.BOLD, size=40),
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                            ),
                        ]
                    )
                )

                header_section = ft.Container(
                    content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[img_icon]),
                    alignment=ft.alignment.top_center,
                    padding=ft.padding.only(top=40),
                )

                self.input_card.controls.append(header_section)

        except Exception as e:
            self.input_card.controls.clear()
            # Display the full error for debugging
            self.input_card.controls.append(
                ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text("Connection or Data Error", weight=ft.FontWeight.BOLD, color="red"),
                        ft.Text(f"Details: {str(e)}", size=12)
                    ])
                )
            )

        finally:
            self.progress_bar.visible = False
            self.progress_bar_container.visible = False
            self.update()

    async def _get_single_savefile(self, name: str):
        """Get the Single Savefile of a user """

        def download_save_file(user_name: str, savefile_name: str, description: str, version: str, authority: str,
                               download_path: str):
            try:
                self.page.close(self.download_modal)

                with user(self.DB_USER, self.DB_PASSWORD, self.DB_SYSTEM, self.DB_DRIVER) as user:
                    try:
                        user.saveuser(
                            user=user_name,
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
            title=ft.Text(f"Create Savefile from user: {name}"),
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
                    value="Saved by iuser",
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
                    helper_text="*EXCLUDE, *ALL, *CHANGE, *userCRTAUT, *USE"
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
                        user_name=name,
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