import sqlite3
from datetime import datetime
import os
import json
from pathlib import Path
import flet as ft
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet
from content.functions import load_decrypted_credentials, get_or_generate_key
from iLibrary import User


class AllUsers(ft.Column):
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

        self.path_to_DB = Path(__file__).parent.parent / ".auth"
        self.path_to_DB_file = self.path_to_DB / "libraries_metadata.db"

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


    async def async_init(self):
        #self.current_page.run_task(self._load_server_status)
        await self._create_app_bar()


        def open_searchbar(e):
            self.current_page.run_task(self.searchbar.open_view)

        def handle_change(e):
            # 2. Use self.user_list (the sanitized version)
            query = e.data.upper()

            # 3. Defensive check: ensure user is treated as a string during filter
            DBConnect = sqlite3.connect(self.path_to_DB_file)
            cursor = DBConnect.cursor()
            data_lib = cursor.execute("SELECT AUTHORIZATION_NAME FROM USER_METADATA WHERE AUTHORIZATION_NAME LIKE ?", (f"%{query}%",))
            raw_data = data_lib.fetchall()
            lv.controls.clear()
            for i in raw_data:
                lv.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"{i[0]}"),
                        on_click=lambda e, name=i[0]: self.current_page.run_task(
                            self._show_single_user_info, name
                        ),
                        data=i
                    )
                )
            self.searchbar.update()

        lv = ft.ListView()
        self.searchbar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.Colors.PRIMARY,
            bar_hint_text="Search for User...",
            view_hint_text="Suggestions...",
            on_change=handle_change,
            on_tap=open_searchbar,
            controls=[lv],
        )

        if not await ft.SharedPreferences().contains_key('download_path'):
            self.DOWNLOAD_PATH = Path.home() / "Downloads"
            await ft.SharedPreferences().set('download_path', str(self.DOWNLOAD_PATH))
        else:
            self.DOWNLOAD_PATH = Path(await ft.SharedPreferences().get('download_path'))

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
                await self._rebuild_users()
            else:
             pass
        else:
            pass

        self.update()

    async def _create_app_bar(self):
        """
            Creating the App Bar
        """
        self.current_page.appbar = ft.AppBar(
            title=ft.Text("All Users"),
            actions=[
                # Reference the instance variable here
                ft.Text(f"Server: {await ft.SharedPreferences().get('server')}"),
                ft.Container(width=60),
            ]
        )
        self.current_page.update()

    async def _rebuild_users(self):
        """
        rebuild the list of libraries
        """
        DBConnect = sqlite3.connect(self.path_to_DB_file)
        cursor = DBConnect.cursor()
        data_lib = cursor.execute("SELECT AUTHORIZATION_NAME, CREATION_TIMESTAMP, TEXT_DESCRIPTION FROM USER_METADATA")

        data = data_lib.fetchall()

        for item in data:
            new_user_image: str = item[0]
            # formated_time = datetime.datetime(item['CREATION_TIMESTAMP'])
            timestamp_str = item[1]

            # 2. Parse the string (must match the input format exactly)
            dt_object = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")

            # 3. Format into a new string
            formatted_str = dt_object.strftime("%A, %b %d, %Y")

            new_user_tile = ft.Container(ft.ListTile(
                leading=ft.CircleAvatar(

                    content=ft.Text(new_user_image[0][0:2], bgcolor="#00ffe5", color="black"),
                    bgcolor="#00ffe5"
                ),
                title=ft.Text(str(item[0]).strip()),
                trailing=ft.PopupMenuButton(
                    icon=ft.Icons.MORE_VERT,
                    items=[
                        ft.PopupMenuItem(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.INFO_OUTLINE),
                                    ft.Text("Show Details"),]
                            ),
                            on_click=lambda e, name=item[0]: self.current_page.run_task(
                                self._show_single_user_info, name)
                        ),
                        ft.PopupMenuItem(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.OUTGOING_MAIL),
                                    ft.Text("Send Message"), ]
                            ),
                            on_click=lambda e, name=item[0]: self.current_page.run_task(self._send_message_to_user, name)
                        ),
                    ],
                ),
                on_click=lambda e, name=item[0]: self.current_page.run_task(self._show_single_user_info, name),
                is_three_line=True,
               subtitle=ft.Text(f"Description: {item[2]} \nCreated: {formatted_str}"),
                bgcolor=ft.Colors.INVERSE_PRIMARY,
            ),
                border_radius=8,
            )
            self.list_container.controls.append(new_user_tile)

        self.input_card.visible = True
        self.list_container.visible = True

        self.progress_bar.visible = False
        self.progress_bar_container.visible = False

        self.update()

    # --------------------------------------------------------
    async def _show_single_user_info(self, name):
        """
        Going to the user info page
        :param name:
        """
        from content.single_user_info import SingleUserInfo
        await self.content_manager(SingleUserInfo(self.current_page, name, self.content_manager))


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


    async def _send_message_to_user(self, username):
        def send_msg(e):
            if message_textfield.value == '' or message_textfield.value is None:
                message_textfield.helper = "Please enter a message"
                self.current_page.update()
                return
            with User(self.DB_USER, self.DB_PASSWORD, self.DB_SYSTEM, self.DB_DRIVER) as msg:
                data:str = msg.send_message_to_user(username=str(username) , message=message_textfield.value)
                get_data = json.loads(data)
                if get_data.get("success"):
                    msg_feedback = ft.Text(f"Message sent successfully to {username}")
                    snack_bg_color = ft.Colors.GREEN_ACCENT_400

                if get_data.get("error"):
                    msg_feedback = ft.Text(f"Message sent was not successfully to {username}")
                    snack_bg_color = ft.Colors.RED_ACCENT_400
                self.current_page.pop_dialog()
                self.current_page.show_dialog(ft.SnackBar(content=msg_feedback, bgcolor=snack_bg_color))


        message_textfield = ft.TextField(
            label="Type your message here:",
            autofocus=True,
            border_color=ft.Colors.PRIMARY,
            multiline=True,
            on_submit=send_msg,
            shift_enter=True,
            min_lines=1,
            max_lines=10,
            max_length=512,
        )
        send_button = ft.TextButton(
            content=ft.Text("Send", color=ft.Colors.ON_PRIMARY),
            style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY),
            on_click = lambda e: send_msg(e),
        )
        message_dialog = ft.AlertDialog(
            title=ft.Text(f"Send Message to User: {username}"),
            content=message_textfield,
            actions=[ft.TextButton("Cancel", on_click=lambda e: self.current_page.pop_dialog()), send_button],
        )
        self.current_page.show_dialog(message_dialog)