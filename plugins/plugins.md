# OSP Plugin Docs

## In Code

* "before_db_init" - Before Initializing DB, First Start
* "after_db_init" - After Initializing DB, First Start

* "after_main_page" - After Accessing "/"
* "after_channels_page" - After Accessing "/"
* "after_channel_view_page" - After Accessing "/channel/<channel ID>"
* "after_topic_page" - After Accessing "/topics"
* "after_topic_view_page" - After Accessing "/topic/<topic ID>"
* "after_streamers_page" - After Accessing "/streamers"
* "after_streamers_view_page" - After Accessing "/streamers/<User ID>"
* "before_view_page" - Before Accessing "/view/<Channel ID>"
* "after_view_page" - After Accessing "/view/<Channel ID>"
* "view_page_chat_popout" - On loading chat channel Popout
* "before_view_vid_page" - Before Accessing "/play/<Video ID>"
* "after_view_vid_page" - After Accessing "/play/<Video ID>"
* "vid_change_page_form_handler" - Handler in "/play/<Video ID>/change" for changing Video Metadata
* "delete_vid_page_handler" - Handler in "/play/<Video ID>/delete' for deleting recorded Videos
* "after_user_page_get" - After Accessing "/settings/user"
* "user_page_post_handler" - Handler in "/settings/user/" for updating settings
* "user_addInviteCode_handler" - Handler in "/settings/user/addInviteCode" for after tying an Invite Code to a User
* "admin_page_delete_handler" - Handler in "/settings/admin" for all deletions
* "admin_page_role_add_handler" - Handler in "/settings/admin" for all adds/creations
* "after_admin_page" - After Accessing "/admin/settings"
* "admin_page_system_post_handler" - Handler in "/settings/admin" for posting system settings changes
* "admin_page_topics_post_change_handler" - Handler in "/settings/admin" for posting Topic changes
* "admin_page_topics_post_add_handler" - Handler in "/settings/admin" for adding Topics
* "settings_channels_page_delete_handler" - Handler in "/settings/channels" for deleting a channel
* "settings_channels_page_new_handler" - Handler in "/settings/channels/" for adding a channel
* "settings_channels_page_change_handler" - Handler in "/settings/channels" for changing a channel
* "after_settings_channels_page" - After Accessing "/settings/channels"
* "after_settings_apikeys_page" - After Accessing "/settings/api"
* "settings_apikeys_post_page_new_handler" - Handler in "/settings/api/" for handing new API Keys
* "settings_apikeys_post_page_delete_handler" - Handler in "/settings/api for handing deleted API Keys"
* "socketio_handle_new_viewer" - On New Viewer Connection to a Stream
* "socketio_handle_leaving_viewer" - On Viewer Leaving a Stream
* "socketio_updateStreamData" - On Update of Live Stream Metadata
* "socketio_text_on_commands" - On Input of a user typing a "/" command in chat
* "socketio.generateInviteCode" - On Generation of an Invite Code
* "onAppInit" - Just before app initialization
