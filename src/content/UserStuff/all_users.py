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
            horizontal_alignment=ft.CrossAxisAlignment.CENTER

        )
        self.current_page = page
        self.content_manager = content_manager
        self.env_file_path = Path(__file__).parent.parent / ".env"
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
        self.progress_bar = ft.Container(
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=8,
                content=ft.Row([
                    ft.ProgressRing(color=ft.Colors.ON_PRIMARY_CONTAINER),
                    ft.Text("Loading users\nplease wait ...",color=ft.Colors.ON_PRIMARY_CONTAINER)]),
                padding=20,
                alignment=ft.Alignment.CENTER_LEFT
            )
        self.progress_bar_container = ft.Container(self.progress_bar, alignment=ft.Alignment.TOP_CENTER)
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
            data_lib = cursor.execute("SELECT AUTHORIZATION_NAME FROM USER_METADATA WHERE AUTHORIZATION_NAME LIKE ? LIMIT 50", (f"%{query}%",))
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
        #Fetch First 10 Users
        with sqlite3.connect(self.path_to_DB_file, timeout=10) as conn:
            cursor = conn.cursor()

            # 3. Fetch data
            cursor.execute("SELECT AUTHORIZATION_NAME FROM USER_METADATA LIMIT 50")
            data = cursor.fetchall()
            cursor.close()
        for i in data:
            lv.controls.append(
                ft.ListTile(
                    title=ft.Text(i[0]),  # Force to string
                    on_click=lambda _, name=str(i[0]).replace("'", ""): self.current_page.run_task(
                        self._show_single_user_info, name
                    )
                )
            )
        self.searchbar = ft.SearchBar(
            view_elevation=4,
            bar_text_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            view_header_text_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            view_hint_text_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            bar_bgcolor=ft.Colors.SECONDARY_CONTAINER,
            view_bgcolor=ft.Colors.SECONDARY_CONTAINER,
            divider_color=ft.Colors.ON_SECONDARY_CONTAINER,
            bar_hint_text="Search for User...",
            view_hint_text="Suggestions...",
            on_change=handle_change,
            on_tap=open_searchbar,
            controls=[lv],
            visible=False,
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
            self._show_loading_status("No users found.\nWaiting for sync...")
            return

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
        Safely rebuilds the list of users from the local SQLite database.
        """
        # 1. Ensure the directory exists before trying to open the file
        # This prevents the "unable to open database file" error
        self.path_to_DB.mkdir(parents=True, exist_ok=True)

        # Clear the container to avoid duplicating the list on refresh
        self.list_container.controls.clear()

        try:
            # Use a timeout in case the background worker is currently writing
            with sqlite3.connect(self.path_to_DB_file, timeout=10) as conn:
                cursor = conn.cursor()

                # 2. Defensive Check: Does the table exist?
                # This prevents crashing if the sync worker hasn't run yet.
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='USER_METADATA'"
                )
                if not cursor.fetchone():
                    print("USER_METADATA table not found yet. Showing syncing state.")
                    self._show_loading_status("Initializing users...")
                    return

                # 3. Fetch data
                cursor.execute("SELECT AUTHORIZATION_NAME, CREATION_TIMESTAMP, TEXT_DESCRIPTION FROM USER_METADATA")
                data = cursor.fetchall()

                if not data:
                    self._show_loading_status("No users found.\nWaiting for sync...")
                    return

                # 4. Loop through data and build UI
                for item in data:
                    username = str(item[0]).strip()
                    timestamp_str = item[1]
                    description = item[2]

                    try:
                        dt_object = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        formatted_str = dt_object.strftime("%A, %b %d, %Y")
                    except:
                        formatted_str = timestamp_str

                    new_user_tile = ft.Container(
                        content=ft.ListTile(
                            leading=ft.CircleAvatar(
                                content=ft.Text(username[0:2].upper()),
                                bgcolor=ft.Colors.TERTIARY,
                                color=ft.Colors.ON_TERTIARY
                            ),
                            title=ft.Text(username),
                            subtitle=ft.Text(f"Description: {description} \nCreated: {formatted_str}"),
                            is_three_line=True,
                            bgcolor=ft.Colors.INVERSE_PRIMARY,
                            on_click=lambda e, name=username: self.current_page.run_task(
                                self._show_single_user_info, name
                            ),
                            trailing=ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                items=[
                                    ft.PopupMenuItem(
                                        content=ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE), ft.Text("Show Details")]),
                                        on_click=lambda e, name=username: self.current_page.run_task(
                                            self._show_single_user_info, name)
                                    ),
                                    ft.PopupMenuItem(
                                        content=ft.Row([ft.Icon(ft.Icons.OUTGOING_MAIL), ft.Text("Send Message")]),
                                        on_click=lambda e, name=username: self.current_page.run_task(
                                            self._send_message_to_user, name)
                                    ),
                                ],
                            ),
                        ),
                        border_radius=8,
                    )
                    self.list_container.controls.append(new_user_tile)

        except sqlite3.OperationalError as e:
            print(f"Database access error: {e}")
            self._show_loading_status("Database Busy...\nPlease wait.")
            return

        # 5. UI Updates
        self.input_card.visible = True
        self.list_container.visible = True
        self.progress_bar_container.visible = False
        self.searchbar.visible = True
        self.update()

    def _show_loading_status(self, message):
        """Shows an error/empty message."""
        self.list_container.controls.append(
            ft.Container(
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=8,
                content=ft.Row([
                    ft.ProgressRing(color=ft.Colors.ON_PRIMARY_CONTAINER),
                    ft.Text(message, color=ft.Colors.ON_PRIMARY_CONTAINER)]),
                padding=20,
                alignment=ft.Alignment.CENTER_LEFT
            )
        )
        self.list_container.visible = True
        if self.list_container not in self.controls:
            self.controls.append(self.list_container)
        self.progress_bar_container.visible = False
        self.update()

    # --------------------------------------------------------
    async def _show_single_user_info(self, name):
        """
        Going to the user info page
        :param name:
        """
        from content.UserStuff.single_user_info import SingleUserInfo
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
                    msg_feedback = ft.Text(f"{get_data.get('message')}")
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

    async def _go_to_settings(self):
        self.current_page.update()
        from content.settings import Settings
        await self.content_manager(Settings(self.current_page, self.content_manager))